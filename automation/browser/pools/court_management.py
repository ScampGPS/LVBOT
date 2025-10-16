"""Court assignment and switching utilities for specialized browser pools."""

from __future__ import annotations
from utils.tracking import t

import logging
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from infrastructure.constants import COURT_CONFIG, BrowserTimeouts


@dataclass
class CourtStats:
    attempts: int = 0
    successes: int = 0


class CourtPoolManager:
    """Track browser-to-court assignments with simple heuristics."""

    def __init__(self, primary_courts: Iterable[int], fallback_court: Optional[int] = None) -> None:
        t('automation.browser.pools.court_management.CourtPoolManager.__init__')
        self.logger = logging.getLogger("CourtPoolManager")
        primary = list(dict.fromkeys(primary_courts))
        extra = [fallback_court] if fallback_court else []
        self.all_courts: List[int] = [c for c in primary + extra if c is not None]
        if not self.all_courts:
            raise ValueError("CourtPoolManager requires at least one court")
        self.primary_courts = primary or self.all_courts[:]
        self._court_to_browser: Dict[int, str] = {}
        self._browser_to_court: Dict[str, int] = {}
        self._stats: Dict[int, CourtStats] = {court: CourtStats() for court in self.all_courts}

    def reset(self) -> None:
        t('automation.browser.pools.court_management.CourtPoolManager.reset')
        self._court_to_browser.clear()
        self._browser_to_court.clear()
        for stats in self._stats.values():
            stats.attempts = 0
            stats.successes = 0

    def assign_browser_to_court(self, browser_id: str, court: int) -> None:
        t('automation.browser.pools.court_management.CourtPoolManager.assign_browser_to_court')
        previous = self._browser_to_court.get(browser_id)
        if previous == court:
            return
        if previous is not None:
            self._court_to_browser.pop(previous, None)
        self._browser_to_court[browser_id] = court
        self._court_to_browser[court] = browser_id

    def get_browser_for_court(self, court: int) -> Optional[str]:
        t('automation.browser.pools.court_management.CourtPoolManager.get_browser_for_court')
        return self._court_to_browser.get(court)

    def get_court_for_browser(self, browser_id: str) -> Optional[int]:
        t('automation.browser.pools.court_management.CourtPoolManager.get_court_for_browser')
        return self._browser_to_court.get(browser_id)

    def get_court_assignment_strategy(self, preferences: Iterable[int]) -> List[int]:
        t('automation.browser.pools.court_management.CourtPoolManager.get_court_assignment_strategy')
        ordered: List[int] = []
        seen = set()
        for court in preferences:
            if court in self.all_courts and court not in seen:
                ordered.append(court)
                seen.add(court)
        # Add remaining courts, favouring ones with fewer attempts
        remaining = [c for c in self.all_courts if c not in seen]
        remaining.sort(key=lambda c: (self._stats[c].attempts, -self._stats[c].successes))
        ordered.extend(remaining)
        return ordered

    def record_booking_result(self, browser_id: str, court: int, success: bool, user_id: Optional[int] = None) -> None:
        t('automation.browser.pools.court_management.CourtPoolManager.record_booking_result')
        stats = self._stats.setdefault(court, CourtStats())
        stats.attempts += 1
        if success:
            stats.successes += 1
        # Ensure mapping reflects latest assignment
        if success:
            self.assign_browser_to_court(browser_id, court)

    def get_next_court_assignment(self, booked_court: int, browser_id: str) -> Optional[int]:
        t('automation.browser.pools.court_management.CourtPoolManager.get_next_court_assignment')
        candidates = [c for c in self.all_courts if c != booked_court]
        for court in candidates:
            if self.get_browser_for_court(court) is None:
                return court
        return candidates[0] if candidates else None

    def get_status_summary(self) -> Dict[int, Dict[str, int]]:
        t('automation.browser.pools.court_management.CourtPoolManager.get_status_summary')
        summary: Dict[int, Dict[str, int]] = {}
        for court in self.all_courts:
            stats = self._stats[court]
            summary[court] = {
                "browser": self._court_to_browser.get(court, "-"),
                "attempts": stats.attempts,
                "successes": stats.successes,
            }
        return summary


class BrowserCourtSwitcher:
    """Lightweight helper to reposition Playwright pages between courts."""

    def __init__(self, navigation_timeout: int = BrowserTimeouts.SLOW_NAVIGATION) -> None:
        t('automation.browser.pools.court_management.BrowserCourtSwitcher.__init__')
        self.logger = logging.getLogger("BrowserCourtSwitcher")
        self.navigation_timeout = navigation_timeout

    async def switch_court(self, page, current_court: int, target_court: int, browser_id: str) -> Dict[str, object]:
        t('automation.browser.pools.court_management.BrowserCourtSwitcher.switch_court')
        target = COURT_CONFIG.get(target_court, {})
        url = target.get("direct_url")
        if not url:
            return {"success": False, "error": f"No direct URL configured for court {target_court}"}
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=self.navigation_timeout)
            return {"success": True, "url": page.url}
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.error("Browser %s failed to navigate to court %s: %s", browser_id, target_court, exc)
            return {"success": False, "error": str(exc)}

    async def verify_browser_health(self, page, court: int) -> Dict[str, object]:
        t('automation.browser.pools.court_management.BrowserCourtSwitcher.verify_browser_health')
        expected = COURT_CONFIG.get(court, {}).get("direct_url")
        try:
            current_url = page.url
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.debug("Could not read page URL for court %s: %s", court, exc)
            return {"positioned": False, "url": None}
        positioned = bool(expected and expected in current_url)
        return {"positioned": positioned, "url": current_url}
