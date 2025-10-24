"""Unified manager for initializing and maintaining the async browser pool."""

from __future__ import annotations
from tracking import t

import asyncio
import logging
from typing import Dict, Optional

from playwright.async_api import async_playwright

from infrastructure.constants import BrowserPoolConfig, BrowserTimeouts

logger = logging.getLogger(__name__)


class BrowserPoolManager:
    """Encapsulates start/stop/refresh operations for the court browser pool."""

    def __init__(self, pool, *, log: logging.Logger | None = None) -> None:
        t("automation.browser.pool.manager.BrowserPoolManager.__init__")
        self.pool = pool
        self.logger = log or logger

    async def start_pool(self) -> None:
        """Initialize Playwright, launch Chromium, and prepare court pages."""

        t("automation.browser.pool.manager.BrowserPoolManager.start_pool")
        try:
            self.logger.info("Starting Playwright...")
            self.pool.playwright = await async_playwright().start()

            self.logger.info("Launching Chromium browser...")
            self.pool.browser = await self.pool.playwright.chromium.launch(
                headless=False,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--window-size=1920,1080",
                    "--start-maximized",
                ],
            )

            self.logger.info(
                "Initializing browser pool with parallel navigation and retry"
            )
            tasks = []
            for index, court in enumerate(self.pool.courts):
                delay = index * 1.5
                tasks.append(
                    self.create_and_navigate_court_page_with_stagger(court, delay)
                )

            results = await asyncio.gather(*tasks, return_exceptions=True)

            successful_courts = 0
            failed_courts: list[int] = []
            for court, result in zip(self.pool.courts, results):
                if isinstance(result, Exception):
                    self.logger.error(
                        "❌ Court %s failed to initialize: %s", court, result
                    )
                    failed_courts.append(court)
                else:
                    successful_courts += 1
                    self.logger.info("✅ Court %s initialized successfully", court)

            if successful_courts == 0:
                raise RuntimeError(
                    f"All court initializations failed: 0/{len(self.pool.courts)} courts ready"
                )

            if successful_courts < len(self.pool.courts):
                self.logger.warning(
                    "⚠️ PARTIAL Browser pool initialization: %s/%s courts ready",
                    successful_courts,
                    len(self.pool.courts),
                )
                self.logger.warning("Failed courts: %s", failed_courts)
                self.logger.info("Continuing with available courts...")
            else:
                self.logger.info(
                    "✅ FULL Browser pool initialized with %s/%s courts ready",
                    successful_courts,
                    len(self.pool.courts),
                )

            self.pool.is_partially_ready = successful_courts < len(self.pool.courts)
        except Exception:
            await self.cleanup_on_failure()
            raise

    async def create_and_navigate_court_page_with_stagger(
        self, court: int, initial_delay: float
    ):
        """Apply staggered delay before creating the court page with retries."""

        t(
            "automation.browser.pool.manager.BrowserPoolManager.create_and_navigate_court_page_with_stagger"
        )
        if initial_delay > 0:
            if not self.pool.production_mode:
                self.logger.info(
                    "Court %s: Waiting %ss before initialization", court, initial_delay
                )
            await asyncio.sleep(initial_delay)

        return await self.create_and_navigate_court_page_with_retry(court)

    async def create_and_navigate_court_page_with_retry(self, court: int):
        """Retry court page creation with exponential backoff."""

        t(
            "automation.browser.pool.manager.BrowserPoolManager.create_and_navigate_court_page_with_retry"
        )
        for attempt in range(BrowserPoolConfig.MAX_RETRY_ATTEMPTS):
            try:
                return await self.create_and_navigate_court_page_safe(court)
            except Exception as exc:
                if attempt < BrowserPoolConfig.MAX_RETRY_ATTEMPTS - 1:
                    delay = BrowserTimeouts.RETRY_DELAY_BASE ** (attempt + 1)
                    self.logger.warning(
                        "Court %s attempt %s/%s failed: %s",
                        court,
                        attempt + 1,
                        BrowserPoolConfig.MAX_RETRY_ATTEMPTS,
                        exc,
                    )
                    if not self.pool.production_mode:
                        self.logger.info("Court %s retrying in %ss", court, delay)
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(
                        "Court %s failed after %s attempts: %s",
                        court,
                        BrowserPoolConfig.MAX_RETRY_ATTEMPTS,
                        exc,
                    )
                    raise

    async def create_and_navigate_court_page_safe(self, court: int):
        """Create a context + page for a court and pre-navigate to its calendar."""

        t(
            "automation.browser.pool.manager.BrowserPoolManager.create_and_navigate_court_page_safe"
        )
        try:
            context = await self.pool.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="es-GT",
                timezone_id="America/Guatemala",
            )
            page = await context.new_page()

            await page.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.chrome = { runtime: {} };
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications'
                        ? Promise.resolve({ state: Notification.permission })
                        : originalQuery(parameters)
                );
            """
            )

            self.pool.pages[court] = page
            self.pool.contexts[court] = context

            if court in self.pool.DIRECT_COURT_URLS:
                court_url = self.pool.DIRECT_COURT_URLS[court]
                if not self.pool.production_mode:
                    self.logger.debug(
                        "Court %s: Pre-navigating to %s", court, court_url
                    )

                await page.goto(
                    court_url,
                    wait_until="domcontentloaded",
                    timeout=BrowserTimeouts.SLOW_NAVIGATION,
                )
                final_url = page.url
                if not self.pool.production_mode:
                    self.logger.info(
                        "Court %s current URL after navigation: %s", court, final_url
                    )
                if "/datetime/" in final_url:
                    self.logger.warning(
                        "Court %s: ended up on booking form URL instead of calendar",
                        court,
                    )
                try:
                    await page.wait_for_selector('[class*="time"]', timeout=30000)
                    if not self.pool.production_mode:
                        self.logger.debug("Court %s: Calendar elements loaded", court)
                except Exception:
                    self.logger.warning(
                        "Court %s: Calendar elements not found, continuing anyway",
                        court,
                    )

                warmup_delay = getattr(self.pool, "WARMUP_DELAY", 10.0)
                self.logger.info(
                    "Court %s: Warming up browser for %ss", court, warmup_delay
                )
                await asyncio.sleep(warmup_delay)
                self.logger.info("Court %s: Browser warm-up completed", court)
            else:
                self.logger.warning(
                    "Court %s: No direct URL available for pre-navigation", court
                )

            return True
        except Exception as exc:
            await self._cleanup_failed_page(court)
            raise exc

    async def cleanup_on_failure(self) -> None:
        """Clean up resources when startup fails."""

        t("automation.browser.pool.manager.BrowserPoolManager.cleanup_on_failure")
        await self._cleanup_failed_page(None, total_cleanup=True)

    async def _cleanup_failed_page(
        self, court: Optional[int], total_cleanup: bool = False
    ) -> None:
        """Close page/context for a specific court or perform full cleanup."""

        if court is not None:
            page = self.pool.pages.pop(court, None)
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            context = self.pool.contexts.pop(court, None)
            if context:
                try:
                    await context.close()
                except Exception:
                    pass

        if total_cleanup:
            for stored_page in list(self.pool.pages.values()):
                try:
                    await stored_page.close()
                except Exception:
                    pass
            for stored_context in list(self.pool.contexts.values()):
                try:
                    await stored_context.close()
                except Exception:
                    pass
            self.pool.pages.clear()
            self.pool.contexts.clear()

            if self.pool.browser:
                try:
                    await self.pool.browser.close()
                except Exception:
                    pass
                self.pool.browser = None

            if self.pool.playwright:
                try:
                    await self.pool.playwright.stop()
                except Exception:
                    pass
                self.pool.playwright = None

    async def set_critical_operation(self, in_progress: bool) -> None:
        """Toggle the critical operation flag to block refresh cycles."""

        t("automation.browser.pool.manager.BrowserPoolManager.set_critical_operation")
        async with self.pool.lock:
            self.pool.critical_operation_in_progress = in_progress
            self.logger.info("Critical operation flag set to: %s", in_progress)

    async def refresh_browser_pages(self) -> Dict[int, bool]:
        """Refresh all initialized court pages to prevent staleness."""

        t("automation.browser.pool.manager.BrowserPoolManager.refresh_browser_pages")
        refresh_results: Dict[int, bool] = {}

        self.logger.info("🔄 Starting browser page refresh cycle")
        if not self.pool.pages:
            self.logger.warning("No browser pages to refresh")
            return refresh_results

        for court in self.pool.courts:
            page = self.pool.pages.get(court)
            if not page:
                self.logger.warning("Court %s has no page to refresh", court)
                refresh_results[court] = False
                continue

            court_url = self.pool.DIRECT_COURT_URLS.get(court)
            if not court_url:
                self.logger.error("No URL found for court %s", court)
                refresh_results[court] = False
                continue

            try:
                self.logger.info("🔄 Refreshing Court %s browser page", court)
                await page.goto(court_url, wait_until="domcontentloaded", timeout=30000)
                self.logger.info("✅ Court %s refreshed successfully", court)
                refresh_results[court] = True
            except Exception as exc:
                self.logger.error("❌ Failed to refresh Court %s: %s", court, exc)
                refresh_results[court] = False

        successful = sum(1 for success in refresh_results.values() if success)
        self.logger.info(
            "🔄 REFRESH COMPLETE: %s/%s courts refreshed successfully",
            successful,
            len(refresh_results),
        )
        return refresh_results

    async def stop_pool(self) -> None:
        """Shut down browser resources, waiting for critical operations if needed."""

        t("automation.browser.pool.manager.BrowserPoolManager.stop_pool")
        self.logger.info("🔴 STARTING BROWSER POOL SHUTDOWN...")

        if self.pool.critical_operation_in_progress:
            self.logger.info(
                "⏳ Waiting for critical booking operations to complete before shutdown..."
            )
            max_wait_time = 300
            waited = 0
            while self.pool.critical_operation_in_progress and waited < max_wait_time:
                await asyncio.sleep(1)
                waited += 1
                if waited % 30 == 0:
                    self.logger.info(
                        "⏳ Still waiting for critical operations... (%ss elapsed)",
                        waited,
                    )
            if self.pool.critical_operation_in_progress:
                self.logger.warning(
                    "⚠️ Forcing shutdown after %ss - critical operation still in progress",
                    max_wait_time,
                )
            else:
                self.logger.info(
                    "✅ Critical operations completed, proceeding with shutdown"
                )

        page_errors = []
        for court, page in self.pool.pages.items():
            try:
                if page and not page.is_closed():
                    await page.close()
                    self.logger.info("✅ Page for court %s closed", court)
                else:
                    self.logger.info("⚠️ Page for court %s already closed", court)
            except Exception as exc:
                if "Connection closed" in str(exc) or "Target closed" in str(exc):
                    self.logger.debug("Page %s already disconnected", court)
                else:
                    self.logger.error("Error closing page for court %s: %s", court, exc)
                    page_errors.append((court, str(exc)))

        context_errors = []
        for court, context in self.pool.contexts.items():
            try:
                if context:
                    await context.close()
                    self.logger.info("✅ Context for court %s closed", court)
            except Exception as exc:
                if "Connection closed" in str(exc) or "Target closed" in str(exc):
                    self.logger.debug("Context %s already disconnected", court)
                else:
                    self.logger.error(
                        "Error closing context for court %s: %s", court, exc
                    )
                    context_errors.append((court, str(exc)))

        self.pool.pages.clear()
        self.pool.contexts.clear()
        self.logger.info("✅ Page and context dictionaries cleared")

        if self.pool.browser:
            try:
                await self.pool.browser.close()
                self.logger.info("✅ Chromium browser closed")
            except Exception as exc:
                if "Connection closed" in str(exc) or "Target closed" in str(exc):
                    self.logger.info("ℹ️ Browser already disconnected")
                else:
                    self.logger.error("❌ Error closing browser: %s", exc)

        if self.pool.playwright:
            try:
                await self.pool.playwright.stop()
                self.logger.info("✅ Playwright stopped")
            except Exception as exc:
                self.logger.error("❌ Error stopping playwright: %s", exc)

        if page_errors or context_errors:
            self.logger.warning(
                "⚠️ Shutdown completed with %s page errors and %s context errors",
                len(page_errors),
                len(context_errors),
            )
        else:
            self.logger.info("✅ BROWSER POOL SHUTDOWN COMPLETED SUCCESSFULLY")

        self.pool.browser = None
        self.pool.playwright = None
        self.pool.critical_operation_in_progress = False
        self.pool.is_partially_ready = False

    async def legacy_stop(self) -> None:
        """Legacy stop helper retained for compatibility."""

        t("automation.browser.pool.manager.BrowserPoolManager.legacy_stop")
        self.logger.info("Stopping AsyncBrowserPool (legacy path)...")

        try:
            for court, page in self.pool.pages.items():
                try:
                    self.logger.debug("Closing page for court %s", court)
                    await page.close()
                except Exception as exc:
                    if "Connection closed" not in str(
                        exc
                    ) and "Target closed" not in str(exc):
                        self.logger.error(
                            "Error closing page for court %s: %s", court, exc
                        )

            for court, context in self.pool.contexts.items():
                try:
                    self.logger.debug("Closing context for court %s", court)
                    await context.close()
                except Exception as exc:
                    if "Connection closed" not in str(
                        exc
                    ) and "Target closed" not in str(exc):
                        self.logger.error(
                            "Error closing context for court %s: %s", court, exc
                        )

            if self.pool.browser:
                try:
                    self.logger.info("Closing browser...")
                    await self.pool.browser.close()
                except Exception as exc:
                    if "Connection closed" not in str(
                        exc
                    ) and "Target closed" not in str(exc):
                        self.logger.error("Error closing browser: %s", exc)

            if self.pool.playwright:
                try:
                    self.logger.info("Stopping playwright...")
                    await self.pool.playwright.stop()
                except Exception as exc:
                    self.logger.error("Error stopping playwright: %s", exc)

            self.pool.pages.clear()
            self.pool.contexts.clear()
            self.pool.browser = None
            self.pool.playwright = None

            self.logger.info("✅ AsyncBrowserPool stopped successfully (legacy path)")
        except Exception as exc:
            self.logger.error("Error during AsyncBrowserPool cleanup: %s", exc)


__all__ = ["BrowserPoolManager"]
