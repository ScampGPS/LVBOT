"""Playwright regression around direct slot URLs exposing booking forms."""

from __future__ import annotations
from tracking import t

import os
from datetime import datetime

import pytest
import pytz
from playwright.async_api import async_playwright

from automation.executors.flows.helpers import build_direct_slot_url


@pytest.mark.asyncio
async def test_direct_slot_page_renders_form_when_enabled():
    """Navigate directly to a slot URL and ensure a booking form appears."""

    t('tests.bot.test_direct_slot_page_playwright.test_direct_slot_page_renders_form_when_enabled')

    flag = os.getenv("LV_SLOT_DEBUG_ENABLE")
    if flag != "1":
        pytest.skip("Set LV_SLOT_DEBUG_ENABLE=1 to run the direct slot Playwright test")

    tz = pytz.timezone("America/Mexico_City")
    target_datetime = tz.localize(datetime(2025, 11, 12, 9, 0))
    url = build_direct_slot_url(1, target_datetime, "09:00")

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            form = await page.query_selector("form")
            assert form is not None, "Booking form not present on direct slot page"
        finally:
            await browser.close()
