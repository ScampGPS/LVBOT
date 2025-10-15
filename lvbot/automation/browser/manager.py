"""Browser manager facade consolidating pool/health utilities."""

from __future__ import annotations

import asyncio
from typing import Optional

from .async_browser_pool import AsyncBrowserPool
from .browser_refresh_manager import BrowserRefreshManager
from .browser_health_checker import BrowserHealthChecker, HealthStatus
from .browser_pool_recovery import BrowserPoolRecoveryService
from .settings import BrowserSettings, load_browser_settings


class BrowserManager:
    """Provide a cohesive interface around browser pool lifecycle."""

    def __init__(
        self,
        settings: Optional[BrowserSettings] = None,
        pool: Optional[AsyncBrowserPool] = None,
    ) -> None:
        self.settings = settings or load_browser_settings()
        self._pool: Optional[AsyncBrowserPool] = pool
        self._refresh_manager: Optional[BrowserRefreshManager] = None
        self._health_checker: Optional[BrowserHealthChecker] = None
        self._recovery_service: Optional[BrowserPoolRecoveryService] = None
        self._pool_lock = asyncio.Lock()

    async def ensure_pool(self) -> AsyncBrowserPool:
        """Ensure the underlying browser pool is started."""

        async with self._pool_lock:
            if self._pool is None:
                self._pool = AsyncBrowserPool(courts=self.settings.courts)
                await self._pool.start()
            if self._refresh_manager is None:
                self._refresh_manager = BrowserRefreshManager(self._pool)
            if self._health_checker is None:
                self._health_checker = BrowserHealthChecker(self._pool)
            if self._recovery_service is None:
                self._recovery_service = BrowserPoolRecoveryService(self._pool)
            return self._pool

    @property
    def pool(self) -> Optional[AsyncBrowserPool]:
        """Return the current browser pool (may be ``None`` until started)."""

        return self._pool

    @property
    def refresh_manager(self) -> Optional[BrowserRefreshManager]:
        return self._refresh_manager

    @property
    def health_checker(self) -> Optional[BrowserHealthChecker]:
        return self._health_checker

    @property
    def recovery_service(self) -> Optional[BrowserPoolRecoveryService]:
        return self._recovery_service

    async def shutdown(self) -> None:
        """Attempt to gracefully close the browser pool."""

        if self._pool:
            await self._pool.stop()
        self._pool = None
        self._refresh_manager = None
        self._health_checker = None
        self._recovery_service = None

    async def perform_health_check(self) -> Optional[HealthStatus]:
        """Run a health check if the service is initialised."""

        if not self._health_checker:
            return None
        return await self._health_checker.check_pool_health()
