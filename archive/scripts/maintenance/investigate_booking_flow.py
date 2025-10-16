"""
Investigate the actual booking flow and why we're seeing rules page instead of calendar
"""
from utils.tracking import t
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

async def investigate_booking_flow():
    """Investigate the booking flow step by step"""
    t('archive.scripts.maintenance.investigate_booking_flow.investigate_booking_flow')
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(
            headless=False,  # Show browser for visual debugging
            args=['--disable-blink-features=AutomationControlled']
        )
        
        page = await browser.new_page()
        
        # Step 1: Navigate to base URL
        base_url = "https://clublavilla.as.me/"
        logger.info(f"\n=== Step 1: Navigate to base URL ===")
        logger.info(f"URL: {base_url}")
        
        await page.goto(base_url, wait_until='networkidle')
        await page.screenshot(path="step1_base_page.png")
        logger.info("Screenshot: step1_base_page.png")
        
        # Look for booking links or buttons
        logger.info("\nLooking for booking links...")
        links = await page.query_selector_all('a')
        for i, link in enumerate(links[:10]):
            href = await link.get_attribute('href')
            text = await link.text_content()
            if href and text:
                logger.info(f"Link {i}: {text.strip()[:50]} -> {href}")
        
        # Step 2: Try the direct appointment URL
        logger.info(f"\n=== Step 2: Direct appointment URL ===")
        appointment_url = "https://clublavilla.as.me/schedule/7d558012/appointment/15970897"
        logger.info(f"URL: {appointment_url}")
        
        await page.goto(appointment_url, wait_until='networkidle')
        await page.wait_for_timeout(2000)
        await page.screenshot(path="step2_appointment_page.png")
        logger.info("Screenshot: step2_appointment_page.png")
        logger.info(f"Current URL: {page.url}")
        
        # Check what's on the page
        h1_elements = await page.query_selector_all('h1')
        h2_elements = await page.query_selector_all('h2')
        
        logger.info(f"\nFound {len(h1_elements)} h1 elements:")
        for h1 in h1_elements[:3]:
            text = await h1.text_content()
            logger.info(f"  H1: {text[:100] if text else 'No text'}")
            
        logger.info(f"\nFound {len(h2_elements)} h2 elements:")
        for h2 in h2_elements[:3]:
            text = await h2.text_content()
            logger.info(f"  H2: {text[:100] if text else 'No text'}")
        
        # Step 3: Look for any accept/continue buttons
        logger.info(f"\n=== Step 3: Looking for accept/continue buttons ===")
        
        button_selectors = [
            'button:has-text("Aceptar")',
            'button:has-text("Continuar")',
            'button:has-text("Accept")',
            'button:has-text("Continue")',
            'button:has-text("Siguiente")',
            'button:has-text("Next")',
            'button[type="submit"]',
            'input[type="submit"]'
        ]
        
        for selector in button_selectors:
            buttons = await page.query_selector_all(selector)
            if buttons:
                logger.info(f"Found {len(buttons)} buttons matching '{selector}'")
                # Click the first one
                button_text = await buttons[0].text_content()
                logger.info(f"Clicking button: {button_text}")
                await buttons[0].click()
                await page.wait_for_load_state('networkidle')
                await page.wait_for_timeout(2000)
                break
        
        await page.screenshot(path="step3_after_button_click.png")
        logger.info("Screenshot: step3_after_button_click.png")
        logger.info(f"Current URL: {page.url}")
        
        # Step 4: Check if we're on calendar page now
        logger.info(f"\n=== Step 4: Checking for calendar elements ===")
        
        # Look for date/time elements
        date_selectors = [
            '.calendar-day',
            '.date-picker',
            '[class*="calendar"]',
            '[class*="date"]',
            '[class*="time"]',
            'button[class*="time"]',
            'button[class*="slot"]'
        ]
        
        for selector in date_selectors:
            elements = await page.query_selector_all(selector)
            if elements:
                logger.info(f"Found {len(elements)} elements matching '{selector}'")
                # Log first few
                for i, elem in enumerate(elements[:3]):
                    text = await elem.text_content()
                    if text and text.strip():
                        logger.info(f"  Element {i}: {text.strip()[:50]}")
        
        # Step 5: Try the direct calendar URL with parameters
        logger.info(f"\n=== Step 5: Direct calendar URL with parameters ===")
        calendar_url = "https://clublavilla.as.me/schedule/7d558012/appointment/15970897/calendar/4282490?appointmentTypeIds[]=15970897"
        logger.info(f"URL: {calendar_url}")
        
        await page.goto(calendar_url, wait_until='networkidle')
        await page.wait_for_timeout(3000)
        await page.screenshot(path="step5_calendar_direct.png")
        logger.info("Screenshot: step5_calendar_direct.png")
        logger.info(f"Current URL: {page.url}")
        
        # Check if we're still on rules page
        rules_text = await page.query_selector('text="Reglamento del sistema de citas"')
        if rules_text:
            logger.warning("Still on rules page!")
            
            # Look for any form or checkbox to accept rules
            checkboxes = await page.query_selector_all('input[type="checkbox"]')
            logger.info(f"Found {len(checkboxes)} checkboxes")
            
            forms = await page.query_selector_all('form')
            logger.info(f"Found {len(forms)} forms")
            
            # Try to find and click any accept button again
            accept_button = await page.query_selector('button:has-text("Aceptar"), button[type="submit"], input[type="submit"]')
            if accept_button:
                logger.info("Found accept button, clicking...")
                await accept_button.click()
                await page.wait_for_load_state('networkidle')
                await page.wait_for_timeout(2000)
                await page.screenshot(path="step5_after_accept.png")
                logger.info("Screenshot: step5_after_accept.png")
                logger.info(f"Current URL after accept: {page.url}")
        
        # Final check for calendar
        logger.info(f"\n=== Final Calendar Check ===")
        time_buttons = await page.query_selector_all('button')
        time_pattern_found = False
        
        for button in time_buttons[:20]:
            text = await button.text_content()
            if text and ':' in text and any(time in text for time in ['AM', 'PM', '00']):
                if not time_pattern_found:
                    logger.info("Found time slot buttons!")
                    time_pattern_found = True
                logger.info(f"  Time slot: {text.strip()}")
        
        if not time_pattern_found:
            logger.warning("No time slot buttons found on page")
        
        # Keep browser open for manual inspection
        logger.info("\nBrowser will stay open for 30 seconds for manual inspection...")
        await page.wait_for_timeout(30000)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(investigate_booking_flow())
