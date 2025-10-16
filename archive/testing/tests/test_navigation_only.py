#!/usr/bin/env python3
"""
Test navigation timing in isolation to verify the optimization
"""
from utils.tracking import t

import asyncio
import logging
import time
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from lvbot.utils.optimized_navigation import OptimizedNavigation

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_navigation_strategies():
    """Test different navigation strategies"""
    t('archive.testing.tests.test_navigation_only.test_navigation_strategies')
    
    # Test URL (tomorrow at 10:00)
    target_date = datetime.now() + timedelta(days=1)
    date_str = target_date.strftime("%Y-%m-%d")
    time_slot = "10:00"
    court_number = 1
    
    appointment_type_ids = {1: "15970897", 2: "16021953", 3: "16120442"}
    appointment_type_id = appointment_type_ids[court_number]
    base_url = "https://clublavilla.as.me/schedule/7d558012/appointment"
    calendar_id = "4291312"
    datetime_str = f"{date_str}T{time_slot}:00-06:00"
    direct_url = f"{base_url}/{appointment_type_id}/calendar/{calendar_id}/datetime/{datetime_str}?appointmentTypeIds[]={appointment_type_id}"
    
    logger.info(f"Testing navigation to: {direct_url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # Test 1: Old approach (networkidle with 10s timeout)
        logger.info("\n=== TEST 1: Old Approach (networkidle, 10s timeout) ===")
        page = await context.new_page()
        start = time.time()
        
        try:
            await page.goto(direct_url, wait_until='networkidle', timeout=10000)
            old_time = time.time() - start
            logger.info(f"✅ Old approach completed in {old_time:.2f}s")
        except Exception as e:
            old_time = time.time() - start
            logger.error(f"❌ Old approach failed after {old_time:.2f}s: {type(e).__name__}")
        
        await page.close()
        
        # Test 2: Optimized approach
        logger.info("\n=== TEST 2: Optimized Approach ===")
        page = await context.new_page()
        
        nav_success, nav_message = await OptimizedNavigation.navigate_and_validate(
            page,
            direct_url,
            expected_form_fields=[
                'input[name="client.firstName"]',
                'input[name="client.lastName"]',
                'input[name="client.email"]',
                'input[name="client.phone"]'
            ]
        )
        
        logger.info(f"Result: {nav_success} - {nav_message}")
        
        # Take screenshot for verification
        await page.screenshot(path="optimized_navigation_result.png")
        logger.info("Screenshot saved as optimized_navigation_result.png")
        
        # Test form presence
        form_count = await page.locator('form').count()
        field_count = await page.locator('input[name*="client."]').count()
        logger.info(f"Forms found: {form_count}, Client fields found: {field_count}")
        
        await browser.close()
        
        # Summary
        logger.info("\n=== SUMMARY ===")
        logger.info(f"Old approach: {old_time:.2f}s")
        logger.info(f"Optimized approach: Included in message above")
        logger.info(f"Expected improvement: Faster initial load, more reliable")

if __name__ == "__main__":
    asyncio.run(test_navigation_strategies())