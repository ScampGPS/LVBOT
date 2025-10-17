"""Booking and availability tasks executed against the browser pool."""

from __future__ import annotations
from tracking import t

import logging
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


aSYNC_BOOKING_DEFAULT_TIME = '10:00'


async def execute_parallel_booking(
    pool,
    target_court: int,
    user_info: Dict[str, Any],
    target_time: str | None = None,
    user_preferences: List[int] | None = None,
    target_date: datetime | None = None,
) -> Dict[str, Any]:
    """Execute parallel booking attempt on specified court."""

    t('automation.browser.pool.tasks.execute_parallel_booking')
    try:
        court_number = target_court
        page = await pool.get_page(court_number)
        if not page:
            available = pool.get_available_courts()
            error_msg = f'Court {court_number} page not available. Available courts: {available}'
            if pool.is_partially_ready:
                error_msg += ' (Browser pool is partially initialized)'
            return {'success': False, 'error': error_msg}

        from automation.executors.booking import BookingFlowExecutor  # Local import to avoid circular dependency

        mode = 'fast' if user_info.get('experienced_mode', True) else 'natural'
        logger.info("Using %s booking mode for Court %s", mode.upper(), court_number)

        executor = BookingFlowExecutor(pool, mode=mode)
        result = await executor.execute_booking(
            court_number=court_number,
            target_date=target_date or datetime.now(),
            time_slot=target_time or ASYNC_BOOKING_DEFAULT_TIME,
            user_info=user_info,
        )

        return {
            'success': result.success,
            'court': result.court_reserved or result.court_number,
            'time': result.time_reserved or (target_time or ASYNC_BOOKING_DEFAULT_TIME),
            'message': result.message or result.confirmation_url,
            'error': result.error_message,
        }
    except Exception as exc:
        logger.error("Error in execute_parallel_booking: %s", exc)
        return {'success': False, 'error': str(exc)}


async def is_slot_available(pool, court_number: int, time_slot: str, target_date: datetime) -> Dict[str, Any]:
    """Check if a time slot is available without actually booking it."""

    t('automation.browser.pool.tasks.is_slot_available')
    try:
        page = await pool.get_page(court_number)
        if not page:
            return {
                'available': False,
                'reason': f'Court {court_number} page not available',
                'checked_at': datetime.now(),
                'court': court_number,
            }

        from infrastructure.constants import COURT_CONFIG
        court_entry = COURT_CONFIG.get(court_number)
        if not court_entry:
            return {
                'available': False,
                'reason': f'No configuration found for court {court_number}',
                'checked_at': datetime.now(),
                'court': court_number,
            }

        court_url = court_entry['direct_url']
        date_str = target_date.strftime("%Y-%m-%d")
        appointment_type_id = court_url.split('/appointment/')[1].split('/')[0]
        direct_url = (
            f"{court_url}/datetime/{date_str}T{time_slot}:00-06:00"
            f"?appointmentTypeIds[]={appointment_type_id}"
        )

        logger.info(
            "Checking availability for Court %s at %s on %s",
            court_number,
            time_slot,
            date_str,
        )

        await page.goto(direct_url, wait_until="domcontentloaded", timeout=30000)

        from infrastructure.constants import BrowserTimeouts
        selectors = [
            f'button.time-selection:has(p:text("{time_slot}"))',
            f'button:has-text("{time_slot}")',
            f'button:has-text("{time_slot.replace(":00", "")}")',
        ]

        for selector in selectors:
            try:
                button = await page.wait_for_selector(selector, timeout=BrowserTimeouts.PAGE_LOAD)
                if button and await button.is_enabled():
                    return {
                        'available': True,
                        'reason': 'Booking form detected - slot appears available',
                        'checked_at': datetime.now(),
                        'court': court_number,
                    }
            except Exception:
                continue

        return {
            'available': False,
            'reason': 'Booking form not detected - slot may be unavailable',
            'checked_at': datetime.now(),
            'court': court_number,
        }
    except Exception as exc:
        logger.error("Error checking availability for Court %s: %s", court_number, exc)
        return {
            'available': False,
            'reason': f'Error during availability check: {exc}',
            'checked_at': datetime.now(),
            'court': court_number,
        }
