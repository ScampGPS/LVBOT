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
from automation.browser.pool import tasks as pool_tasks
from automation.browser.pool.manager import BrowserPoolManager
from infrastructure.constants import COURT_CONFIG

PRODUCTION_MODE = os.getenv("PRODUCTION_MODE", "false").lower() == "true"
logger = logging.getLogger(__name__)


def _manager_delegate(method_name: str, tracking_id: str, doc: str):
    """Create an async wrapper that forwards to ``BrowserPoolManager``."""

    async def handler(self, *args, **kwargs):
        t(tracking_id)
        method = getattr(self.manager, method_name)
        return await method(*args, **kwargs)

    handler.__doc__ = doc
    handler.__name__ = method_name
    return handler


def _health_delegate(method_name: str, tracking_id: str, doc: str, *, is_async: bool):
    health_method = getattr(pool_health, method_name)

    if is_async:

        async def async_handler(self, *args, **kwargs):
            t(tracking_id)
            return await health_method(self, *args, **kwargs)

        async_handler.__doc__ = doc
        async_handler.__name__ = method_name
        return async_handler

    def sync_handler(self, *args, **kwargs):
        t(tracking_id)
        return health_method(self, *args, **kwargs)

    sync_handler.__doc__ = doc
    sync_handler.__name__ = method_name
    return sync_handler


