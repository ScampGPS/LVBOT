"""Fast booking flow implementation with experienced shortcuts."""

from __future__ import annotations
from tracking import t

import asyncio
import logging
import os
import random
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from playwright.async_api import Page

from automation.availability import DateTimeHelpers
from automation.executors.core import ExecutionResult

from .helpers import confirmation_result

EXPERIENCED_SPEED_MULTIPLIER = 3.0
PRODUCTION_MODE = os.getenv("PRODUCTION_MODE", "false").lower() == "true"


def apply_speed(delay_seconds: float) -> float:
    """Adjust delays to reflect the fast flow speed multiplier."""
    t('automation.executors.flows.fast_flow.apply_speed')
    return max(0.05, delay_seconds / EXPERIENCED_SPEED_MULTIPLIER)


async def take_screenshot_if_dev(
    page: Page,
    filename_prefix: str,
    court_number: int,
    log: logging.Logger,
) -> Optional[str]:
    """Persist debug screenshots when not running in production."""
    t('automation.executors.flows.fast_flow.take_screenshot_if_dev')
    if PRODUCTION_MODE:
        log.debug("Screenshot skipped in production mode: %s", filename_prefix)
        return None

    try:
        screenshot_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logs", "screenshots")
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


async def fast_fill(element, text: str) -> None:
    """Fill an input rapidly for the fast flow."""
    t('automation.executors.flows.fast_flow.fast_fill')
    await element.click()
    await asyncio.sleep(0.05)
    await element.fill("")
    await asyncio.sleep(0.05)
    await element.fill(text)
    await asyncio.sleep(0.1)


async def minimal_mouse_movement(page: Page) -> None:
    """Perform a minimal mouse movement to warm up the page."""
    t('automation.executors.flows.fast_flow.minimal_mouse_movement')
    x = random.randint(400, 800)
    y = random.randint(300, 600)
    await page.mouse.move(x, y)
    await asyncio.sleep(0.1)


async def find_time_slot_with_refresh(
    page: Page,
    time_slot: str,
    court_number: int,
    max_attempts: int,
    refresh_delay: float,
    log: logging.Logger,
    target_datetime: Optional[datetime] = None,
) -> Optional[Any]:
    """Find a time slot, refreshing when necessary until available."""
    t('automation.executors.flows.fast_flow.find_time_slot_with_refresh')
    if target_datetime:
        booking_window_opens = target_datetime - timedelta(hours=48)
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
        await take_screenshot_if_dev(page, f"time_search_attempt{attempt}", court_number, log)

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


async def fill_form(page: Page, user_info: Dict[str, str], *, logger: Optional[logging.Logger] = None) -> None:
    """Populate the Acuity form fields using the fast flow strategy."""
    t('automation.executors.flows.fast_flow.fill_form')

    try:
        await page.wait_for_selector('form', timeout=5000)
    except Exception:
        if logger:
            logger.debug("Booking form not detected before filling")

    fields = {
        'input[name="client.firstName"]': user_info.get("first_name", ""),
        'input[name="client.lastName"]': user_info.get("last_name", ""),
        'input[name="client.email"]': user_info.get("email", ""),
        'input[name="client.phone"]': user_info.get("phone", ""),
    }

    for selector, value in fields.items():
        try:
            element = await page.wait_for_selector(selector, timeout=5000)
        except Exception:
            if logger:
                logger.debug("Field %s not found", selector)
            continue
        await fast_fill(element, value)
        if logger:
            logger.debug("Filled %s with %s", selector, value)

    try:
        country_select = await page.query_selector('select[name="client.phoneCountry"]')
        if country_select and not await country_select.get_attribute("value"):
            await country_select.select_option("GT")
            if logger:
                logger.debug("Selected phone country GT")
    except Exception:
        pass


async def execute_fast_flow(
    page: Page,
    court_number: int,
    target_date: datetime,
    time_slot: str,
    user_info: Dict[str, str],
    *,
    logger: logging.Logger,
) -> ExecutionResult:
    """Execute the fast booking flow and return the result."""
    t('automation.executors.flows.fast_flow.execute_fast_flow')
    await minimal_mouse_movement(page)

    target_date_str = target_date.strftime("%Y-%m-%d") if hasattr(target_date, "strftime") else str(target_date)
    target_datetime = None
    try:
        target_datetime = DateTimeHelpers.parse_reservation_datetime(target_date_str, time_slot)
    except Exception:  # pragma: no cover - defensive guard against malformed data
        target_datetime = None

    time_button = await find_time_slot_with_refresh(
        page,
        time_slot,
        court_number,
        max_attempts=5,
        refresh_delay=0.6,
        log=logger,
        target_datetime=target_datetime,
    )
    if not time_button:
        return ExecutionResult(
            success=False,
            error_message=f"Time slot {time_slot} not available",
            court_number=court_number,
        )

    await time_button.click()
    await asyncio.sleep(apply_speed(0.3))

    await fill_form(page, user_info, logger=logger)

    submit_button = await page.query_selector('button:has-text("Confirmar")')
    if submit_button:
        await submit_button.click()

    await asyncio.sleep(apply_speed(1.0))
    return await confirmation_result(
        page,
        court_number,
        time_slot,
        user_info,
        logger=logger,
        success_log="Booking confirmed for Court %s",
    )


__all__ = [
    "EXPERIENCED_SPEED_MULTIPLIER",
    "apply_speed",
    "take_screenshot_if_dev",
    "fast_fill",
    "minimal_mouse_movement",
    "find_time_slot_with_refresh",
    "fill_form",
    "execute_fast_flow",
]
