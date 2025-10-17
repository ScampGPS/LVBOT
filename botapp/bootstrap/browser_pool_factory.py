"""Factories for browser pool resources used by the bot."""

from __future__ import annotations
from tracking import t

from automation.availability import AvailabilityChecker
from automation.browser.async_browser_pool import AsyncBrowserPool
from automation.browser.manager import BrowserManager


def build_browser_resources() -> tuple[AsyncBrowserPool, BrowserManager, AvailabilityChecker]:
    """Construct the browser pool, manager, and availability checker trio."""

    t('botapp.bootstrap.browser_pool_factory.build_browser_resources')

    browser_pool = AsyncBrowserPool()
    browser_manager = BrowserManager(pool=browser_pool)
    availability_checker = AvailabilityChecker(browser_pool)

    return browser_pool, browser_manager, availability_checker


__all__ = ['build_browser_resources']
