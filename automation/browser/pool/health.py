"""Health and status helpers for the async browser pool."""

from __future__ import annotations
from tracking import t

import asyncio
import logging
import time
from typing import Dict, Optional

from automation.browser.pool.manager import BrowserPoolManager

logger = logging.getLogger(__name__)


def is_ready(pool) -> bool:
    """Return True if at least one court page is available."""

    t('automation.browser.pool.health.is_ready')
    return bool(pool.browser and pool.pages)


async def wait_until_ready(pool, timeout: float = 30) -> bool:
    """Wait until the browser pool is ready or timeout occurs."""

    t('automation.browser.pool.health.wait_until_ready')
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_ready(pool):
            return True
        await asyncio.sleep(0.5)
    return False


def get_initialization_error(pool) -> Optional[str]:
    """Return initialization error details if the pool is not ready."""

    t('automation.browser.pool.health.get_initialization_error')
    if not is_ready(pool):
        return "Browser pool not initialized or no pages available"
    return None


def get_stats(pool) -> Dict[str, object]:
    """Gather basic statistics about the browser pool."""

    t('automation.browser.pool.health.get_stats')
    return {
        'browser_count': len(pool.pages),
        'browsers_created': len(pool.pages),
        'browsers_recycled': 0,
        'positioning_failures': 0,
        'total_bookings': 0,
        'successful_bookings': 0,
        'max_browsers': len(pool.courts),
        'court_assignments': {court: court for court in pool.pages.keys()},
        'browser_details': {
            f"court{court}": {
                'court': court,
                'healthy': True,
                'positioned': True,
                'uses': 0,
                'age_minutes': 0,
            }
            for court in pool.pages.keys()
        },
        'available_courts': list(pool.pages.keys()),
    }


def get_available_courts(pool) -> list[int]:
    """Return the list of courts that have been successfully initialized."""

    t('automation.browser.pool.health.get_available_courts')
    return list(pool.pages.keys())


def is_fully_ready(pool) -> bool:
    """Return True if all requested courts are initialized."""

    t('automation.browser.pool.health.is_fully_ready')
    return is_ready(pool) and not pool.is_partially_ready


def is_critical_operation_in_progress(pool) -> bool:
    """Return True when a critical booking operation is flagged."""

    t('automation.browser.pool.health.is_critical_operation_in_progress')
    return pool.critical_operation_in_progress


async def get_page(pool, court_num: int):
    """Fetch (and lazily recreate) the page for a specific court."""

    t('automation.browser.pool.health.get_page')
    async with pool.lock:
        page = pool.pages.get(court_num)
        if not page:
            if court_num not in pool.courts:
                logger.warning("Court %s was not requested during initialization", court_num)
            else:
                logger.warning("Court %s is not available (initialization may have failed)", court_num)
            return None

        try:
            _ = page.url
            return page
        except Exception as exc:
            logger.warning("Court %s page connection is dead: %s. Recreating...", court_num, exc)
            await _close_page_and_context(pool, court_num)
            try:
                manager = BrowserPoolManager(pool, log=logger)
                await manager.create_and_navigate_court_page_safe(court_num)
                return pool.pages.get(court_num)
            except Exception as recreate_error:
                logger.error("Failed to recreate Court %s page: %s", court_num, recreate_error)
                return None


async def _close_page_and_context(pool, court_num: int) -> None:
    page = pool.pages.pop(court_num, None)
    if page:
        try:
            await page.close()
        except Exception:
            pass
    context = pool.contexts.pop(court_num, None)
    if context:
        try:
            await context.close()
        except Exception:
            pass
