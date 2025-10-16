#!/usr/bin/env python3
"""
Check actual form field names on the booking page
"""
from utils.tracking import t
import pathlib
from pathlib import Path
import sys

ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


import asyncio
import logging
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_form_fields():
    """Check the actual form field names"""
    t('archive.scripts.playwright.check_form_fields.check_form_fields')
    
    # Test URL
    target_date = datetime.now() + timedelta(days=1)
    date_str = target_date.strftime("%Y-%m-%d")
    direct_url = f"https://clublavilla.as.me/schedule/7d558012/appointment/15970897/calendar/4291312/datetime/{date_str}T10:00:00-06:00?appointmentTypeIds[]=15970897"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Navigate quickly
        await page.goto(direct_url, wait_until='commit')
        await page.wait_for_selector('form', timeout=5000)
        
        # Find all input fields
        logger.info("=== FORM FIELDS FOUND ===")
        
        # Check different possible selectors
        selectors_to_check = [
            'input[name*="client"]',
            'input[name*="phone"]',
            'input[name*="email"]',
            'input[name*="name"]',
            'input[type="text"]',
            'input[type="tel"]',
            'input[type="email"]',
            'input'
        ]
        
        for selector in selectors_to_check:
            elements = await page.locator(selector).all()
            if elements:
                logger.info(f"\nSelector: {selector}")
                for i, elem in enumerate(elements):
                    name = await elem.get_attribute('name')
                    field_type = await elem.get_attribute('type')
                    placeholder = await elem.get_attribute('placeholder')
                    logger.info(f"  Field {i+1}: name='{name}', type='{field_type}', placeholder='{placeholder}'")
        
        # Also check for phone field specifically
        logger.info("\n=== PHONE FIELD SEARCH ===")
        phone_selectors = [
            'input[type="tel"]',
            'input[placeholder*="phone"]',
            'input[placeholder*="teléfono"]',
            'input[name*="phone"]',
            'input[id*="phone"]'
        ]
        
        for selector in phone_selectors:
            count = await page.locator(selector).count()
            if count > 0:
                logger.info(f"Found {count} field(s) with selector: {selector}")
                elem = page.locator(selector).first
                name = await elem.get_attribute('name')
                logger.info(f"  Phone field name: '{name}'")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_form_fields())
