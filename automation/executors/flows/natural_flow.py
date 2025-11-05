"""Natural (human-like) booking flow implementation."""

from __future__ import annotations
from tracking import t

import asyncio
import logging
import random
from datetime import datetime
from typing import Dict, Tuple, Optional

from playwright.async_api import Page

from automation.executors.core import ExecutionResult
from automation.debug import get_logger

from .helpers import confirmation_result
from .human_behaviors import HumanLikeActions

WORKING_SPEED_MULTIPLIER = 1.5  # Conservative speed to avoid detection
_VALIDATION_SLEEP = (0.3, 0.6)  # More natural validation pauses
_MOUSE_DELAY = (0.15, 0.35)     # Natural mouse delays
_FIELD_LINGER = (0.5, 0.9)      # Natural field review time


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
        time_button = await self.select_time_button(time_slot)
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

        await self.actions.click_with_hesitation(
            time_button,
            hesitation_prob=0.6,              # Natural hesitation before committing
            correction_count_range=(0, 1)     # Sometimes correct cursor position
        )

        await self.actions.pause(*_VALIDATION_SLEEP)

        try:
            await self.page.wait_for_selector("form", timeout=8000)
            await self.debug_logger.capture_state(self.page, "03_after_time_click_form_loaded")
        except Exception:
            self.logger.error("Booking form not found after selecting time slot")
            await self.debug_logger.capture_state(self.page, "03_ERROR_no_form_after_click")
            return ExecutionResult(
                success=False,
                error_message="Booking form not found",
                court_number=court_number,
            )

        form_present = await self.page.query_selector("form")
        if not form_present:
            self.logger.error("Booking form not found after selecting time slot")
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