class AsyncBrowserPool:
    """Async browser pool backed by Playwright with modular helpers."""

    WARMUP_DELAY = 10.0

    @property
    def DIRECT_COURT_URLS(self) -> Dict[int, str]:
        """Return direct court URLs from centralized configuration."""

        t("automation.browser.async_browser_pool.AsyncBrowserPool.DIRECT_COURT_URLS")
        return {
            court_num: config["direct_url"]
            for court_num, config in COURT_CONFIG.items()
        }

    def __init__(self, courts: Optional[List[int]] = None) -> None:
        t("automation.browser.async_browser_pool.AsyncBrowserPool.__init__")
        self.courts = courts or [1, 2, 3]
        self.pages: Dict[int, Page] = {}
        self.contexts: Dict[int, BrowserContext] = {}
        self.lock = asyncio.Lock()
        self.browser: Optional[Browser] = None
        self.playwright = None
        self.critical_operation_in_progress = False
        self.is_partially_ready = False
        self.production_mode = PRODUCTION_MODE
        self.manager = BrowserPoolManager(self, log=logger)

    def enable_natural_navigation(self, enabled: bool = True) -> None:
        """Enable or disable natural navigation for anti-bot evasion.

        When enabled, browsers will visit the main site first before navigating
        to court pages, mimicking natural user behavior.

        Args:
            enabled: True to enable natural navigation, False for direct navigation
        """
        t("automation.browser.async_browser_pool.AsyncBrowserPool.enable_natural_navigation")
        self.manager.enable_natural_navigation(enabled)

    start = _manager_delegate(
        "start_pool",
        "automation.browser.async_browser_pool.AsyncBrowserPool.start",
        "Initialize the browser pool.",
    )

    _create_and_navigate_court_page_with_stagger = _manager_delegate(
        "create_and_navigate_court_page_with_stagger",
        "automation.browser.async_browser_pool.AsyncBrowserPool._create_and_navigate_court_page_with_stagger",
        "Compatibility wrapper for legacy recovery routines.",
    )

    _create_and_navigate_court_page_with_retry = _manager_delegate(
        "create_and_navigate_court_page_with_retry",
        "automation.browser.async_browser_pool.AsyncBrowserPool._create_and_navigate_court_page_with_retry",
        "Retry navigation helper retained for recovery flows.",
    )

    _create_and_navigate_court_page_safe = _manager_delegate(
        "create_and_navigate_court_page_safe",
        "automation.browser.async_browser_pool.AsyncBrowserPool._create_and_navigate_court_page_safe",
        "Navigate to a court page with guarded error handling.",
    )

    _create_and_navigate_court_page = _manager_delegate(
        "create_and_navigate_court_page_safe",
        "automation.browser.async_browser_pool.AsyncBrowserPool._create_and_navigate_court_page",
        "Legacy method retained for compatibility.",
    )

    _cleanup_on_failure = _manager_delegate(
        "cleanup_on_failure",
        "automation.browser.async_browser_pool.AsyncBrowserPool._cleanup_on_failure",
        "Cleanup hook invoked after pool failures.",
    )

    stop = _manager_delegate(
        "stop_pool",
        "automation.browser.async_browser_pool.AsyncBrowserPool.stop",
        "Clean up all browser resources with critical-operation awareness.",
    )

    legacy_stop = _manager_delegate(
        "legacy_stop",
        "automation.browser.async_browser_pool.AsyncBrowserPool.legacy_stop",
        "Legacy stop path used by older callers.",
    )

    refresh_browser_pages = _manager_delegate(
        "refresh_browser_pages",
        "automation.browser.async_browser_pool.AsyncBrowserPool.refresh_browser_pages",
        "Refresh all initialized court pages.",
    )

    set_critical_operation = _manager_delegate(
        "set_critical_operation",
        "automation.browser.async_browser_pool.AsyncBrowserPool.set_critical_operation",
        "Toggle the critical operation flag for booking windows.",
    )

    is_critical_operation_in_progress = _health_delegate(
        "is_critical_operation_in_progress",
        "automation.browser.async_browser_pool.AsyncBrowserPool.is_critical_operation_in_progress",
        "Return True when a critical booking operation is flagged.",
        is_async=False,
    )

    get_page = _health_delegate(
        "get_page",
        "automation.browser.async_browser_pool.AsyncBrowserPool.get_page",
        "Fetch (and lazily recreate) the page for a specific court.",
        is_async=True,
    )

    is_ready = _health_delegate(
        "is_ready",
        "automation.browser.async_browser_pool.AsyncBrowserPool.is_ready",
        "Return True if at least one court page is available.",
        is_async=False,
    )

    wait_until_ready = _health_delegate(
        "wait_until_ready",
        "automation.browser.async_browser_pool.AsyncBrowserPool.wait_until_ready",
        "Wait until the browser pool is ready or timeout occurs.",
        is_async=True,
    )

    get_initialization_error = _health_delegate(
        "get_initialization_error",
        "automation.browser.async_browser_pool.AsyncBrowserPool.get_initialization_error",
        "Return initialization error details if the pool is not ready.",
        is_async=False,
    )

    get_stats = _health_delegate(
        "get_stats",
        "automation.browser.async_browser_pool.AsyncBrowserPool.get_stats",
        "Gather basic statistics about the browser pool.",
        is_async=False,
    )

    get_available_courts = _health_delegate(
        "get_available_courts",
        "automation.browser.async_browser_pool.AsyncBrowserPool.get_available_courts",
        "Return the list of courts that have been successfully initialized.",
        is_async=False,
    )

    is_fully_ready = _health_delegate(
        "is_fully_ready",
        "automation.browser.async_browser_pool.AsyncBrowserPool.is_fully_ready",
        "Return True if all requested courts are initialized.",
        is_async=False,
    )

    async def execute_parallel_booking(
        self,
        target_court: int,
        user_info: Dict[str, Any],
        target_time: Optional[str] = None,
        user_preferences: Optional[List[int]] = None,
        target_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Execute booking using the configured flow executor."""

        t(
            "automation.browser.async_browser_pool.AsyncBrowserPool.execute_parallel_booking"
        )
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

        t("automation.browser.async_browser_pool.AsyncBrowserPool.is_slot_available")
        return await pool_tasks.is_slot_available(
            self,
            court_number=court_number,
            time_slot=time_slot,
            target_date=target_date,
        )
