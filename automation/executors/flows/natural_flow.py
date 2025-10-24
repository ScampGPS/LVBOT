"""Natural (human-like) booking flow implementation."""

from __future__ import annotations
from tracking import t

import asyncio
import logging
import random
from datetime import datetime
from typing import Dict, Tuple

from playwright.async_api import Page

from automation.executors.core import ExecutionResult

from .helpers import confirmation_result

WORKING_SPEED_MULTIPLIER = 2.5
_VALIDATION_SLEEP = (0.3, 0.8)
_MOUSE_DELAY = (0.2, 0.5)


class NaturalFlowSteps:
    """Encapsulates the human-like steps used by the natural booking flow."""

    def __init__(self, page: Page, logger: logging.Logger) -> None:
        t("automation.executors.flows.natural_flow.NaturalFlowSteps.__init__")
        self.page = page
        self.logger = logger

    @staticmethod
    def apply_speed(delay_seconds: float) -> float:
        t("automation.executors.flows.natural_flow.NaturalFlowSteps.apply_speed")
        return max(0.1, delay_seconds / WORKING_SPEED_MULTIPLIER)

    async def type_text(self, element, text: str) -> None:
        t("automation.executors.flows.natural_flow.NaturalFlowSteps.type_text")
        await element.click()
        await asyncio.sleep(self.apply_speed(random.uniform(0.3, 0.8)))
        await element.fill("")
        await asyncio.sleep(self.apply_speed(random.uniform(0.2, 0.5)))

        for char in text:
            base_delay = random.randint(90, 220) / WORKING_SPEED_MULTIPLIER
            await element.type(char, delay=max(20, int(base_delay)))
            if random.random() < (0.2 / WORKING_SPEED_MULTIPLIER):
                await asyncio.sleep(self.apply_speed(random.uniform(0.3, 1.2)))

    async def move_mouse(self) -> None:
        t("automation.executors.flows.natural_flow.NaturalFlowSteps.move_mouse")
        movement_count = max(1, int(random.randint(1, 2) / WORKING_SPEED_MULTIPLIER))
        for _ in range(movement_count):
            x = random.randint(200, 1000)
            y = random.randint(200, 700)
            await self.page.mouse.move(x, y)
            await asyncio.sleep(self.apply_speed(random.uniform(*_MOUSE_DELAY)))
            if random.random() < (0.15 / WORKING_SPEED_MULTIPLIER):
                await asyncio.sleep(self.apply_speed(random.uniform(0.5, 1.0)))

    async def fill_user_form(self, user_info: Dict[str, str]) -> None:
        t("automation.executors.flows.natural_flow.NaturalFlowSteps.fill_user_form")
        selectors = {
            "first_name": 'input[name="client.firstName"]',
            "last_name": 'input[name="client.lastName"]',
            "email": 'input[name="client.email"]',
            "phone": 'input[name="client.phone"]',
        }
        values = {
            "first_name": user_info.get("first_name", ""),
            "last_name": user_info.get("last_name", ""),
            "email": user_info.get("email", ""),
            "phone": user_info.get("phone", ""),
        }

        for key, selector in selectors.items():
            element = await self.page.query_selector(selector)
            if element:
                await self.type_text(element, values[key])

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
            await submit_button.click()
            await asyncio.sleep(self.apply_speed(random.uniform(1.0, 1.8)))

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
        await asyncio.sleep(delay)

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

        await asyncio.sleep(self.apply_speed(random.uniform(*_VALIDATION_SLEEP)))
        await time_button.click()
        await asyncio.sleep(self.apply_speed(random.uniform(*_VALIDATION_SLEEP)))

        form_present = await self.page.query_selector("form")
        if not form_present:
            self.logger.error("Booking form not found after selecting time slot")
            return ExecutionResult(
                success=False,
                error_message="Booking form not found",
                court_number=court_number,
            )

        await self.fill_user_form(user_info)
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
