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
        self._last_mouse_pos: Optional[Tuple[float, float]] = None

    @staticmethod
    def apply_speed(delay_seconds: float) -> float:
        t("automation.executors.flows.natural_flow.NaturalFlowSteps.apply_speed")
        return max(0.1, delay_seconds / WORKING_SPEED_MULTIPLIER)

    async def type_text(self, element, text: str) -> None:
        t("automation.executors.flows.natural_flow.NaturalFlowSteps.type_text")
        await element.click()
        await asyncio.sleep(self.apply_speed(random.uniform(0.4, 1.0)))
        await element.fill("")
        await asyncio.sleep(self.apply_speed(random.uniform(0.3, 0.7)))

        for index, char in enumerate(text):
            base_delay = random.randint(110, 260) / WORKING_SPEED_MULTIPLIER
            jitter = random.uniform(-15, 25)
            await element.type(char, delay=max(35, int(base_delay + jitter)))
            if random.random() < (0.1 / WORKING_SPEED_MULTIPLIER):
                await asyncio.sleep(self.apply_speed(random.uniform(0.4, 1.2)))
            if index and index % 3 == 0 and random.random() < 0.05:
                await asyncio.sleep(self.apply_speed(random.uniform(0.6, 1.4)))

        await asyncio.sleep(self.apply_speed(random.uniform(0.5, 1.5)))

    async def _mouse_curve_to(self, target_x: float, target_y: float) -> None:
        start_x, start_y = self._last_mouse_pos or (random.randint(0, 50), random.randint(0, 50))

        control_x1 = start_x + random.uniform(-80, 120)
        control_y1 = start_y + random.uniform(-80, 120)
        control_x2 = target_x + random.uniform(-120, 80)
        control_y2 = target_y + random.uniform(-120, 80)

        steps = random.randint(9, 16)
        easing = random.uniform(0.6, 1.4)

        for i in range(1, steps + 1):
            t_ratio = i / steps
            inv = 1 - t_ratio
            x = (
                inv ** 3 * start_x
                + 3 * inv ** 2 * t_ratio * control_x1
                + 3 * inv * t_ratio ** 2 * control_x2
                + t_ratio ** 3 * target_x
            )
            y = (
                inv ** 3 * start_y
                + 3 * inv ** 2 * t_ratio * control_y1
                + 3 * inv * t_ratio ** 2 * control_y2
                + t_ratio ** 3 * target_y
            )

            try:
                await self.page.mouse.move(x, y)
            except Exception:
                continue

            await asyncio.sleep(self.apply_speed(random.uniform(0.045, 0.095) * easing))

        self._last_mouse_pos = (target_x, target_y)

    async def _scroll_into_view(self, selector: str) -> Optional[object]:
        try:
            element = await self.page.wait_for_selector(selector, timeout=6000)
            await element.scroll_into_view_if_needed()
            await asyncio.sleep(self.apply_speed(random.uniform(0.4, 1.0)))
            return element
        except Exception:
            return None

    async def move_mouse(self) -> None:
        t("automation.executors.flows.natural_flow.NaturalFlowSteps.move_mouse")
        movement_count = max(1, int(random.randint(1, 2) / WORKING_SPEED_MULTIPLIER))
        viewport = self.page.viewport_size or {"width": 1280, "height": 720}
        width = viewport.get("width", 1280)
        height = viewport.get("height", 720)

        for _ in range(movement_count):
            target_x = random.randint(int(width * 0.15), int(width * 0.85))
            target_y = random.randint(int(height * 0.15), int(height * 0.85))
            await self._mouse_curve_to(target_x, target_y)
            await asyncio.sleep(self.apply_speed(random.uniform(*_MOUSE_DELAY)))
            if random.random() < (0.2 / WORKING_SPEED_MULTIPLIER):
                await asyncio.sleep(self.apply_speed(random.uniform(0.6, 1.2)))
            if random.random() < 0.15:
                delta = random.randint(-200, 200)
                try:
                    await self.page.mouse.wheel(0, delta)
                    await asyncio.sleep(self.apply_speed(random.uniform(0.4, 0.9)))
                except Exception:
                    pass

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
            await self.type_text(element, user_info.get(key, ""))
            await asyncio.sleep(self.apply_speed(random.uniform(*_FIELD_LINGER)))
            await self.move_mouse()

        try:
            country_select = await self.page.query_selector('select[name="client.phoneCountry"]')
            if country_select and not await country_select.get_attribute("value"):
                await country_select.select_option("GT")
                await asyncio.sleep(self.apply_speed(random.uniform(0.4, 0.9)))
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
        try:
            await time_button.hover()
        except Exception:
            pass
        await asyncio.sleep(self.apply_speed(random.uniform(0.4, 1.2)))
        await time_button.click()
        await asyncio.sleep(self.apply_speed(random.uniform(*_VALIDATION_SLEEP)))

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
        await asyncio.sleep(self.apply_speed(random.uniform(1.8, 3.5)))
        await self.move_mouse()
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
