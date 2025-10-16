"""Natural (human-like) booking flow implementation."""

from __future__ import annotations
from tracking import t

import asyncio
import logging
import random
from datetime import datetime
from typing import Dict, Optional, Tuple

from playwright.async_api import Page

from automation.executors.core import ExecutionResult

from .helpers import confirmation_result

WORKING_SPEED_MULTIPLIER = 2.5


def apply_speed(delay_seconds: float) -> float:
    """Adjust delays to reflect the natural flow speed multiplier."""
    t('automation.executors.flows.natural_flow.apply_speed')
    return max(0.1, delay_seconds / WORKING_SPEED_MULTIPLIER)


async def human_type_with_mistakes(element, text: str, mistake_prob: float = 0.10) -> None:
    """Simulate human typing with occasional mistakes."""
    t('automation.executors.flows.natural_flow.human_type_with_mistakes')
    await element.click()
    await asyncio.sleep(apply_speed(random.uniform(0.3, 0.8)))
    await element.fill("")
    await asyncio.sleep(apply_speed(random.uniform(0.2, 0.5)))

    for i, char in enumerate(text):
        adjusted_mistake_prob = mistake_prob / max(1, WORKING_SPEED_MULTIPLIER * 0.5)

        if random.random() < adjusted_mistake_prob and i > 0:
            wrong_chars = "abcdefghijklmnopqrstuvwxyz"
            wrong_char = random.choice(wrong_chars)
            if wrong_char != char.lower():
                base_delay = random.randint(80, 180) / WORKING_SPEED_MULTIPLIER
                await element.type(wrong_char, delay=max(20, int(base_delay)))
                await asyncio.sleep(apply_speed(random.uniform(0.1, 0.4)))
                await element.press("Backspace")
                await asyncio.sleep(apply_speed(random.uniform(0.2, 0.6)))

        base_delay = random.randint(90, 220) / WORKING_SPEED_MULTIPLIER
        await element.type(char, delay=max(20, int(base_delay)))

        if random.random() < (0.2 / WORKING_SPEED_MULTIPLIER):
            await asyncio.sleep(apply_speed(random.uniform(0.3, 1.2)))


async def natural_mouse_movement(page: Page) -> None:
    """Run gentle mouse movements to mimic human exploration."""
    t('automation.executors.flows.natural_flow.natural_mouse_movement')
    movement_count = max(1, int(random.randint(1, 2) / WORKING_SPEED_MULTIPLIER))
    for _ in range(movement_count):
        x = random.randint(200, 1000)
        y = random.randint(200, 700)
        await page.mouse.move(x, y)
        await asyncio.sleep(apply_speed(random.uniform(0.2, 0.5)))
        if random.random() < (0.15 / WORKING_SPEED_MULTIPLIER):
            await asyncio.sleep(apply_speed(random.uniform(0.5, 1.0)))


async def fill_form(page: Page, user_info: Dict[str, str]) -> None:
    """Populate the Acuity form fields with human typing."""
    t('automation.executors.flows.natural_flow.fill_form')
    first_name = user_info.get("first_name", "")
    last_name = user_info.get("last_name", "")
    email = user_info.get("email", "")
    phone = user_info.get("phone", "")

    first_name_field = await page.query_selector('input[name="client.firstName"]')
    last_name_field = await page.query_selector('input[name="client.lastName"]')
    email_field = await page.query_selector('input[name="client.email"]')
    phone_field = await page.query_selector('input[name="client.phone"]')

    if first_name_field:
        await human_type_with_mistakes(first_name_field, first_name)
    if last_name_field:
        await human_type_with_mistakes(last_name_field, last_name)
    if email_field:
        await human_type_with_mistakes(email_field, email)
    if phone_field:
        await human_type_with_mistakes(phone_field, phone)


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
    t('automation.executors.flows.natural_flow.execute_natural_flow')
    delay_min, delay_max = initial_delay_range
    delay = random.uniform(delay_min, delay_max)
    logger.info("Initial natural delay (%.1f seconds)...", delay)
    await asyncio.sleep(delay)

    await natural_mouse_movement(page)

    logger.info("Looking for %s time slot...", time_slot)
    time_button = await page.query_selector(f'button:has-text("{time_slot}")')

    if not time_button:
        alt_formats = [time_slot.replace(":00", ""), time_slot.split(":")[0]]
        for alt_time in alt_formats:
            time_button = await page.query_selector(f'button:has-text("{alt_time}")')
            if time_button:
                break

    if not time_button:
        logger.error("Time slot %s not found", time_slot)
        return ExecutionResult(
            success=False,
            error_message=f"Time slot {time_slot} not found",
            court_number=court_number,
        )

    await asyncio.sleep(apply_speed(random.uniform(0.3, 0.7)))
    await time_button.click()
    await asyncio.sleep(apply_speed(random.uniform(0.4, 0.8)))

    form_present = await page.query_selector("form")
    if not form_present:
        logger.error("Booking form not found after selecting time slot")
        return ExecutionResult(
            success=False,
            error_message="Booking form not found",
            court_number=court_number,
        )

    await fill_form(page, user_info)

    logger.info("Submitting booking form (natural mode)...")
    submit_button = await page.query_selector('button:has-text("Confirmar")')
    if not submit_button:
        submit_button = await page.query_selector('button:has-text("Confirm")')
    if submit_button:
        await submit_button.click()
        await asyncio.sleep(apply_speed(random.uniform(1.0, 1.8)))

    return await confirmation_result(
        page,
        court_number,
        time_slot,
        user_info,
        logger=logger,
        success_log="Booking confirmed for Court %s",
        failure_log="Booking result uncertain for Court %s",
    )


__all__ = [
    "WORKING_SPEED_MULTIPLIER",
    "apply_speed",
    "human_type_with_mistakes",
    "natural_mouse_movement",
    "fill_form",
    "execute_natural_flow",
]
