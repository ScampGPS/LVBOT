"""Unified async booking executor facade."""

from __future__ import annotations

from typing import Any

from .async_booking_executor import AsyncBookingExecutor
from .experienced_booking_executor import ExperiencedBookingExecutor
from .smart_async_booking_executor import SmartAsyncBookingExecutor
from .working_booking_executor import WorkingBookingExecutor
from .config import AsyncExecutorConfig, DEFAULT_EXECUTOR_CONFIG


class UnifiedAsyncBookingExecutor:
    """Route booking requests to the appropriate executor based on config."""

    def __init__(self, browser_pool=None, config: AsyncExecutorConfig = DEFAULT_EXECUTOR_CONFIG):
        self.config = config
        self.browser_pool = browser_pool
        self._executor = self._build_executor()

    def _build_executor(self) -> Any:
        if self.config.use_experienced_mode:
            return ExperiencedBookingExecutor(browser_pool=self.browser_pool)
        if self.config.use_smart_navigation:
            return SmartAsyncBookingExecutor(browser_pool=self.browser_pool)
        if self.config.natural_flow:
            return WorkingBookingExecutor(browser_pool=self.browser_pool)
        return AsyncBookingExecutor(browser_pool=self.browser_pool)

    def __getattr__(self, item: str) -> Any:
        return getattr(self._executor, item)

    def with_config(self, config: AsyncExecutorConfig) -> "UnifiedAsyncBookingExecutor":
        """Return a new executor instance using the provided config."""

        return UnifiedAsyncBookingExecutor(browser_pool=self.browser_pool, config=config)
