"""Async browser pool facade delegating to modular helpers."""

from __future__ import annotations
from tracking import t

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from playwright.async_api import Browser, BrowserContext, Page

from automation.browser.pool import health as pool_health
from automation.browser.pool import init as pool_init
from automation.browser.pool import maintenance as pool_maintenance
from automation.browser.pool import tasks as pool_tasks
from infrastructure.constants import COURT_CONFIG

PRODUCTION_MODE = os.getenv('PRODUCTION_MODE', 'false').lower() == 'true'
logger = logging.getLogger(__name__)


class AsyncBrowserPool:
    """Async browser pool backed by Playwright with modular helpers."""

    WARMUP_DELAY = 10.0

    @property
    def DIRECT_COURT_URLS(self) -> Dict[int, str]:
        """Return direct court URLs from centralized configuration."""

        t('automation.browser.async_browser_pool.AsyncBrowserPool.DIRECT_COURT_URLS')
        return {court_num: config["direct_url"] for court_num, config in COURT_CONFIG.items()}

    def __init__(self, courts: Optional[List[int]] = None) -> None:
        t('automation.browser.async_browser_pool.AsyncBrowserPool.__init__')
        self.courts = courts or [1, 2, 3]
        self.pages: Dict[int, Page] = {}
        self.contexts: Dict[int, BrowserContext] = {}
        self.lock = asyncio.Lock()
        self.browser: Optional[Browser] = None
        self.playwright = None
        self.critical_operation_in_progress = False
        self.is_partially_ready = False
        self.production_mode = PRODUCTION_MODE

    async def start(self) -> None:
        """Initialize the browser pool."""

        t('automation.browser.async_browser_pool.AsyncBrowserPool.start')
        await pool_init.start_pool(self)

    async def _create_and_navigate_court_page_with_stagger(self, court: int, initial_delay: float):
        """Compatibility wrapper for legacy recovery routines."""

        t('automation.browser.async_browser_pool.AsyncBrowserPool._create_and_navigate_court_page_with_stagger')
        return await pool_init.create_and_navigate_court_page_with_stagger(self, court, initial_delay)

    async def _create_and_navigate_court_page_with_retry(self, court: int):
        t('automation.browser.async_browser_pool.AsyncBrowserPool._create_and_navigate_court_page_with_retry')
        return await pool_init.create_and_navigate_court_page_with_retry(self, court)

    async def _create_and_navigate_court_page_safe(self, court: int):
        t('automation.browser.async_browser_pool.AsyncBrowserPool._create_and_navigate_court_page_safe')
        return await pool_init.create_and_navigate_court_page_safe(self, court)

    async def _create_and_navigate_court_page(self, court: int):
        """Legacy method retained for compatibility."""

        t('automation.browser.async_browser_pool.AsyncBrowserPool._create_and_navigate_court_page')
        return await pool_init.create_and_navigate_court_page_safe(self, court)

    async def _cleanup_on_failure(self) -> None:
        t('automation.browser.async_browser_pool.AsyncBrowserPool._cleanup_on_failure')
        await pool_init.cleanup_on_failure(self)

    async def stop(self) -> None:
        """Clean up all browser resources with critical-operation awareness."""

        t('automation.browser.async_browser_pool.AsyncBrowserPool.stop')
        await pool_maintenance.stop_pool(self)

    async def legacy_stop(self) -> None:
        """Legacy stop path used by older callers."""

        t('automation.browser.async_browser_pool.AsyncBrowserPool.legacy_stop')
        await pool_maintenance.legacy_stop(self)

    async def refresh_browser_pages(self) -> Dict[int, bool]:
        """Refresh all initialized court pages."""

        t('automation.browser.async_browser_pool.AsyncBrowserPool.refresh_browser_pages')
        return await pool_maintenance.refresh_browser_pages(self)

    async def set_critical_operation(self, in_progress: bool) -> None:
        """Toggle the critical operation flag for booking windows."""

        t('automation.browser.async_browser_pool.AsyncBrowserPool.set_critical_operation')
        await pool_maintenance.set_critical_operation(self, in_progress)

    def is_critical_operation_in_progress(self) -> bool:
        t('automation.browser.async_browser_pool.AsyncBrowserPool.is_critical_operation_in_progress')
        return pool_health.is_critical_operation_in_progress(self)

    async def get_page(self, court_num: int) -> Optional[Page]:
        """Fetch (and lazily recreate) the page for a specific court."""

        t('automation.browser.async_browser_pool.AsyncBrowserPool.get_page')
        return await pool_health.get_page(self, court_num)

    def is_ready(self) -> bool:
        t('automation.browser.async_browser_pool.AsyncBrowserPool.is_ready')
        return pool_health.is_ready(self)

    async def wait_until_ready(self, timeout: float = 30) -> bool:
        t('automation.browser.async_browser_pool.AsyncBrowserPool.wait_until_ready')
        return await pool_health.wait_until_ready(self, timeout)

    def get_initialization_error(self) -> Optional[str]:
        t('automation.browser.async_browser_pool.AsyncBrowserPool.get_initialization_error')
        return pool_health.get_initialization_error(self)

    def get_stats(self) -> Dict[str, Any]:
        t('automation.browser.async_browser_pool.AsyncBrowserPool.get_stats')
        return pool_health.get_stats(self)

    def get_available_courts(self) -> List[int]:
        t('automation.browser.async_browser_pool.AsyncBrowserPool.get_available_courts')
        return pool_health.get_available_courts(self)

    def is_fully_ready(self) -> bool:
        t('automation.browser.async_browser_pool.AsyncBrowserPool.is_fully_ready')
        return pool_health.is_fully_ready(self)

    async def execute_parallel_booking(
        self,
        target_court: int,
        user_info: Dict[str, Any],
        target_time: Optional[str] = None,
        user_preferences: Optional[List[int]] = None,
        target_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Execute booking using the configured flow executor."""

        t('automation.browser.async_browser_pool.AsyncBrowserPool.execute_parallel_booking')
        return await pool_tasks.execute_parallel_booking(
            self,
            target_court=target_court,
            user_info=user_info,
            target_time=target_time,
            user_preferences=user_preferences,
            target_date=target_date,
        )

    async def is_slot_available(
        self,
        court_number: int,
        time_slot: str,
        target_date: datetime,
    ) -> Dict[str, Any]:
        """Probe a slot without booking it."""

        t('automation.browser.async_browser_pool.AsyncBrowserPool.is_slot_available')
        return await pool_tasks.is_slot_available(
            self,
            court_number=court_number,
            time_slot=time_slot,
            target_date=target_date,
        )
