"""Navigation helpers shared across booking executors."""

from __future__ import annotations
from utils.tracking import t

import asyncio
import logging
import time
from typing import Any, Dict, Optional, Tuple

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)


class OptimizedNavigation:
    """Handles optimized navigation strategies for booking URLs."""

    @staticmethod
    async def navigate_with_progressive_fallback(
        page: Page,
        url: str,
        max_timeout: int = 30000,
    ) -> Tuple[bool, float]:
        t('automation.executors.navigation.OptimizedNavigation.navigate_with_progressive_fallback')
        import time as _time

        start_time = _time.time()

        try:
            logger.info("Attempting fast navigation (commit only)...")
            await page.goto(url, wait_until="commit", timeout=5000)
            try:
                await page.wait_for_selector("form", timeout=5000)
                nav_time = _time.time() - start_time
                logger.info("✅ Fast navigation successful in %.2fs", nav_time)
                return True, nav_time
            except PlaywrightTimeout:
                logger.warning("Form not found after commit, trying next strategy...")
        except Exception as exc:
            logger.debug("Fast navigation failed: %s", exc)

        try:
            logger.info("Attempting standard navigation (domcontentloaded)...")
            await page.goto(url, wait_until="domcontentloaded", timeout=10000)
            await page.wait_for_timeout(2000)
            form_present = await page.locator("form").count() > 0
            if form_present:
                nav_time = _time.time() - start_time
                logger.info("✅ Standard navigation successful in %.2fs", nav_time)
                return True, nav_time
            logger.warning("Form not present after domcontentloaded")
        except Exception as exc:
            logger.debug("Standard navigation failed: %s", exc)

        try:
            logger.info("Attempting full navigation (networkidle)...")
            await page.goto(url, wait_until="networkidle", timeout=max_timeout)
            nav_time = _time.time() - start_time
            logger.info("✅ Full navigation completed in %.2fs", nav_time)
            return True, nav_time
        except PlaywrightTimeout:
            nav_time = _time.time() - start_time
            logger.warning("Navigation timed out after %.2fs, checking for usable page", nav_time)
            try:
                form_present = await page.locator("form").count() > 0
                if form_present:
                    logger.info("Form present despite timeout, continuing...")
                    return True, nav_time
            except Exception:
                pass
            return False, nav_time
        except Exception as exc:
            nav_time = _time.time() - start_time
            logger.error("Navigation failed after %.2fs: %s", nav_time, exc)
            return False, nav_time

    @staticmethod
    async def ensure_page_ready(page: Page, timeout: int = 10000) -> bool:
        t('automation.executors.navigation.OptimizedNavigation.ensure_page_ready')
        try:
            loading_selectors = [
                ".loading",
                ".spinner",
                "[class*='load']",
                "[class*='spin']",
                ".loader",
            ]
            for selector in loading_selectors:
                try:
                    await page.wait_for_selector(selector, state="hidden", timeout=1000)
                except Exception:
                    pass

            await page.wait_for_selector("form", state="visible", timeout=timeout)

            key_fields = [
                'input[name="client.firstName"]',
                'input[name="client.lastName"]',
                'input[name="client.email"]',
            ]
            for field in key_fields:
                await page.wait_for_selector(field, state="visible", timeout=2000)

            try:
                await page.wait_for_selector('input[name="client.phone"]', state="attached", timeout=3000)
            except Exception:
                logger.debug("Phone field not immediately available, but form likely ready")

            await page.evaluate("() => document.readyState")
            return True
        except Exception as exc:
            logger.error("Page readiness check failed: %s", exc)
            return False

    @staticmethod
    async def navigate_and_validate(
        page: Page,
        url: str,
        expected_form_fields: Optional[list] = None,
    ) -> Tuple[bool, str]:
        t('automation.executors.navigation.OptimizedNavigation.navigate_and_validate')
        success, nav_time = await OptimizedNavigation.navigate_with_progressive_fallback(page, url)
        if not success:
            return False, "Navigation failed"

        if expected_form_fields:
            for selector in expected_form_fields:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                except Exception:
                    return False, f"Missing expected field: {selector}"

        return True, f"Navigation completed in {nav_time:.2f}s"


