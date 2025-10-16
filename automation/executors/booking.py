"""Consolidated booking executors and related helpers."""

from __future__ import annotations
from tracking import t

import asyncio
import logging
import os
import random
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pytz
from playwright.async_api import Page

from automation.availability import DateTimeHelpers
from automation.browser.async_browser_pool import AsyncBrowserPool
from automation.forms.acuity_booking_form import AcuityBookingForm
from infrastructure.constants import BrowserTimeouts

from .core import AsyncExecutorConfig, DEFAULT_EXECUTOR_CONFIG, ExecutionResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _safe_sleep(seconds: float) -> None:
    """Sleep helper that clamps to non-negative values."""
    t('automation.executors.booking._safe_sleep')

    if seconds > 0:
        time.sleep(seconds)


# ---------------------------------------------------------------------------
# Working booking executor (baseline proven flow)
# ---------------------------------------------------------------------------

WORKING_SPEED_MULTIPLIER = 2.5


def _working_apply_speed(delay_seconds: float) -> float:
    t('automation.executors.booking._working_apply_speed')
    return max(0.1, delay_seconds / WORKING_SPEED_MULTIPLIER)


async def _working_human_type_with_mistakes(element, text: str, mistake_prob: float = 0.10) -> None:
    t('automation.executors.booking._working_human_type_with_mistakes')
    await element.click()
    await asyncio.sleep(_working_apply_speed(random.uniform(0.3, 0.8)))
    await element.fill("")
    await asyncio.sleep(_working_apply_speed(random.uniform(0.2, 0.5)))

    for i, char in enumerate(text):
        adjusted_mistake_prob = mistake_prob / max(1, WORKING_SPEED_MULTIPLIER * 0.5)

        if random.random() < adjusted_mistake_prob and i > 0:
            wrong_chars = "abcdefghijklmnopqrstuvwxyz"
            wrong_char = random.choice(wrong_chars)
            if wrong_char != char.lower():
                base_delay = random.randint(80, 180) / WORKING_SPEED_MULTIPLIER
                await element.type(wrong_char, delay=max(20, int(base_delay)))
                await asyncio.sleep(_working_apply_speed(random.uniform(0.1, 0.4)))
                await element.press("Backspace")
                await asyncio.sleep(_working_apply_speed(random.uniform(0.2, 0.6)))

        base_delay = random.randint(90, 220) / WORKING_SPEED_MULTIPLIER
        await element.type(char, delay=max(20, int(base_delay)))

        if random.random() < (0.2 / WORKING_SPEED_MULTIPLIER):
            await asyncio.sleep(_working_apply_speed(random.uniform(0.3, 1.2)))


async def _working_natural_mouse_movement(page: Page) -> None:
    t('automation.executors.booking._working_natural_mouse_movement')
    movement_count = max(1, int(random.randint(1, 2) / WORKING_SPEED_MULTIPLIER))
    for _ in range(movement_count):
        x = random.randint(200, 1000)
        y = random.randint(200, 700)
        await page.mouse.move(x, y)
        await asyncio.sleep(_working_apply_speed(random.uniform(0.2, 0.5)))
        if random.random() < (0.15 / WORKING_SPEED_MULTIPLIER):
            await asyncio.sleep(_working_apply_speed(random.uniform(0.5, 1.0)))


