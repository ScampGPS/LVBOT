"""Minimal async helpers for locating the Acuity scheduling iframe."""

from __future__ import annotations
from tracking import t

import asyncio
import logging
from typing import Optional

from playwright.async_api import Frame, Page

from infrastructure.constants import (
    SCHEDULING_IFRAME_URL_PATTERN,
    DEFAULT_TIMEOUT_SECONDS,
    FAST_POLL_INTERVAL,
)

logger = logging.getLogger(__name__)


class BrowserHelpers:
    """Utilities to locate the Acuity scheduling iframe on a page."""

    @staticmethod
    async def get_scheduling_frame(
        page: Page,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> Optional[Frame]:
        """Poll the page until the scheduling iframe is located."""
        t('automation.browser.async_browser_helpers.BrowserHelpers.get_scheduling_frame')
        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            try:
                for frame in page.frames:
                    if SCHEDULING_IFRAME_URL_PATTERN in frame.url:
                        logger.debug("Found scheduling iframe at %s", frame.url)
                        return frame
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.debug("Error while inspecting frames: %s", exc)
            await asyncio.sleep(FAST_POLL_INTERVAL)

        logger.debug(
            "Scheduling iframe not found after %.1fs (modern Acuity pages may not use it)",
            timeout,
        )
        return None

    @staticmethod
    async def wait_for_iframe(page: Page, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Optional[Frame]:
        """Backward-compatible alias for :meth:`get_scheduling_frame`."""
        t('automation.browser.async_browser_helpers.BrowserHelpers.wait_for_iframe')
        return await BrowserHelpers.get_scheduling_frame(page, timeout)


__all__ = ["BrowserHelpers"]
