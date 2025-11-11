"""Natural (human-like) booking flow implementation."""

from __future__ import annotations
from tracking import t

import asyncio
import logging
import random
from datetime import date, datetime, timedelta
from typing import Dict, Tuple, Optional, Union

from playwright.async_api import Page

from automation.executors.core import ExecutionResult
from automation.debug import get_logger

from .helpers import build_direct_slot_url, confirmation_result
from .human_behaviors import HumanLikeActions

WORKING_SPEED_MULTIPLIER = 1.5  # Conservative speed to avoid detection
_VALIDATION_SLEEP = (0.3, 0.6)  # More natural validation pauses
_MOUSE_DELAY = (0.15, 0.35)     # Natural mouse delays
_FIELD_LINGER = (0.5, 0.9)      # Natural field review time
_REFRESH_DELAY = (0.35, 0.65)
_MAX_REFRESH_WITHOUT_TARGET = 15
_POST_SLOT_GRACE_SECONDS = 6
_TARGET_POLL_INTERVAL = (0.25, 0.45)
_MAX_POST_TARGET_REFRESHES = 5
_QUEUE_RELEASE_OFFSET = timedelta(hours=48)


class NaturalFlowSteps:
    """Encapsulates the human-like steps used by the natural booking flow."""

    def __init__(self, page: Page, logger: logging.Logger) -> None:
        t("automation.executors.flows.natural_flow.NaturalFlowSteps.__init__")
        self.page = page
        self.logger = logger
        self.actions = HumanLikeActions(page, speed_multiplier=WORKING_SPEED_MULTIPLIER)
        self.debug_logger = get_logger()
        self.debug_logger.attach_listeners(page)

    async def type_text(self, element, text: str) -> None:
        t("automation.executors.flows.natural_flow.NaturalFlowSteps.type_text")
        await self.actions.type_text(element, text or "")

    async def _scroll_into_view(self, selector: str) -> Optional[object]:
        t('automation.executors.flows.natural_flow.NaturalFlowSteps._scroll_into_view')
        try:
            element = await self.page.wait_for_selector(selector, timeout=6000)
            await element.scroll_into_view_if_needed()
            await self.actions.pause(0.3, 0.6)  # Natural scroll pause
            return element
        except Exception:
            return None

    async def move_mouse(self) -> None:
        t("automation.executors.flows.natural_flow.NaturalFlowSteps.move_mouse")
        await self.actions.move_mouse_random()

    async def fill_user_form(self, user_info: Dict[str, str]) -> None:
        t("automation.executors.flows.natural_flow.NaturalFlowSteps.fill_user_form")
        selectors = (
            ("first_name", 'input[name="client.firstName"]'),
            ("last_name", 'input[name="client.lastName"]'),
            ("email", 'input[name="client.email"]'),
            ("phone", 'input[name="client.phone"]'),
        )

        for key, selector in selectors:
            element = await self._scroll_into_view(selector)
            if not element:
                continue
            value = user_info.get(key, "")
            if key == "phone":
                await element.click()
                await self.actions.pause(0.4, 0.7)
                await element.fill(str(value))
                await self.actions.pause(0.6, 1.0)
            else:
                await self.actions.type_text(element, str(value))
                await self.actions.pause(*_FIELD_LINGER)
            await self.actions.move_mouse_random()

        try:
            country_select = await self.page.query_selector('select[name="client.phoneCountry"]')
            if country_select and not await country_select.get_attribute("value"):
                await country_select.select_option("GT")
                await self.actions.pause(0.4, 0.8)
        except Exception:
            pass

    async def select_time_button(self, time_slot: str):
        t("automation.executors.flows.natural_flow.NaturalFlowSteps.select_time_button")
        button = await self.page.query_selector(f'button:has-text("{time_slot}")')
        if button:
            return button

        alt_formats = [time_slot.replace(":00", ""), time_slot.split(":")[0]]
        for alt_time in alt_formats:
            button = await self.page.query_selector(f'button:has-text("{alt_time}")')
            if button:
                return button
        return None

    async def submit(self) -> None:
        t("automation.executors.flows.natural_flow.NaturalFlowSteps.submit")
        submit_button = await self.page.query_selector('button:has-text("Confirmar")')
        if not submit_button:
            submit_button = await self.page.query_selector('button:has-text("Confirm")')
        if submit_button:
            # Natural pause before submission - review the form
            await self.actions.reading_pause(duration_range=(1.0, 2.0))  # Review form before submit
            await self.actions.click_with_hesitation(
                submit_button,
                hesitation_prob=0.5,              # Natural hesitation
                correction_count_range=(0, 1)     # Occasional corrections
            )
            await self.actions.pause(1.0, 1.5)  # Wait for page to respond

    async def execute(
        self,
        court_number: int,
        target_date: datetime,
        time_slot: str,
        user_info: Dict[str, str],
        *,
        initial_delay_range: Tuple[float, float],
    ) -> ExecutionResult:
        t("automation.executors.flows.natural_flow.NaturalFlowSteps.execute")
        delay_min, delay_max = initial_delay_range
        delay = random.uniform(delay_min, delay_max)
        self.logger.info("Initial natural delay (%.1f seconds)...", delay)
        await self.actions.pause(delay, delay)

        # Natural page interaction (natural scroll + reading)
        self.logger.info("Performing natural page interaction (scroll + reading)...")
        await self.debug_logger.capture_state(self.page, "01_initial_page_load")

        await self.actions.scroll_naturally(
            scroll_count_range=(2, 3),      # Natural scrolling to review page
            scroll_amount_range=(150, 350), # Natural scroll amounts
            scroll_back_prob=0.2            # Sometimes scroll back to review
        )
        await self.actions.reading_pause(duration_range=(1.5, 3.0))  # Read the page content

        await self.move_mouse()

        self.logger.info("Looking for %s time slot...", time_slot)
        target_datetime = self._resolve_slot_datetime(target_date, time_slot)
        release_datetime = self._resolve_release_datetime(target_datetime)
        time_button = await self._wait_for_time_slot(
            time_slot,
            court_number,
            target_datetime=target_datetime,
            release_datetime=release_datetime,
        )
        if not time_button:
            self.logger.error("Time slot %s not found", time_slot)
            return ExecutionResult(
                success=False,
                error_message=f"Time slot {time_slot} not found",
                court_number=court_number,
            )

        await self.actions.pause(*_VALIDATION_SLEEP)

        # Click time slot with natural hesitation
        self.logger.info("Clicking time slot...")
        await self.debug_logger.capture_state(self.page, "02_before_time_click")

        await self._commit_time_selection(time_button)

        form_ready = await self._ensure_booking_form_visible(
            court_number=court_number,
            target_date=target_date,
            time_slot=time_slot,
        )
        if not form_ready:
            return ExecutionResult(
                success=False,
                error_message="Booking form not found",
                court_number=court_number,
            )

        await self.fill_user_form(user_info)
        await self.debug_logger.capture_state(self.page, "04_after_form_fill")

        await self.actions.pause(1.2, 2.0)  # Review form after filling
        await self.actions.move_mouse_random()
        self.logger.info("Submitting booking form (natural mode)...")
        await self.debug_logger.capture_state(self.page, "05_before_submit")

        await self.submit()
        await self.debug_logger.capture_state(self.page, "06_after_submit")

        result = await confirmation_result(
            self.page,
            court_number,
            time_slot,
            user_info,
            logger=self.logger,
            success_log="Booking confirmed for Court %s",
            failure_log="Booking result uncertain for Court %s",
        )

        await self.debug_logger.capture_state(self.page, "07_final_result")
        self.debug_logger.save_logs()
        self.debug_logger.print_summary()

        return result

    def _resolve_slot_datetime(
        self,
        target_date: Union[datetime, date],
        time_slot: str,
    ) -> Optional[datetime]:
        """Build a datetime for the target slot to know when to stop refreshing."""

        t("automation.executors.flows.natural_flow.NaturalFlowSteps._resolve_slot_datetime")
        try:
            slot_time = datetime.strptime(time_slot, "%H:%M").time()
        except ValueError:
            return None

        tzinfo = target_date.tzinfo if isinstance(target_date, datetime) else None
        base_date = target_date.date() if isinstance(target_date, datetime) else target_date

        resolved = datetime.combine(base_date, slot_time)
        if tzinfo is not None:
            resolved = resolved.replace(tzinfo=tzinfo)
        return resolved

    def _resolve_release_datetime(
        self,
        target_datetime: Optional[datetime],
    ) -> Optional[datetime]:
        """Return release datetime (48h before target) when applicable."""

        t("automation.executors.flows.natural_flow.NaturalFlowSteps._resolve_release_datetime")
        if not target_datetime:
            return None

        tzinfo = target_datetime.tzinfo
        now = datetime.now(tzinfo) if tzinfo else datetime.now()
        delta = target_datetime - now

        if delta >= (_QUEUE_RELEASE_OFFSET - timedelta(minutes=1)):
            release = target_datetime - _QUEUE_RELEASE_OFFSET
            if release < now:
                return None
            return release
        return None

    async def _wait_for_time_slot(
        self,
        time_slot: str,
        court_number: int,
        *,
        target_datetime: Optional[datetime],
        release_datetime: Optional[datetime],
    ):
        """Refresh the calendar until the desired time slot appears."""

        t("automation.executors.flows.natural_flow.NaturalFlowSteps._wait_for_time_slot")
        refresh_count = 0
        deadline = (
            target_datetime + timedelta(seconds=_POST_SLOT_GRACE_SECONDS)
            if target_datetime
            else None
        )

        button = await self.select_time_button(time_slot)
        if button:
            if target_datetime:
                now = (
                    datetime.now(target_datetime.tzinfo)
                    if target_datetime and target_datetime.tzinfo
                    else datetime.now()
                )
                if now < target_datetime:
                    self.logger.info(
                        "Time slot %s became visible %.2fs before target for Court %s - booking immediately",
                        time_slot,
                        (target_datetime - now).total_seconds(),
                        court_number,
                    )
                else:
                    self.logger.info(
                        "Time slot %s already visible at release time for Court %s - booking immediately",
                        time_slot,
                        court_number,
                    )
            else:
                self.logger.info("Time slot %s already visible for Court %s - booking immediately", time_slot, court_number)
            return button

        wait_point = release_datetime or target_datetime
        tzinfo = wait_point.tzinfo if isinstance(wait_point, datetime) else None
        now = datetime.now(tzinfo) if tzinfo else datetime.now()
        if wait_point and now < wait_point:
            wait_seconds = (wait_point - now).total_seconds()
            self.logger.info(
                "Arrived %.2fs before %s for Court %s - waiting before slot scan",
                wait_seconds,
                "release" if release_datetime else "target",
                court_number,
            )

            while now < wait_point:
                remaining = max((wait_point - now).total_seconds(), 0)
                sleep_for = min(
                    _TARGET_POLL_INTERVAL[1],
                    max(_TARGET_POLL_INTERVAL[0], remaining),
                )
                await asyncio.sleep(sleep_for)
                now = datetime.now(tzinfo) if tzinfo else datetime.now()

        max_refreshes = (
            _MAX_POST_TARGET_REFRESHES
            if target_datetime
            else _MAX_REFRESH_WITHOUT_TARGET
        )

        while True:
            button = await self.select_time_button(time_slot)
            if button:
                if refresh_count:
                    self.logger.info(
                        "Time slot %s appeared after %s refresh(es) for Court %s",
                        time_slot,
                        refresh_count,
                        court_number,
                    )
                return button

            now = (
                datetime.now(target_datetime.tzinfo)
                if target_datetime and target_datetime.tzinfo
                else datetime.now()
            )

            if refresh_count >= max_refreshes:
                break

            refresh_count += 1

            if deadline and now > deadline:
                break

            self.logger.info(
                "Time slot %s not visible yet for Court %s - refreshing (attempt %s)",
                time_slot,
                court_number,
                refresh_count,
            )
            await self._refresh_time_grid(refresh_count)

        return None

    async def _refresh_time_grid(self, attempt: int) -> None:
        """Reload the time grid and wait naturally between refreshes."""

        t("automation.executors.flows.natural_flow.NaturalFlowSteps._refresh_time_grid")
        try:
            await self.debug_logger.capture_state(
                self.page, f"refresh_wait_{attempt:02d}"
            )
        except Exception:
            pass

        try:
            await self.page.reload(wait_until="domcontentloaded")
        except Exception as exc:
            self.logger.debug("Refresh attempt %s failed: %s", attempt, exc)
        await self.actions.pause(*_REFRESH_DELAY)

    async def _commit_time_selection(self, button) -> None:
        """Click a time button with human-like hesitation."""

        await self.actions.click_with_hesitation(
            button,
            hesitation_prob=0.6,
            correction_count_range=(0, 1),
        )
        await self.actions.pause(*_VALIDATION_SLEEP)

    async def _ensure_booking_form_visible(
        self,
        *,
        court_number: int,
        target_date: datetime,
        time_slot: str,
    ) -> bool:
        """Ensure the booking form renders, trying recovery strategies when missing."""

        if await self._wait_for_form_once("03_after_time_click_form_loaded"):
            return True

        self.logger.warning(
            "Booking form not found after selecting time slot %s for Court %s - attempting recovery",
            time_slot,
            court_number,
        )
        await self.debug_logger.capture_state(self.page, "03_ERROR_no_form_after_click")

        if await self._reload_and_retry_time_slot(time_slot):
            return True

        return await self._navigate_direct_slot(
            court_number=court_number,
            target_date=target_date,
            time_slot=time_slot,
        )

    async def _wait_for_form_once(self, label: str, timeout: int = 8000) -> bool:
        """Wait for a booking form element to appear once."""

        try:
            await self.page.wait_for_selector("form", timeout=timeout)
            await self.debug_logger.capture_state(self.page, label)
            form_present = await self.page.query_selector("form")
            return form_present is not None
        except Exception:
            return False

    async def _reload_and_retry_time_slot(self, time_slot: str) -> bool:
        """Reload the calendar and try clicking the time slot again."""

        self.logger.info("Reloading page to retry time selection for %s", time_slot)
        try:
            await self.page.reload(wait_until="domcontentloaded")
        except Exception as exc:
            self.logger.warning("Page reload failed during booking-form recovery: %s", exc)
            return False

        await self.actions.pause(0.8, 1.2)
        retry_button = await self.select_time_button(time_slot)
        if not retry_button:
            self.logger.warning("Time slot %s no longer visible after refresh", time_slot)
            return False

        await self._commit_time_selection(retry_button)
        recovered = await self._wait_for_form_once(
            "03_after_time_click_form_loaded_retry",
            timeout=6000,
        )
        if not recovered:
            self.logger.warning("Booking form still missing after refresh retry")
        return recovered

    async def _navigate_direct_slot(
        self,
        *,
        court_number: int,
        target_date: datetime,
        time_slot: str,
    ) -> bool:
        """Jump straight to the slot URL if inline interaction never surfaces the form."""

        try:
            direct_url = build_direct_slot_url(court_number, target_date, time_slot)
        except Exception as exc:
            self.logger.error(
                "Unable to build direct slot URL for court %s (%s at %s): %s",
                court_number,
                target_date.date(),
                time_slot,
                exc,
            )
            return False

        self.logger.warning(
            "Direct slot fallback engaged for Court %s (%s @ %s)",
            court_number,
            target_date.date(),
            time_slot,
        )

        try:
            await self.page.goto(
                direct_url,
                wait_until="domcontentloaded",
                timeout=30000,
            )
        except Exception as exc:
            self.logger.error("Direct slot navigation failed: %s", exc)
            return False

        recovered = await self._wait_for_form_once(
            "03_after_direct_nav_form_loaded",
            timeout=10000,
        )
        if not recovered:
            self.logger.error("Booking form still unavailable after direct slot navigation")
        return recovered


async def execute_natural_flow(
    page: Page,
    court_number: int,
    target_date: datetime,
    time_slot: str,
    user_info: Dict[str, str],
    *,
    logger: logging.Logger,
    initial_delay_range: Tuple[float, float],
) -> ExecutionResult:
    """Execute the natural booking flow and return the result."""

    t("automation.executors.flows.natural_flow.execute_natural_flow")
    steps = NaturalFlowSteps(page, logger)
    return await steps.execute(
        court_number,
        target_date,
        time_slot,
        user_info,
        initial_delay_range=initial_delay_range,
    )


__all__ = [
    "WORKING_SPEED_MULTIPLIER",
    "NaturalFlowSteps",
    "execute_natural_flow",
]
