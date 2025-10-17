"""Initialization helpers for the async browser pool."""

from __future__ import annotations
from tracking import t

import asyncio
import logging
from typing import Optional

from playwright.async_api import async_playwright

from infrastructure.constants import BrowserPoolConfig, BrowserTimeouts

logger = logging.getLogger(__name__)


async def start_pool(pool) -> None:
    """Initialize Playwright, launch Chromium, and pre-navigate court pages."""

    t('automation.browser.pool.init.start_pool')
    try:
        logger.info("Starting Playwright...")
        pool.playwright = await async_playwright().start()

        logger.info("Launching Chromium browser...")
        pool.browser = await pool.playwright.chromium.launch(
            headless=False,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--window-size=1920,1080',
                '--start-maximized',
            ],
        )

        logger.info("Initializing browser pool with parallel navigation and retry")
        tasks = []
        for index, court in enumerate(pool.courts):
            delay = index * 1.5
            tasks.append(create_and_navigate_court_page_with_stagger(pool, court, delay))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful_courts = 0
        failed_courts = []
        for court, result in zip(pool.courts, results):
            if isinstance(result, Exception):
                logger.error("❌ Court %s failed to initialize: %s", court, result)
                failed_courts.append(court)
            else:
                successful_courts += 1
                logger.info("✅ Court %s initialized successfully", court)

        if successful_courts == 0:
            raise RuntimeError(f"All court initializations failed: 0/{len(pool.courts)} courts ready")

        if successful_courts < len(pool.courts):
            logger.warning(
                "⚠️ PARTIAL Browser pool initialization: %s/%s courts ready",
                successful_courts,
                len(pool.courts),
            )
            logger.warning("Failed courts: %s", failed_courts)
            logger.info("Continuing with available courts...")
        else:
            logger.info("✅ FULL Browser pool initialized with %s/%s courts ready", successful_courts, len(pool.courts))

        pool.is_partially_ready = successful_courts < len(pool.courts)
    except Exception:
        await cleanup_on_failure(pool)
        raise


async def create_and_navigate_court_page_with_stagger(pool, court: int, initial_delay: float):
    """Apply staggered delay before creating the court page with retries."""

    t('automation.browser.pool.init.create_and_navigate_court_page_with_stagger')
    if initial_delay > 0:
        if not pool.production_mode:
            logger.info("Court %s: Waiting %ss before initialization", court, initial_delay)
        await asyncio.sleep(initial_delay)

    return await create_and_navigate_court_page_with_retry(pool, court)


async def create_and_navigate_court_page_with_retry(pool, court: int):
    """Retry court page creation with exponential backoff."""

    t('automation.browser.pool.init.create_and_navigate_court_page_with_retry')
    for attempt in range(BrowserPoolConfig.MAX_RETRY_ATTEMPTS):
        try:
            return await create_and_navigate_court_page_safe(pool, court)
        except Exception as exc:
            if attempt < BrowserPoolConfig.MAX_RETRY_ATTEMPTS - 1:
                delay = BrowserTimeouts.RETRY_DELAY_BASE ** (attempt + 1)
                logger.warning(
                    "Court %s attempt %s/%s failed: %s",
                    court,
                    attempt + 1,
                    BrowserPoolConfig.MAX_RETRY_ATTEMPTS,
                    exc,
                )
                if not pool.production_mode:
                    logger.info("Court %s retrying in %ss", court, delay)
                await asyncio.sleep(delay)
            else:
                logger.error(
                    "Court %s failed after %s attempts: %s",
                    court,
                    BrowserPoolConfig.MAX_RETRY_ATTEMPTS,
                    exc,
                )
                raise


async def create_and_navigate_court_page_safe(pool, court: int):
    """Create a context + page for a court and pre-navigate to its calendar."""

    t('automation.browser.pool.init.create_and_navigate_court_page_safe')
    try:
        context = await pool.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='es-GT',
            timezone_id='America/Guatemala',
        )
        page = await context.new_page()

        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications'
                    ? Promise.resolve({ state: Notification.permission })
                    : originalQuery(parameters)
            );
        """)

        pool.pages[court] = page
        pool.contexts[court] = context

        if court in pool.DIRECT_COURT_URLS:
            court_url = pool.DIRECT_COURT_URLS[court]
            if not pool.production_mode:
                logger.debug("Court %s: Pre-navigating to %s", court, court_url)

            await page.goto(court_url, wait_until='domcontentloaded', timeout=BrowserTimeouts.SLOW_NAVIGATION)
            final_url = page.url
            if not pool.production_mode:
                logger.info("Court %s current URL after navigation: %s", court, final_url)
            if '/datetime/' in final_url:
                logger.warning(
                    "Court %s: ended up on booking form URL instead of calendar",
                    court,
                )
            try:
                await page.wait_for_selector('[class*="time"]', timeout=30000)
                if not pool.production_mode:
                    logger.debug("Court %s: Calendar elements loaded", court)
            except Exception:
                logger.warning("Court %s: Calendar elements not found, continuing anyway", court)

            warmup_delay = getattr(pool, 'WARMUP_DELAY', 10.0)
            logger.info("Court %s: Warming up browser for %ss", court, warmup_delay)
            await asyncio.sleep(warmup_delay)
            logger.info("Court %s: Browser warm-up completed", court)
        else:
            logger.warning("Court %s: No direct URL available for pre-navigation", court)

        return True
    except Exception as exc:
        await _cleanup_failed_page(pool, court)
        raise exc


async def cleanup_on_failure(pool) -> None:
    """Clean up resources when startup fails."""

    t('automation.browser.pool.init.cleanup_on_failure')
    await _cleanup_failed_page(pool, None, total_cleanup=True)


async def _cleanup_failed_page(pool, court: Optional[int], total_cleanup: bool = False) -> None:
    """Close page/context for a specific court or perform full cleanup."""

    if court is not None:
        page = pool.pages.pop(court, None)
        if page:
            try:
                await page.close()
            except Exception:
                pass
        context = pool.contexts.pop(court, None)
        if context:
            try:
                await context.close()
            except Exception:
                pass
        return

    # total cleanup
    for page in pool.pages.values():
        try:
            await page.close()
        except Exception:
            pass
    for context in pool.contexts.values():
        try:
            await context.close()
        except Exception:
            pass

    if pool.browser:
        try:
            await pool.browser.close()
        except Exception:
            pass
    if pool.playwright:
        try:
            await pool.playwright.stop()
        except Exception:
            pass

    pool.pages.clear()
    pool.contexts.clear()
    pool.browser = None
    pool.playwright = None