class BookingFlowExecutor:
    """Unified booking executor supporting natural and fast flows."""

    def __init__(self, browser_pool: Optional[Any] = None, mode: str = "natural") -> None:
        t('automation.executors.booking.BookingFlowExecutor.__init__')
        if mode not in {"natural", "fast"}:
            raise ValueError(f"Unknown booking flow mode: {mode}")

        self.browser_pool = browser_pool
        self.mode = mode
        self.logger = logging.getLogger("BookingFlowExecutor")

    async def execute_booking(
        self,
        court_number: int,
        target_date: datetime,
        time_slot: str,
        user_info: Dict[str, str],
    ) -> ExecutionResult:
        t('automation.executors.booking.BookingFlowExecutor.execute_booking')
        if not self.browser_pool:
            return ExecutionResult(success=False, error_message="Browser pool not initialized")

        try:
            page = await self.browser_pool.get_page(court_number)
            if not page:
                return ExecutionResult(
                    success=False,
                    error_message=f"Could not get page for court {court_number}",
                    court_number=court_number,
                )
            return await self._execute_booking_internal(page, court_number, target_date, time_slot, user_info)
        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.error("Booking execution error: %s", exc)
            return ExecutionResult(success=False, error_message=str(exc), court_number=court_number)

    async def _execute_booking_internal(
        self,
        page: Page,
        court_number: int,
        target_date: datetime,
        time_slot: str,
        user_info: Dict[str, str],
    ) -> ExecutionResult:
        t('automation.executors.booking.BookingFlowExecutor._execute_booking_internal')
        self.logger.info("Starting booking (%s mode): Court %s at %s on %s", self.mode, court_number, time_slot, target_date)

        if self.mode == "fast":
            return await self._execute_fast(page, court_number, target_date, time_slot, user_info)

        return await self._execute_natural(page, court_number, target_date, time_slot, user_info)

    async def _execute_natural(
        self,
        page: Page,
        court_number: int,
        target_date: datetime,
        time_slot: str,
        user_info: Dict[str, str],
    ) -> ExecutionResult:
        delay_min = getattr(self, "INITIAL_DELAY_MIN", 3.0)
        delay_max = getattr(self, "INITIAL_DELAY_MAX", 5.0)
        delay = random.uniform(delay_min, delay_max)
        self.logger.info("Initial natural delay (%.1f seconds)...", delay)
        await asyncio.sleep(delay)

        await _working_natural_mouse_movement(page)

        self.logger.info("Looking for %s time slot...", time_slot)
        time_button = await page.query_selector(f'button:has-text("{time_slot}")')

        if not time_button:
            alt_formats = [time_slot.replace(":00", ""), time_slot.split(":")[0]]
            for alt_time in alt_formats:
                time_button = await page.query_selector(f'button:has-text("{alt_time}")')
                if time_button:
                    break

        if not time_button:
            self.logger.error("Time slot %s not found", time_slot)
            return ExecutionResult(
                success=False,
                error_message=f"Time slot {time_slot} not found",
                court_number=court_number,
            )

        await asyncio.sleep(_working_apply_speed(random.uniform(0.3, 0.7)))
        await time_button.click()
        await asyncio.sleep(_working_apply_speed(random.uniform(0.4, 0.8)))

        form_present = await page.query_selector("form")
        if not form_present:
            self.logger.error("Booking form not found after selecting time slot")
            return ExecutionResult(
                success=False,
                error_message="Booking form not found",
                court_number=court_number,
            )

        await self._fill_form_natural(page, user_info)

        self.logger.info("Submitting booking form (natural mode)...")
        submit_button = await page.query_selector('button:has-text("Confirmar")')
        if not submit_button:
            submit_button = await page.query_selector('button:has-text("Confirm")')
        if submit_button:
            await submit_button.click()
            await asyncio.sleep(_working_apply_speed(random.uniform(1.0, 1.8)))

        confirmation_text = await page.text_content("body")
        if confirmation_text and "confirm" in confirmation_text.lower():
            self.logger.info("Booking confirmed for Court %s", court_number)
            return ExecutionResult(
                success=True,
                court_number=court_number,
                court_reserved=court_number,
                time_reserved=time_slot,
                user_name=user_info.get("first_name"),
            )

        self.logger.warning("Booking result uncertain for Court %s", court_number)
        return ExecutionResult(success=False, error_message="Booking confirmation not detected", court_number=court_number)

    async def _execute_fast(
        self,
        page: Page,
        court_number: int,
        target_date: datetime,
        time_slot: str,
        user_info: Dict[str, str],
    ) -> ExecutionResult:
        await _experienced_minimal_mouse_movement(page)

        target_date_str = target_date.strftime("%Y-%m-%d") if hasattr(target_date, "strftime") else str(target_date)
        target_datetime = None
        try:
            target_datetime = DateTimeHelpers.parse_reservation_datetime(target_date_str, time_slot)
        except Exception:  # pragma: no cover - defensive guard against malformed data
            target_datetime = None

        time_button = await _experienced_find_time_slot_with_refresh(
            page,
            time_slot,
            court_number,
            max_attempts=5,
            refresh_delay=0.6,
            log=self.logger,
            target_datetime=target_datetime,
        )
        if not time_button:
            return ExecutionResult(
                success=False,
                error_message=f"Time slot {time_slot} not available",
                court_number=court_number,
            )

        await time_button.click()
        await asyncio.sleep(_experienced_apply_speed(0.3))

        await self._fill_form_fast(page, user_info)

        submit_button = await page.query_selector('button:has-text("Confirmar")')
        if submit_button:
            await submit_button.click()

        await asyncio.sleep(_experienced_apply_speed(1.0))
        confirmation_text = await page.text_content("body")
        if confirmation_text and "confirm" in confirmation_text.lower():
            return ExecutionResult(
                success=True,
                court_number=court_number,
                court_reserved=court_number,
                time_reserved=time_slot,
                user_name=user_info.get("first_name"),
            )

        return ExecutionResult(success=False, error_message="Booking confirmation not detected", court_number=court_number)

    async def _fill_form_natural(self, page: Page, user_info: Dict[str, str]) -> None:
        first_name = user_info.get("first_name", "")
        last_name = user_info.get("last_name", "")
        email = user_info.get("email", "")
        phone = user_info.get("phone", "")

        first_name_field = await page.query_selector('input[name="client.firstName"]')
        last_name_field = await page.query_selector('input[name="client.lastName"]')
        email_field = await page.query_selector('input[name="client.email"]')
        phone_field = await page.query_selector('input[name="client.phone"]')

        if first_name_field:
            await _working_human_type_with_mistakes(first_name_field, first_name)
        if last_name_field:
            await _working_human_type_with_mistakes(last_name_field, last_name)
        if email_field:
            await _working_human_type_with_mistakes(email_field, email)
        if phone_field:
            await _working_human_type_with_mistakes(phone_field, phone)

    async def _fill_form_fast(self, page: Page, user_info: Dict[str, str]) -> None:
        fields = {
            'input[name="client.firstName"]': user_info.get("first_name", ""),
            'input[name="client.lastName"]': user_info.get("last_name", ""),
            'input[name="client.email"]': user_info.get("email", ""),
            'input[name="client.phone"]': user_info.get("phone", ""),
        }

        for selector, value in fields.items():
            element = await page.query_selector(selector)
            if element:
                await _experienced_fast_fill(element, value)


