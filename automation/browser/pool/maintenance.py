"""Maintenance and shutdown helpers for the async browser pool."""

from __future__ import annotations
from tracking import t

import asyncio
import logging
from typing import Dict

from infrastructure.constants import BrowserTimeouts

logger = logging.getLogger(__name__)


async def set_critical_operation(pool, in_progress: bool) -> None:
    """Toggle the critical operation flag to block refresh cycles."""

    t('automation.browser.pool.maintenance.set_critical_operation')
    async with pool.lock:
        pool.critical_operation_in_progress = in_progress
        logger.info("Critical operation flag set to: %s", in_progress)


async def refresh_browser_pages(pool) -> Dict[int, bool]:
    """Refresh all initialized court pages to prevent staleness."""

    t('automation.browser.pool.maintenance.refresh_browser_pages')
    refresh_results: Dict[int, bool] = {}

    logger.info("🔄 Starting browser page refresh cycle")
    if not pool.pages:
        logger.warning("No browser pages to refresh")
        return refresh_results

    for court in pool.courts:
        page = pool.pages.get(court)
        if not page:
            logger.warning("Court %s has no page to refresh", court)
            refresh_results[court] = False
            continue

        court_url = pool.DIRECT_COURT_URLS.get(court)
        if not court_url:
            logger.error("No URL found for court %s", court)
            refresh_results[court] = False
            continue

        try:
            logger.info("🔄 Refreshing Court %s browser page", court)
            await page.goto(court_url, wait_until='domcontentloaded', timeout=30000)
            logger.info("✅ Court %s refreshed successfully", court)
            refresh_results[court] = True
        except Exception as exc:
            logger.error("❌ Failed to refresh Court %s: %s", court, exc)
            refresh_results[court] = False

    successful = sum(1 for success in refresh_results.values() if success)
    logger.info("🔄 REFRESH COMPLETE: %s/%s courts refreshed successfully", successful, len(refresh_results))
    return refresh_results


async def stop_pool(pool) -> None:
    """Shut down browser resources, waiting for critical operations if needed."""

    t('automation.browser.pool.maintenance.stop_pool')
    logger.info("🔴 STARTING BROWSER POOL SHUTDOWN...")

    if pool.critical_operation_in_progress:
        logger.info("⏳ Waiting for critical booking operations to complete before shutdown...")
        max_wait_time = 300
        waited = 0
        while pool.critical_operation_in_progress and waited < max_wait_time:
            await asyncio.sleep(1)
            waited += 1
            if waited % 30 == 0:
                logger.info("⏳ Still waiting for critical operations... (%ss elapsed)", waited)
        if pool.critical_operation_in_progress:
            logger.warning("⚠️ Forcing shutdown after %ss - critical operation still in progress", max_wait_time)
        else:
            logger.info("✅ Critical operations completed, proceeding with shutdown")

    page_errors = []
    for court, page in pool.pages.items():
        try:
            if page and not page.is_closed():
                await page.close()
                logger.info("✅ Page for court %s closed", court)
            else:
                logger.info("⚠️ Page for court %s already closed", court)
        except Exception as exc:
            if "Connection closed" in str(exc) or "Target closed" in str(exc):
                logger.debug("Page %s already disconnected", court)
            else:
                logger.error("Error closing page for court %s: %s", court, exc)
                page_errors.append((court, str(exc)))

    context_errors = []
    for court, context in pool.contexts.items():
        try:
            if context:
                await context.close()
                logger.info("✅ Context for court %s closed", court)
        except Exception as exc:
            if "Connection closed" in str(exc) or "Target closed" in str(exc):
                logger.debug("Context %s already disconnected", court)
            else:
                logger.error("Error closing context for court %s: %s", court, exc)
                context_errors.append((court, str(exc)))

    pool.pages.clear()
    pool.contexts.clear()
    logger.info("✅ Page and context dictionaries cleared")

    if pool.browser:
        try:
            await pool.browser.close()
            logger.info("✅ Chromium browser closed")
        except Exception as exc:
            if "Connection closed" in str(exc) or "Target closed" in str(exc):
                logger.info("ℹ️ Browser already disconnected")
            else:
                logger.error("❌ Error closing browser: %s", exc)

    if pool.playwright:
        try:
            await pool.playwright.stop()
            logger.info("✅ Playwright stopped")
        except Exception as exc:
            logger.error("❌ Error stopping playwright: %s", exc)

    if page_errors or context_errors:
        logger.warning(
            "⚠️ Shutdown completed with %s page errors and %s context errors",
            len(page_errors),
            len(context_errors),
        )
    else:
        logger.info("✅ BROWSER POOL SHUTDOWN COMPLETED SUCCESSFULLY")

    pool.browser = None
    pool.playwright = None
    pool.critical_operation_in_progress = False
    pool.is_partially_ready = False


async def legacy_stop(pool) -> None:
    """Legacy stop helper retained for compatibility."""

    t('automation.browser.pool.maintenance.legacy_stop')
    logger.info("Stopping AsyncBrowserPool (legacy path)...")

    try:
        for court, page in pool.pages.items():
            try:
                logger.debug("Closing page for court %s", court)
                await page.close()
            except Exception as exc:
                if "Connection closed" not in str(exc) and "Target closed" not in str(exc):
                    logger.error("Error closing page for court %s: %s", court, exc)

        for court, context in pool.contexts.items():
            try:
                logger.debug("Closing context for court %s", court)
                await context.close()
            except Exception as exc:
                if "Connection closed" not in str(exc) and "Target closed" not in str(exc):
                    logger.error("Error closing context for court %s: %s", court, exc)

        if pool.browser:
            try:
                logger.info("Closing browser...")
                await pool.browser.close()
            except Exception as exc:
                if "Connection closed" not in str(exc) and "Target closed" not in str(exc):
                    logger.error("Error closing browser: %s", exc)

        if pool.playwright:
            try:
                logger.info("Stopping playwright...")
                await pool.playwright.stop()
            except Exception as exc:
                logger.error("Error stopping playwright: %s", exc)

        pool.pages.clear()
        pool.contexts.clear()
        pool.browser = None
        pool.playwright = None

        logger.info("✅ AsyncBrowserPool stopped successfully (legacy path)")
    except Exception as exc:
        logger.error("Error during AsyncBrowserPool cleanup: %s", exc)
