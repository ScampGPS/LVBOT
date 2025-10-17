"""Signal collection helpers for browser health checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from tracking import t


@dataclass
class PoolSignals:
    ready: bool
    browser_connected: bool
    critical_operation: bool
    partially_ready: bool
    available_courts: int
    requested_courts: int


@dataclass
class CourtSignals:
    url_accessible: bool
    javascript_works: bool
    network_ok: bool
    dom_queryable: bool
    current_url: Optional[str]
    error: Optional[str]


async def collect_pool_signals(browser_pool: Any) -> PoolSignals:
    """Collect high-level signals about the browser pool."""

    t('automation.browser.health.collectors.collect_pool_signals')

    ready = browser_pool.is_ready()
    browser_connected = bool(getattr(browser_pool, 'browser', None)) and browser_pool.browser.is_connected()
    critical_operation = browser_pool.is_critical_operation_in_progress()
    partially_ready = getattr(browser_pool, 'is_partially_ready', False)
    available_courts = len(browser_pool.get_available_courts()) if hasattr(browser_pool, 'get_available_courts') else 0
    requested_courts = len(getattr(browser_pool, 'courts', []))

    return PoolSignals(
        ready=ready,
        browser_connected=browser_connected,
        critical_operation=critical_operation,
        partially_ready=partially_ready,
        available_courts=available_courts,
        requested_courts=requested_courts,
    )


async def collect_court_signals(page: Any, *, logger: Any, court_number: int) -> CourtSignals:
    """Collect responsiveness signals for a court browser."""

    t('automation.browser.health.collectors.collect_court_signals')

    results = {
        "url_accessible": False,
        "javascript_works": False,
        "network_ok": False,
        "dom_queryable": False,
        "current_url": None,
        "error": None,
    }

    try:
        try:
            current_url = page.url
            results["current_url"] = current_url
            results["url_accessible"] = True
        except Exception as exc:
            logger.warning("Court %s: URL access failed - %s", court_number, exc)
            results["error"] = f"URL access failed: {exc}"
            return CourtSignals(**results)

        try:
            js_result = await page.evaluate("() => 1 + 1")
            if js_result == 2:
                results["javascript_works"] = True
        except Exception as exc:
            logger.warning("Court %s: JavaScript execution failed - %s", court_number, exc)

        try:
            if current_url and ("clublavilla.as.me" in current_url or "acuityscheduling" in current_url):
                results["network_ok"] = True
            else:
                can_reach = await page.evaluate(
                    "() => window.location.hostname.includes('as.me') || window.location.hostname.includes('acuityscheduling')"
                )
                results["network_ok"] = bool(can_reach)
        except Exception as exc:
            logger.warning("Court %s: Network check failed - %s", court_number, exc)

        try:
            button_count = await page.evaluate("() => document.querySelectorAll('button').length")
            results["dom_queryable"] = button_count > 0
        except Exception as exc:
            logger.warning("Court %s: DOM query failed - %s", court_number, exc)

    except Exception as exc:  # pragma: no cover - defensive guard
        logger.error("Court %s: Responsiveness test failed - %s", court_number, exc)
        results["error"] = f"Responsiveness test failed: {exc}"

    return CourtSignals(**results)