# ---------------------------------------------------------------------------
# Experienced booking executor (fast variant)
# ---------------------------------------------------------------------------

EXPERIENCED_SPEED_MULTIPLIER = 3.0
PRODUCTION_MODE = os.getenv("PRODUCTION_MODE", "false").lower() == "true"


def _experienced_apply_speed(delay_seconds: float) -> float:
    t('automation.executors.booking._experienced_apply_speed')
    return max(0.05, delay_seconds / EXPERIENCED_SPEED_MULTIPLIER)


async def _experienced_take_screenshot_if_dev(
    page: Page,
    filename_prefix: str,
    court_number: int,
    log: logging.Logger,
) -> Optional[str]:
    t('automation.executors.booking._experienced_take_screenshot_if_dev')
    if PRODUCTION_MODE:
        log.debug("Screenshot skipped in production mode: %s", filename_prefix)
        return None

    try:
        screenshot_dir = os.path.join(os.path.dirname(__file__), "..", "logs", "screenshots")
        os.makedirs(screenshot_dir, exist_ok=True)
        screenshot_path = os.path.join(
            screenshot_dir,
            f"{filename_prefix}_court{court_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
        )
        await page.screenshot(path=screenshot_path)
        log.info("Screenshot saved: %s", screenshot_path)
        return screenshot_path
    except Exception as exc:  # pragma: no cover - defensive guard
        log.debug("Could not save screenshot: %s", exc)
        return None


async def _experienced_fast_fill(element, text: str) -> None:
    t('automation.executors.booking._experienced_fast_fill')
    await element.click()
    await asyncio.sleep(0.05)
    await element.fill("")
    await asyncio.sleep(0.05)
    await element.fill(text)
    await asyncio.sleep(0.1)


async def _experienced_minimal_mouse_movement(page: Page) -> None:
    t('automation.executors.booking._experienced_minimal_mouse_movement')
    x = random.randint(400, 800)
    y = random.randint(300, 600)
    await page.mouse.move(x, y)
    await asyncio.sleep(0.1)


