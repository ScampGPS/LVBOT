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

from .helpers import confirmation_result
from .human_behaviors import HumanLikeActions

WORKING_SPEED_MULTIPLIER = 2.5
_VALIDATION_SLEEP = (0.3, 0.8)
_MOUSE_DELAY = (0.2, 0.5)
_FIELD_LINGER = (0.6, 1.4)


class NaturalFlowSteps:
    """Encapsulates the human-like steps used by the natural booking flow."""

    def __init__(self, page: Page, logger: logging.Logger) -> None:
        t("automation.executors.flows.natural_flow.NaturalFlowSteps.__init__")
        self.page = page
        self.logger = logger
        self.actions = HumanLikeActions(page, speed_multiplier=WORKING_SPEED_MULTIPLIER)

    async def type_text(self, element, text: str) -> None:
        t("automation.executors.flows.natural_flow.NaturalFlowSteps.type_text")
        await self.actions.type_text(element, text or "")

    async def _scroll_into_view(self, selector: str) -> Optional[object]:
        try:
            element = await self.page.wait_for_selector(selector, timeout=6000)
            await element.scroll_into_view_if_needed()
            await self.actions.pause(0.4, 1.0)
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
            await self.actions.type_text(element, user_info.get(key, ""))
            await self.actions.pause(*_FIELD_LINGER)
            await self.actions.move_mouse_random()

        try:
            country_select = await self.page.query_selector('select[name="client.phoneCountry"]')
            if country_select and not await country_select.get_attribute("value"):
                await country_select.select_option("GT")
                await self.actions.pause(0.4, 0.9)
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
            await self.actions.move_mouse_to_element(submit_button)
            await self.actions.pause(1.0, 2.0)
            await submit_button.click()
            await self.actions.pause(1.0, 1.8)

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
        await self.actions.move_mouse_to_element(time_button)
        await self.actions.pause(0.4, 1.2)
        await time_button.click()
        await self.actions.pause(*_VALIDATION_SLEEP)

        try:
            await self.page.wait_for_selector("form", timeout=8000)
        except Exception:
            self.logger.error("Booking form not found after selecting time slot")
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
        await self.actions.pause(1.8, 3.5)
        await self.actions.move_mouse_random()
        self.logger.info("Submitting booking form (natural mode)...")
        await self.submit()

        return await confirmation_result(
            self.page,
            court_number,
            time_slot,
            user_info,
            logger=self.logger,
            success_log="Booking confirmed for Court %s",
            failure_log="Booking result uncertain for Court %s",
        )


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
