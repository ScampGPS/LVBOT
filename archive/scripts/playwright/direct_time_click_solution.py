"""
Direct solution to click time slots even with overlay present
"""
from tracking import t
import pathlib
from pathlib import Path
import sys

ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import asyncio
import time
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def direct_time_click():
    """Click time slots directly using various methods"""
    t('archive.scripts.playwright.direct_time_click_solution.direct_time_click')
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(
            headless=False,  # Show browser for visual debugging
            args=['--disable-blink-features=AutomationControlled']
        )
        
        page = await browser.new_page()
        
        # Navigate to the calendar URL
        url = "https://clublavilla.as.me/schedule/7d558012/appointment/15970897/calendar/4282490?appointmentTypeIds[]=15970897"
        logger.info(f"Navigating to: {url}")
        
        start_nav = time.time()
        await page.goto(url, wait_until='networkidle')
        nav_time = time.time() - start_nav
        logger.info(f"Navigation took: {nav_time:.2f} seconds")
        
        await page.wait_for_timeout(2000)
        
        # Method 1: Direct button selector with force click
        logger.info("\n=== Method 1: Direct button click ===")
        
        start_query = time.time()
        time_buttons = await page.query_selector_all('button.time-selection')
        query_time = time.time() - start_query
        logger.info(f"Query selector took: {query_time:.2f} seconds")
        logger.info(f"Found {len(time_buttons)} time buttons")
        
        if time_buttons:
            # Click the first available time slot
            first_button = time_buttons[0]
            button_text = await first_button.text_content()
            logger.info(f"Clicking time button: {button_text}")
            
            # Use JavaScript click to bypass any overlay
            await page.evaluate('(element) => element.click()', first_button)
            
            # Wait for navigation
            logger.info("Waiting for form to load...")
            await page.wait_for_load_state('networkidle', timeout=10000)
            await page.wait_for_timeout(2000)
            
            # Check current URL
            current_url = page.url
            logger.info(f"Current URL: {current_url}")
            
            # Take screenshot
            await page.screenshot(path="after_time_click_direct.png")
            
            # Check for form fields
            form_fields = await page.query_selector_all('input[type="text"], input[type="email"], input[type="tel"]')
            logger.info(f"Form fields found: {len(form_fields)}")
            
            if form_fields:
                logger.info("SUCCESS! Reached the booking form!")
                
                # Log field details
                for i, field in enumerate(form_fields):
                    field_name = await field.get_attribute('name')
                    field_placeholder = await field.get_attribute('placeholder')
                    field_id = await field.get_attribute('id')
                    logger.info(f"  Field {i}: name='{field_name}', id='{field_id}', placeholder='{field_placeholder}'")
                
                # Try filling the form
                logger.info("\n=== Testing form filling ===")
                
                # Look for specific fields
                first_name_field = await page.query_selector('input[name="client.firstName"], input[name="firstName"], input[placeholder*="First"], input[placeholder*="Nombre"]')
                if first_name_field:
                    logger.info("Filling first name field...")
                    await first_name_field.fill("Test")
                    
                last_name_field = await page.query_selector('input[name="client.lastName"], input[name="lastName"], input[placeholder*="Last"], input[placeholder*="Apellido"]')
                if last_name_field:
                    logger.info("Filling last name field...")
                    await last_name_field.fill("User")
                
                await page.screenshot(path="form_filled_test.png")
                logger.info("Form filling test completed")
                
        # Method 2: If method 1 didn't work, try different selectors
        if not form_fields:
            logger.info("\n=== Method 2: Alternative selectors ===")
            
            # Try different button selectors
            alt_selectors = [
                'button:has-text("11:00")',
                'button:has-text("12:00")',
                'button:has-text("10:00")',
                '[class*="time"]:has-text("11:00")',
                '[class*="time"]:has-text("12:00")'
            ]
            
            for selector in alt_selectors:
                button = await page.query_selector(selector)
                if button:
                    button_text = await button.text_content()
                    logger.info(f"Found button with selector '{selector}': {button_text}")
                    
                    # Click using JavaScript
                    await page.evaluate('(element) => element.click()', button)
                    await page.wait_for_load_state('networkidle', timeout=5000)
                    
                    # Check for form
                    form_fields = await page.query_selector_all('input')
                    if form_fields:
                        logger.info(f"SUCCESS with selector '{selector}'! Found {len(form_fields)} form fields")
                        break
        
        # Method 3: Direct URL navigation (bypass calendar completely)
        if not form_fields:
            logger.info("\n=== Method 3: Direct datetime URL ===")
            
            # Try direct navigation to a specific time
            base_url = "https://clublavilla.as.me/schedule/7d558012/appointment/15970897"
            datetime_url = f"{base_url}/datetime/2025-07-30T11:00:00-06:00?appointmentTypeIds[]=15970897"
            
            logger.info(f"Navigating directly to: {datetime_url}")
            await page.goto(datetime_url, wait_until='networkidle')
            await page.wait_for_timeout(2000)
            
            # Check for form
            form_fields = await page.query_selector_all('input')
            logger.info(f"Form fields after direct navigation: {len(form_fields)}")
            
            if form_fields:
                logger.info("SUCCESS with direct URL navigation!")
                await page.screenshot(path="direct_url_success.png")
        
        # Final status
        logger.info("\n=== Final Status ===")
        logger.info(f"Current URL: {page.url}")
        logger.info(f"Page title: {await page.title()}")
        
        # Check what's visible on the page
        visible_text = await page.evaluate('''() => {
            const headings = [];
            document.querySelectorAll('h1, h2, h3').forEach(h => {
                if (h.offsetParent !== null) {
                    headings.push(h.textContent.trim());
                }
            });
            return headings;
        }''')
        
        logger.info(f"Visible headings: {visible_text}")
        
        logger.info("\nBrowser will stay open for 30 seconds for manual inspection...")
        await page.wait_for_timeout(30000)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(direct_time_click())