async def _experienced_find_time_slot_with_refresh(
    page: Page,
    time_slot: str,
    court_number: int,
    max_attempts: int,
    refresh_delay: float,
    log: logging.Logger,
    target_datetime: Optional[datetime] = None,
) -> Optional[Any]:
    t('automation.executors.booking._experienced_find_time_slot_with_refresh')
    if target_datetime:
        booking_window_opens = DateTimeHelpers.get_booking_window_open_time(target_datetime, 48)
        current_time = datetime.now(target_datetime.tzinfo)
        pre_window_attempts = 0
        while current_time < booking_window_opens:
            time_until_window = (booking_window_opens - current_time).total_seconds()
            if time_until_window <= 30:
                log.info(
                    "Court %s: PRE-WINDOW PHASE - Attempt #%s (%.1fs until official window)",
                    court_number,
                    pre_window_attempts + 1,
                    time_until_window,
                )
                pre_window_attempts += 1

                try:
                    button = await page.query_selector(f'button.time-selection:has(p:text("{time_slot}"))')
                    if button and await button.is_visible() and await button.is_enabled():
                        log.info("Court %s: Time slot appeared early; waiting for window", court_number)
                        await asyncio.sleep(max(0, time_until_window))
                        if await button.is_visible() and await button.is_enabled():
                            log.info("Court %s: Window open, clicking now", court_number)
                            return button
                except Exception:  # pragma: no cover - DOM race
                    pass

                for time_format in [time_slot, time_slot.replace(":00", "")]:
                    try:
                        button = await page.query_selector(f'button:has-text("{time_format}")')
                        if button and await button.is_visible() and await button.is_enabled():
                            await asyncio.sleep(max(0, time_until_window))
                            if await button.is_visible() and await button.is_enabled():
                                return button
                    except Exception:  # pragma: no cover
                        pass

                try:
                    await page.reload(wait_until="domcontentloaded")
                    await asyncio.sleep(0.5)
                except Exception as exc:
                    log.debug("Pre-window refresh error: %s", exc)
                    await asyncio.sleep(0.5)
            else:
                log.info("Court %s: Waiting... Opens in %.0fs", court_number, time_until_window)
                await asyncio.sleep(min(5.0, time_until_window - 30))

            current_time = datetime.now(target_datetime.tzinfo)

        log.info("Court %s: Booking window officially open", court_number)

    attempt = 0
    time_formats = [time_slot, time_slot.replace(":00", "")]

    try:
        button = await page.query_selector(f'button.time-selection:has(p:text("{time_slot}"))')
        if button and await button.is_visible() and await button.is_enabled():
            return button
    except Exception:  # pragma: no cover
        pass

    while attempt < max_attempts:
        attempt += 1
        log.info("Court %s: Attempt %s/%s to find %s", court_number, attempt, max_attempts, time_slot)
        await _experienced_take_screenshot_if_dev(page, f"time_search_attempt{attempt}", court_number, log)

        for time_format in time_formats:
            try:
                button = await page.query_selector(f'button:has-text("{time_format}")')
                if button and await button.is_visible() and await button.is_enabled():
                    return button
            except Exception:  # pragma: no cover
                pass

        try:
            await page.reload(wait_until="domcontentloaded")
        except Exception as exc:
            log.debug("Refresh attempt error: %s", exc)
        await asyncio.sleep(refresh_delay)

    return None


# ---------------------------------------------------------------------------
# Async booking executor (multi-court orchestration)
# ---------------------------------------------------------------------------

