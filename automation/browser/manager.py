"""Browser manager facade consolidating pool/health utilities."""

from __future__ import annotations
from tracking import t

import asyncio
import logging
from typing import Optional

from .async_browser_pool import AsyncBrowserPool
from .browser_health_checker import BrowserHealthChecker
from .health.types import HealthStatus
from .browser_pool_recovery import BrowserPoolRecoveryService
from .settings import BrowserSettings, load_browser_settings


class BrowserManager:
    """Provide a cohesive interface around browser pool lifecycle."""

    def __init__(
        self,
        settings: Optional[BrowserSettings] = None,
        pool: Optional[AsyncBrowserPool] = None,
    ) -> None:
        t('automation.browser.manager.BrowserManager.__init__')
        self.settings = settings or load_browser_settings()
        self._pool: Optional[AsyncBrowserPool] = pool
        self._health_checker: Optional[BrowserHealthChecker] = None
        self._recovery_service: Optional[BrowserPoolRecoveryService] = None
        self._pool_lock = asyncio.Lock()

    async def ensure_pool(self) -> AsyncBrowserPool:
        """Ensure the underlying browser pool is started."""
        t('automation.browser.manager.BrowserManager.ensure_pool')

        async with self._pool_lock:
            if self._pool is None:
                self._pool = AsyncBrowserPool(courts=self.settings.courts)
                await self._pool.start()
            if self._health_checker is None:
                self._health_checker = BrowserHealthChecker(self._pool)
            if self._recovery_service is None:
                self._recovery_service = BrowserPoolRecoveryService(self._pool)
            return self._pool

    @property
    def pool(self) -> Optional[AsyncBrowserPool]:
        """Return the current browser pool (may be ``None`` until started)."""
        t('automation.browser.manager.BrowserManager.pool')

        return self._pool

    @property
    def health_checker(self) -> Optional[BrowserHealthChecker]:
        t('automation.browser.manager.BrowserManager.health_checker')
        return self._health_checker

    @property
    def recovery_service(self) -> Optional[BrowserPoolRecoveryService]:
        t('automation.browser.manager.BrowserManager.recovery_service')
        return self._recovery_service

    async def start_pool(self, logger: Optional[logging.Logger] = None) -> bool:
        """Start the browser pool with logging."""
        t('automation.browser.manager.BrowserManager.start_pool')

        pool = self._pool or await self.ensure_pool()

        log = logger or logging.getLogger("BrowserManager")
        try:
            log.info("Initializing browser pool...")
            await pool.start()
            log.info("✅ Browser pool started successfully")
            return True
        except Exception:
            log.exception("Failed to start browser pool")
            raise

    async def stop_pool(self, logger: Optional[logging.Logger] = None) -> bool:
        """Stop the browser pool with logging."""
        t('automation.browser.manager.BrowserManager.stop_pool')

        if not self._pool:
            return True

        log = logger or logging.getLogger("BrowserManager")
        try:
            log.info("Stopping browser pool...")
            await self._pool.stop()
            log.info("✅ Browser pool stopped successfully")
            return True
        except Exception:
            log.exception("Error stopping browser pool")
            return False
        finally:
            self._pool = None
            self._health_checker = None
            self._recovery_service = None

    async def perform_health_check(self) -> Optional[HealthStatus]:
        """Run a health check if the service is initialised."""
        t('automation.browser.manager.BrowserManager.perform_health_check')

        if not self._health_checker:
            return None
        return await self._health_checker.check_pool_health()
