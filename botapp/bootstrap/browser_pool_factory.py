"""Factories for browser pool resources used by the bot."""

from __future__ import annotations
from tracking import t

from automation.availability import AvailabilityChecker
from automation.browser.async_browser_pool import AsyncBrowserPool
from automation.browser.manager import BrowserManager

from botapp.config import BotAppConfig


def build_browser_resources(
    config: BotAppConfig,
) -> tuple[AsyncBrowserPool, BrowserManager, AvailabilityChecker]:
    """Construct the browser pool, manager, and availability checker trio."""

    t('botapp.bootstrap.browser_pool_factory.build_browser_resources')

    # Future refactors can leverage ``config.browser`` to fine-tune pool behaviour.
    _ = config
    browser_pool = AsyncBrowserPool()

    # Enable natural navigation for anti-bot evasion
    # This ensures all browsers open to main site first before navigating to court pages
    browser_pool.enable_natural_navigation(True)

    browser_manager = BrowserManager(pool=browser_pool)
    availability_checker = AvailabilityChecker(browser_pool)

    return browser_pool, browser_manager, availability_checker


__all__ = ['build_browser_resources']