class AsyncBookingExecutor:
    """Async booking executor that orchestrates bookings across courts."""

    TIMEOUTS = {
        "total_execution": 60.0,
        "navigation": 15.0,
        "form_filling": 20.0,
        "confirmation": 10.0,
        "element_wait": 5.0,
        "health_check": 2.0,
        "form_detection": 3.0,
    }

    def __init__(self, browser_pool: Optional[Any] = None, use_natural_flow: bool = False, experienced_mode: bool = True) -> None:
        t('automation.executors.booking.AsyncBookingExecutor.__init__')
        self.browser_pool = browser_pool
        self.use_natural_flow = use_natural_flow
        self.experienced_mode = experienced_mode
        self.logger = logging.getLogger(self.__class__.__name__)

        mode = "natural" if use_natural_flow else ("fast" if experienced_mode else "natural")
        self._flow_executor = BookingFlowExecutor(browser_pool, mode=mode)

    async def execute_parallel_booking(
        self,
        court_numbers: List[int],
        time_slot: str,
        user_info: Dict[str, str],
        target_date: datetime,
        max_concurrent: int = 3,
    ) -> Dict[str, Any]:
        t('automation.executors.booking.AsyncBookingExecutor.execute_parallel_booking')
        self.logger.info("Starting parallel booking for courts %s at %s", court_numbers, time_slot)

        tasks: List[Tuple[int, asyncio.Task]] = []
        for court_number in court_numbers[:max_concurrent]:
            task = asyncio.create_task(
                self.execute_booking(court_number, time_slot, user_info, target_date),
                name=f"court_{court_number}_booking",
            )
            tasks.append((court_number, task))

        results: Dict[int, ExecutionResult] = {}
        successful_court: Optional[int] = None

        try:
            for court_number, task in tasks:
                try:
                    result = await asyncio.wait_for(task, timeout=self.TIMEOUTS["total_execution"])
                    results[court_number] = result

                    if result.success and not successful_court:
                        successful_court = court_number
                        self.logger.info("✅ Successfully booked Court %s!", court_number)
                        for other_court, other_task in tasks:
                            if other_court != court_number and not other_task.done():
                                other_task.cancel()
                        break
                except asyncio.TimeoutError:
                    self.logger.error("Court %s booking timed out", court_number)
                    results[court_number] = ExecutionResult(
                        success=False,
                        error_message="Booking timed out",
                        court_attempted=court_number,
                        court_number=court_number,
                    )
                except Exception as exc:  # pragma: no cover - defensive guard
                    self.logger.error("Court %s booking failed: %s", court_number, exc)
                    results[court_number] = ExecutionResult(
                        success=False,
                        error_message=str(exc),
                        court_attempted=court_number,
                        court_number=court_number,
                    )

            remaining_tasks = [task for _, task in tasks if not task.done()]
            if remaining_tasks:
                await asyncio.gather(*remaining_tasks, return_exceptions=True)
        finally:
            pass

        return {
            "success": successful_court is not None,
            "successful_court": successful_court,
            "results": results,
            "courts_attempted": court_numbers,
        }

    async def execute_booking(
        self,
        court_number: int,
        time_slot: str,
        user_info: Dict[str, str],
        target_date: datetime,
    ) -> ExecutionResult:
        t('automation.executors.booking.AsyncBookingExecutor.execute_booking')
        if not self.browser_pool:
            return ExecutionResult(success=False, error_message="Browser pool not initialized", court_number=court_number)

        try:
            return await self._flow_executor.execute_booking(court_number, target_date, time_slot, user_info)
        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.error("Booking failed for court %s: %s", court_number, exc)
            return ExecutionResult(success=False, error_message=str(exc), court_number=court_number)


# ---------------------------------------------------------------------------
# Unified async booking executor facade
# ---------------------------------------------------------------------------

class UnifiedAsyncBookingExecutor:
    """Route booking requests to the appropriate executor based on config."""

    def __init__(self, browser_pool: Optional[Any] = None, config: AsyncExecutorConfig = DEFAULT_EXECUTOR_CONFIG) -> None:
        t('automation.executors.booking.UnifiedAsyncBookingExecutor.__init__')
        self.config = config
        self.browser_pool = browser_pool
        self._executor = self._build_executor()

    def _build_executor(self) -> Any:
        t('automation.executors.booking.UnifiedAsyncBookingExecutor._build_executor')
        use_natural = self.config.natural_flow
        use_fast = self.config.use_experienced_mode or self.config.use_smart_navigation

        return AsyncBookingExecutor(
            browser_pool=self.browser_pool,
            use_natural_flow=use_natural,
            experienced_mode=use_fast,
        )

    def __getattr__(self, item: str) -> Any:
        t('automation.executors.booking.UnifiedAsyncBookingExecutor.__getattr__')
        return getattr(self._executor, item)

    def with_config(self, config: AsyncExecutorConfig) -> "UnifiedAsyncBookingExecutor":
        t('automation.executors.booking.UnifiedAsyncBookingExecutor.with_config')
        return UnifiedAsyncBookingExecutor(browser_pool=self.browser_pool, config=config)


__all__ = [
    "AsyncBookingExecutor",
    "BookingFlowExecutor",
    "UnifiedAsyncBookingExecutor",
]
