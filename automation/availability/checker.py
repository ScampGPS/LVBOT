"""Core availability checker built on consolidated helpers."""

from __future__ import annotations
from tracking import t

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from playwright.async_api import Page

from infrastructure.constants import COURT_CONFIG, NO_AVAILABILITY_PATTERNS
from .api import fetch_available_slots
from infrastructure.settings import get_settings
from pathlib import Path

logger = logging.getLogger(__name__)


class AvailabilityChecker:
    """Fetch and format court availability using Playwright pages."""

    def __init__(self, browser_pool) -> None:
        t('automation.availability.checker.AvailabilityChecker.__init__')
        self.browser_pool = browser_pool
        self._reference_date: Optional[date] = None
        self._current_time: Optional[datetime] = None
        settings = get_settings()
        self._save_screenshots = settings.save_availability_screenshots
        self._screenshot_dir = Path(settings.data_directory) / "screenshots" / "availability"

    async def check_all_courts_parallel(self) -> Dict[int, List[str]]:
        t('automation.availability.checker.AvailabilityChecker.check_all_courts_parallel')
        structured = await self.check_availability()
        flattened: Dict[int, List[str]] = {}

        for court_num, per_day in structured.items():
            if isinstance(per_day, dict) and "error" in per_day:
                flattened[court_num] = []
                continue

            collected: List[str] = []
            for times in per_day.values():
                collected.extend(times)
            flattened[court_num] = sorted(set(collected))

        return flattened

    async def check_availability(
        self,
        court_numbers: Optional[List[int]] = None,
        max_concurrent: int = 3,
        timeout_per_court: float = 30.0,
        reference_date: Optional[date] = None,
        current_time: Optional[datetime] = None,
    ) -> Dict[int, Dict[str, List[str]]]:
        t('automation.availability.checker.AvailabilityChecker.check_availability')
        self._reference_date = reference_date
        self._current_time = current_time

        targets = court_numbers or list(COURT_CONFIG.keys())
        valid_courts = [c for c in targets if c in COURT_CONFIG]
        if len(valid_courts) < len(targets):
            invalid = sorted(set(targets) - set(valid_courts))
            logger.warning("Invalid court numbers requested: %s", invalid)

        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = [self._check_with_semaphore(court, semaphore, timeout_per_court) for court in valid_courts]
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            self._reference_date = None
            self._current_time = None

        availability: Dict[int, Dict[str, List[str]]] = {}
        for court_num, result in zip(valid_courts, results):
            if isinstance(result, Exception):
                logger.error("Court %s check failed: %s", court_num, result)
                availability[court_num] = {"error": str(result)}
            else:
                availability[court_num] = result

        return availability

    async def _check_with_semaphore(
        self,
        court_num: int,
        semaphore: asyncio.Semaphore,
        timeout: float,
    ) -> Dict[str, List[str]]:
        t('automation.availability.checker.AvailabilityChecker._check_with_semaphore')
        async with semaphore:
            try:
                return await asyncio.wait_for(self.check_single_court(court_num), timeout=timeout)
            except asyncio.TimeoutError as exc:
                logger.error("Court %s check timed out after %.1fs", court_num, timeout)
                return {"error": str(exc)}

    async def check_single_court(self, court_num: int) -> Dict[str, List[str]]:
        t('automation.availability.checker.AvailabilityChecker.check_single_court')
        if court_num not in COURT_CONFIG:
            raise ValueError(f"Invalid court number: {court_num}")

        pages = getattr(self.browser_pool, "pages", {})
        page: Optional[Page] = pages.get(court_num) if isinstance(pages, dict) else None
        if not page:
            raise RuntimeError(f"No page available for court {court_num}")

        logger.info("Checking Court %s availability", court_num)

        try:
            await page.reload(wait_until="domcontentloaded")
            await asyncio.sleep(1)

            if self._save_screenshots:
                await self._capture_screenshot(page, court_num)

            if await self._has_no_availability_message(page):
                return {}

            parsed = await fetch_available_slots(
                page,
                reference_date=self._reference_date,
                current_time=self._current_time,
            )
            if not parsed:
                logger.warning("Court %s: No times returned by parser", court_num)
                return {}

            total = sum(len(times) for times in parsed.values())
            logger.info("Court %s: Found %s time slots across %s days", court_num, total, len(parsed))
            for day_key, times in parsed.items():
                logger.debug("Court %s %s => %s", court_num, day_key, times)

            return parsed

        except Exception as exc:  # pragma: no cover - defensive guard
            logger.error("Court %s availability check failed: %s", court_num, exc, exc_info=True)
            raise

    async def _capture_screenshot(self, page: Page, court_num: int) -> None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        try:
            self._screenshot_dir.mkdir(parents=True, exist_ok=True)
            path = self._screenshot_dir / f"court-{court_num}-{timestamp}.png"
            await page.screenshot(path=str(path))
            logger.debug(
                "Saved availability screenshot for court %s at %s",
                court_num,
                path,
            )
        except Exception as exc:  # pragma: no cover - debug helper
            logger.debug(
                "Failed to capture availability screenshot for court %s: %s",
                court_num,
                exc,
            )

    async def _has_no_availability_message(self, page: Page) -> bool:
        t('automation.availability.checker.AvailabilityChecker._has_no_availability_message')
        try:
            for pattern in NO_AVAILABILITY_PATTERNS.get("es", []):
                if await page.query_selector(f'*:has-text("{pattern}")'):
                    return True
            for pattern in NO_AVAILABILITY_PATTERNS.get("en", []):
                if await page.query_selector(f'*:has-text("{pattern}")'):
                    return True
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.debug("Error checking no availability copy: %s", exc)
        return False

    async def get_next_available_slot(
        self,
        court_numbers: Optional[List[int]] = None,
        min_time: Optional[str] = None,
        max_time: Optional[str] = None,
    ) -> Optional[Tuple[int, date, str]]:
        t('automation.availability.checker.AvailabilityChecker.get_next_available_slot')
        availability = await self.check_availability(court_numbers)

        earliest: Optional[Tuple[int, date, str]] = None
        for court_num, per_day in availability.items():
            if isinstance(per_day, dict) and "error" in per_day:
                continue

            for day_key, times in per_day.items():
                try:
                    day_value = datetime.strptime(day_key, "%Y-%m-%d").date()
                except ValueError:
                    continue

                for time_value in times:
                    if min_time and time_value < min_time:
                        continue
                    if max_time and time_value > max_time:
                        continue

                    candidate = (court_num, day_value, time_value)
                    if earliest is None or (day_value, time_value) < (earliest[1], earliest[2]):
                        earliest = candidate

        return earliest

    @staticmethod
    def format_availability_message(availability: Dict[int, Dict[str, List[str]]]) -> str:
        t('automation.availability.checker.AvailabilityChecker.format_availability_message')
        if not availability:
            return "No hay disponibilidad en ninguna cancha"

        lines = ["🎾 *Disponibilidad de Canchas*\n"]
        today = date.today()

        for court_num in sorted(availability.keys()):
            court_data = availability[court_num]
            if isinstance(court_data, dict) and "error" in court_data:
                lines.append(f"*Cancha {court_num}:* ❌ Error al verificar")
                continue
            if not court_data:
                lines.append(f"*Cancha {court_num}:* Sin disponibilidad")
                continue

            lines.append(f"*Cancha {court_num}:*")
            for day_key in sorted(court_data.keys()):
                try:
                    day_value = datetime.strptime(day_key, "%Y-%m-%d").date()
                except ValueError:
                    label = day_key
                else:
                    if day_value == today:
                        label = "Hoy"
                    elif day_value == today + timedelta(days=1):
                        label = "Mañana"
                    else:
                        label = day_value.strftime("%d/%m")

                times = ", ".join(sorted(court_data[day_key]))
                lines.append(f"  • {label}: {times}")

        return "\n".join(lines)


# Backwards compatibility for legacy imports
class AvailabilityCheckerV3(AvailabilityChecker):
    pass
