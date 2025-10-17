"""Browser pool lifecycle helpers for the reservation scheduler."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from tracking import t

from automation.browser.pools import SpecializedBrowserPool
from automation.browser.browser_health_checker import BrowserHealthChecker
from automation.browser.browser_pool_recovery import BrowserPoolRecoveryService


@dataclass
class BrowserLifecycle:
    """Manage browser pool creation and health/recovery services."""

    logger: Any
    browser_manager: Any
    config: Any
    production_mode: bool
    browser_pool: Optional[Any] = None
    health_checker: Optional[BrowserHealthChecker] = None
    recovery_service: Optional[BrowserPoolRecoveryService] = None
    _pool_init_attempts: int = 0
    _pool_initialized: bool = False
    MAX_POOL_INIT_ATTEMPTS: int = 3

    def __post_init__(self) -> None:
        self._pool_initialized = self.browser_pool is not None
        if self.browser_pool and (self.health_checker is None or self.recovery_service is None):
            self.ensure_services(log_prefix="Using pre-initialized browser pool from main thread")

    async def ensure_browser_pool(self) -> Optional[Any]:
        """Ensure a browser pool exists and is ready for use."""

        t('reservations.queue.scheduler.browser_lifecycle.ensure_browser_pool')

        if not self._pool_initialized:
            if self._pool_init_attempts >= self.MAX_POOL_INIT_ATTEMPTS:
                self.logger.error(
                    "Exceeded max browser pool initialization attempts (%s)",
                    self.MAX_POOL_INIT_ATTEMPTS,
                )
                return self.browser_pool

            self._pool_init_attempts += 1
            self.logger.info(
                "Browser pool not initialized, initializing now... (attempt %s/%s)",
                self._pool_init_attempts,
                self.MAX_POOL_INIT_ATTEMPTS,
            )
            await self.initialize_browser_pool()
            self._pool_initialized = self.browser_pool is not None
        elif not self.production_mode:
            self.logger.debug("Browser pool already initialized")

        return self.browser_pool

    async def initialize_browser_pool(self) -> Optional[Any]:
        """Initialise the persistent browser pool via the manager."""

        t('reservations.queue.scheduler.browser_lifecycle.initialize_browser_pool')
        try:
            pool = await self.browser_manager.ensure_pool()
            self.browser_pool = pool
            self.health_checker = self.browser_manager.health_checker
            self.recovery_service = self.browser_manager.recovery_service
            if self.browser_pool:
                self.logger.info("Browser pool initialized successfully: %s", self.browser_pool)
            return self.browser_pool
        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.error(f"Failed to initialize browser pool: {exc}")
            self.browser_pool = None
            return None

    async def create_and_initialize_browser_pool_async(self) -> Optional[Any]:
        """Create a browser pool and wait until it is usable."""

        t('reservations.queue.scheduler.browser_lifecycle.create_and_initialize_browser_pool_async')
        try:
            browser_pool = await self.create_browser_pool_async()

            if browser_pool:
                if not self.production_mode:
                    self.logger.info("Waiting for browser pool to initialize browsers...")
                if await browser_pool.wait_until_ready(timeout=60):
                    self.logger.info("Browser pool is ready for use")
                    return browser_pool
                error = browser_pool.get_initialization_error()
                self.logger.error(f"Browser pool failed to initialize: {error}")
                return browser_pool

            return None

        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.error(f"Error in browser pool creation: {exc}")
            return None

    async def create_browser_pool_async(self) -> Optional[Any]:
        """Create a specialized browser pool in an async context."""

        t('reservations.queue.scheduler.browser_lifecycle.create_browser_pool_async')
        try:
            self.logger.info("=" * 60)
            self.logger.info("INITIALIZING SPECIALIZED BROWSER POOL (ASYNC)")
            self.logger.info("=" * 60)

            browser_pool = SpecializedBrowserPool(
                courts_needed=[1, 2, 3],
                headless=True,
                booking_url=self.config.booking_url,
                low_resource_mode=self.config.low_resource_mode,
                persistent=True,
                max_browsers=self.config.browser_pool_size,
            )

            self.logger.info("Starting specialized browser pool...")
            await browser_pool.start()

            self.logger.info("✓ Specialized browser pool started successfully!")
            self.logger.info("✓ All browsers initialized with performance optimizations")
            self.logger.info("✓ Ready for high-speed court checking")

            self.health_checker = BrowserHealthChecker(browser_pool)
            self.recovery_service = BrowserPoolRecoveryService(browser_pool)
            self.logger.info("✓ Health check and recovery services initialized with browser pool")

            self.browser_pool = browser_pool
            self._pool_initialized = True
            return browser_pool

        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.error(f"Error creating browser pool: {exc}")
            return None

    def ensure_services(self, log_prefix: Optional[str] = None) -> None:
        """Ensure health checker and recovery service exist for the current pool."""

        if not self.browser_pool:
            return

        if log_prefix:
            self.logger.info(log_prefix)

        if self.health_checker is None:
            self.health_checker = BrowserHealthChecker(self.browser_pool)
            self.logger.info("✓ Health check service initialized with pre-initialized pool")
        if self.recovery_service is None:
            self.recovery_service = BrowserPoolRecoveryService(self.browser_pool)
            self.logger.info("✓ Recovery service initialized with pre-initialized pool")