class ReliableNavigation:
    """Centralized navigation utility that works around Playwright goto() hanging."""

    @staticmethod
    async def navigate_to_url(
        page: Page,
        url: str,
        timeout_seconds: int = 10,
        enable_network_logging: bool = False,
    ) -> Dict[str, Any]:
        t('automation.executors.navigation.ReliableNavigation.navigate_to_url')
        start_time = time.time()
        dom_ready = asyncio.Event()
        navigation_response = None
        request_count = 0
        response_count = 0

        def on_dom_ready() -> None:
            t('automation.executors.navigation.ReliableNavigation.navigate_to_url.on_dom_ready')
            dom_time = time.time() - start_time
            logger.info("[RELIABLE NAV] DOM ready at %.2fs", dom_time)
            dom_ready.set()

        def on_request(request) -> None:
            t('automation.executors.navigation.ReliableNavigation.navigate_to_url.on_request')
            nonlocal request_count
            request_count += 1
            if enable_network_logging:
                elapsed = time.time() - start_time
                logger.debug("[RELIABLE NAV %.1fs] REQ #%s: %s", elapsed, request_count, request.url[:80])

        def on_response(response) -> None:
            t('automation.executors.navigation.ReliableNavigation.navigate_to_url.on_response')
            nonlocal response_count, navigation_response
            response_count += 1
            if enable_network_logging:
                elapsed = time.time() - start_time
                logger.debug(
                    "[RELIABLE NAV %.1fs] RES #%s: %s %s",
                    elapsed,
                    response_count,
                    response.status,
                    response.url[:80],
                )
            if response.url == url or response.url.startswith(url.split("?")[0]):
                navigation_response = response

        page.on("domcontentloaded", on_dom_ready)
        if enable_network_logging:
            page.on("request", on_request)
            page.on("response", on_response)

        try:
            logger.info("[RELIABLE NAV] Starting navigation to: %s", url[:100])
            navigation_task = asyncio.create_task(page.goto(url, wait_until="commit", timeout=5000))

            try:
                await asyncio.wait_for(dom_ready.wait(), timeout=timeout_seconds)
                dom_ready_time = time.time() - start_time
                logger.info("[RELIABLE NAV] DOM ready in %.2fs", dom_ready_time)
                try:
                    await asyncio.wait_for(navigation_task, timeout=2.0)
                    navigation_time = time.time() - start_time
                    logger.info("[RELIABLE NAV] Navigation task completed in %.2fs", navigation_time)
                except asyncio.TimeoutError:
                    navigation_time = time.time() - start_time
                    logger.warning("[RELIABLE NAV] Navigation task hanging after %.2fs, proceeding", navigation_time)
                    navigation_task.cancel()

                return {
                    "success": True,
                    "navigation_time": navigation_time,
                    "dom_ready_time": dom_ready_time,
                    "status_code": navigation_response.status if navigation_response else 200,
                    "requests": request_count,
                    "responses": response_count,
                }
            except asyncio.TimeoutError:
                failed_time = time.time() - start_time
                logger.error("[RELIABLE NAV] DOM never loaded after %.2fs", failed_time)
                navigation_task.cancel()
                return {
                    "success": False,
                    "navigation_time": failed_time,
                    "error": f"DOM never loaded after {timeout_seconds}s",
                    "requests": request_count,
                    "responses": response_count,
                }
        except Exception as exc:
            error_time = time.time() - start_time
            logger.error("[RELIABLE NAV] Navigation error after %.2fs: %s", error_time, exc)
            return {
                "success": False,
                "navigation_time": error_time,
                "error": str(exc),
                "requests": request_count,
                "responses": response_count,
            }
        finally:
            try:
                page.remove_listener("domcontentloaded", on_dom_ready)
                if enable_network_logging:
                    page.remove_listener("request", on_request)
                    page.remove_listener("response", on_response)
            except Exception:
                pass

    @staticmethod
    async def navigate_with_form_check(
        page: Page,
        url: str,
        form_selectors: Optional[list] = None,
        timeout_seconds: int = 15,
    ) -> Dict[str, Any]:
        t('automation.executors.navigation.ReliableNavigation.navigate_with_form_check')
        result = await ReliableNavigation.navigate_to_url(page, url, timeout_seconds)
        if not result.get("success"):
            return result

        selectors = form_selectors or [
            'button.time-selection',
            'input[name="client.firstName"]',
        ]

        for selector in selectors:
            try:
                await page.wait_for_selector(selector, timeout=timeout_seconds * 1000)
            except Exception as exc:
                result["success"] = False
                result["error"] = f"Missing selector {selector}: {exc}"
                return result

        result["success"] = True
        return result


__all__ = ["OptimizedNavigation", "ReliableNavigation"]
