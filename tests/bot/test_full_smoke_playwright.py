"""End-to-end smoke test that drives the Playwright booking flow."""

from __future__ import annotations
from tracking import t

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import pytest
import pytz

from automation.availability.checker import AvailabilityChecker
from automation.browser.async_browser_pool import AsyncBrowserPool
from automation.executors.booking import AsyncBookingExecutor


def _load_user_profile(user_id: int) -> Dict[str, str]:
    t('tests.bot.test_full_smoke_playwright._load_user_profile')
    users_path = Path("data/users.json")
    data = json.loads(users_path.read_text(encoding="utf-8"))
    profile = data.get(str(user_id))
    if not profile:
        raise ValueError(f"No user profile found for user_id={user_id}")

    required_fields = ["first_name", "last_name", "email", "phone"]
    for field in required_fields:
        if not profile.get(field):
            raise ValueError(f"User profile missing required field '{field}'")

    return {
        "first_name": profile["first_name"],
        "last_name": profile["last_name"],
        "email": profile["email"],
        "phone": profile["phone"],
    }


def _resolve_target_slot(
    availability: Dict[int, Dict[str, list]],
    *,
    preferred_court: Optional[int],
    preferred_date: Optional[str],
    preferred_time: Optional[str],
) -> Optional[Tuple[int, str, str]]:
    t('tests.bot.test_full_smoke_playwright._resolve_target_slot')
    courts = (
        [preferred_court]
        if preferred_court is not None
        else [court for court in sorted(availability.keys()) if isinstance(availability.get(court), dict)]
    )

    for court in courts:
        per_day = availability.get(court) or {}
        if isinstance(per_day, dict) and "error" in per_day:
            continue

        date_keys = [preferred_date] if preferred_date else sorted(per_day.keys())
        for date_key in date_keys:
            times = per_day.get(date_key)
            if not times:
                continue

            if preferred_time:
                if preferred_time in times:
                    return court, date_key, preferred_time
                continue

            return court, date_key, times[0]

    if preferred_date or preferred_time or preferred_court is not None:
        return _resolve_target_slot(
            availability,
            preferred_court=None,
            preferred_date=None,
            preferred_time=None,
        )

    return None


async def _capture_confirmation_screenshot(pool: AsyncBrowserPool, court: int, filename: str) -> Path:
    t('tests.bot.test_full_smoke_playwright._capture_confirmation_screenshot')
    page = pool.pages.get(court)
    if not page:
        raise RuntimeError(f"No active page for court {court}; cannot capture screenshot")

    artifact_dir = Path("logs/latest_log/booking_artifacts")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    path = artifact_dir / filename
    await page.screenshot(path=str(path), full_page=True)
    return path


@pytest.mark.asyncio
@pytest.mark.smoke
async def test_full_booking_smoke_playwright(capfd):
    """Drive the real booking flow using Playwright and capture a confirmation screenshot.

    This smoke test purposely interacts with the live Acuity scheduling pages. To avoid
    accidental execution it is opt-in: set ``LV_SMOKE_ENABLE=1`` before running pytest.

    Additional optional environment variables:
        * ``LV_SMOKE_USER_ID`` (default: 125763357)
        * ``LV_SMOKE_TARGET_COURT`` (default: 3)
        * ``LV_SMOKE_TARGET_DATE`` (ISO date, default: 2025-10-29)
        * ``LV_SMOKE_TARGET_TIME`` (HH:MM, default: 20:15)
        * ``LV_SMOKE_TIMEZONE`` (default: America/Mexico_City)
    """
    t('tests.bot.test_full_smoke_playwright.test_full_booking_smoke_playwright')

    flag = os.getenv("LV_SMOKE_ENABLE")
    if flag != "1":
        pytest.skip(f"Set LV_SMOKE_ENABLE=1 to run the full Playwright smoke test. (current={flag!r})")
        pytest.skip("Set LV_SMOKE_ENABLE=1 to run the full Playwright smoke test.")

    preferred_court = int(os.getenv("LV_SMOKE_TARGET_COURT", "3"))
    preferred_date = os.getenv("LV_SMOKE_TARGET_DATE", "2025-10-29")
    preferred_time = os.getenv("LV_SMOKE_TARGET_TIME", "20:15")

    user_id = int(os.getenv("LV_SMOKE_USER_ID", "125763357"))
    user_profile = _load_user_profile(user_id)

    pool = AsyncBrowserPool(courts=[preferred_court])

    await pool.start()
    ready = await pool.wait_until_ready(timeout=60)
    if not ready:
        await pool.stop()
        pytest.fail("Browser pool failed to initialize within timeout")

    timezone_name = os.getenv("LV_SMOKE_TIMEZONE", "America/Mexico_City")
    tz = pytz.timezone(timezone_name)

    try:
        checker = AvailabilityChecker(pool)
        availability = await checker.check_availability()

        slot = _resolve_target_slot(
            availability,
            preferred_court=preferred_court,
            preferred_date=preferred_date,
            preferred_time=preferred_time,
        )

        if slot is None:
            pytest.skip(
                f"No availability for court={preferred_court} date={preferred_date} time={preferred_time}"
            )

        court, date_key, time_slot = slot

        target_date = datetime.strptime(date_key, "%Y-%m-%d").date()
        target_time = datetime.strptime(time_slot, "%H:%M").time()
        target_datetime = tz.localize(datetime.combine(target_date, target_time))

        executor = AsyncBookingExecutor(
            browser_pool=pool,
            use_natural_flow=False,
            experienced_mode=True,
        )

        result = await executor.execute_booking(
            court_number=court,
            target_date=target_datetime,
            time_slot=time_slot,
            user_info=user_profile,
        )

        assert result.success, f"Booking failed: {result.error_message or result.message}"

        timestamp = datetime.now(tz).strftime("%Y%m%d_%H%M%S")
        screenshot_name = (
            f"smoke_confirmation_court{court}_{date_key}_{time_slot.replace(':', '-')}_{timestamp}.png"
        )
        screenshot_path = await _capture_confirmation_screenshot(pool, court, screenshot_name)

        capfd.writeout(  # type: ignore[attr-defined]
            f"Booking confirmation screenshot saved to: {screenshot_path}\n"
        )

    finally:
        await pool.stop()
