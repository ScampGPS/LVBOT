"""
Fix for the rules overlay blocking the calendar page
"""
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

async def fix_rules_overlay():
    """Test methods to bypass or close the rules overlay"""
    
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
        
        await page.goto(url, wait_until='networkidle')
        await page.wait_for_timeout(2000)
        
        # Method 1: Try to close overlay using JavaScript
        logger.info("\n=== Method 1: Close overlay with JavaScript ===")
        
        try:
            # Find and hide any modal/overlay elements
            await page.evaluate('''() => {
                // Common overlay selectors
                const overlaySelectors = [
                    '.modal', '.overlay', '.popup', '[class*="modal"]', '[class*="overlay"]',
                    '[class*="popup"]', '[class*="rules"]', '[class*="reglamento"]',
                    'div[style*="position: fixed"]', 'div[style*="position: absolute"]'
                ];
                
                overlaySelectors.forEach(selector => {
                    const elements = document.querySelectorAll(selector);
                    elements.forEach(el => {
                        // Check if element is blocking
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 300 && rect.height > 300) {
                            console.log('Hiding overlay:', selector, el);
                            el.style.display = 'none';
                            el.style.visibility = 'hidden';
                        }
                    });
                });
                
                // Also remove any backdrop
                const backdrops = document.querySelectorAll('.backdrop, .modal-backdrop, [class*="backdrop"]');
                backdrops.forEach(el => el.style.display = 'none');
            }''')
            
            logger.info("Attempted to hide overlays with JavaScript")
            await page.screenshot(path="method1_js_hide.png")
            
        except Exception as e:
            logger.error(f"JavaScript method failed: {e}")
        
        # Method 2: Try clicking outside the overlay
        logger.info("\n=== Method 2: Click outside overlay ===")
        
        try:
            # Click at multiple points to try to dismiss overlay
            await page.mouse.click(50, 50)  # Top left
            await page.wait_for_timeout(500)
            await page.mouse.click(1200, 50)  # Top right
            await page.wait_for_timeout(500)
            await page.screenshot(path="method2_click_outside.png")
            
        except Exception as e:
            logger.error(f"Click outside method failed: {e}")
        
        # Method 3: Press Escape key
        logger.info("\n=== Method 3: Press Escape key ===")
        
        try:
            await page.keyboard.press('Escape')
            await page.wait_for_timeout(1000)
            await page.screenshot(path="method3_escape_key.png")
            
        except Exception as e:
            logger.error(f"Escape key method failed: {e}")
        
        # Method 4: Direct interaction with time slots (ignore overlay)
        logger.info("\n=== Method 4: Direct time slot interaction ===")
        
        try:
            # Force click on time slots even if covered
            time_buttons = await page.query_selector_all('button[class*="time"]')
            logger.info(f"Found {len(time_buttons)} time buttons")
            
            if time_buttons:
                # Try force clicking the first time button
                first_button = time_buttons[0]
                button_text = await first_button.text_content()
                logger.info(f"Attempting to force click: {button_text}")
                
                # Use JavaScript click which can bypass overlays
                await page.evaluate('(element) => element.click()', first_button)
                await page.wait_for_timeout(2000)
                await page.screenshot(path="method4_force_click.png")
                logger.info(f"Force clicked button: {button_text}")
                
        except Exception as e:
            logger.error(f"Force click method failed: {e}")
        
        # Method 5: Navigate with direct time URL
        logger.info("\n=== Method 5: Direct time URL navigation ===")
        
        try:
            # Build direct URL to bypass calendar selection
            base_url = "https://clublavilla.as.me/schedule/7d558012/appointment/15970897"
            datetime_url = f"{base_url}/datetime/2025-07-30T11:00:00-06:00?appointmentTypeIds[]=15970897"
            logger.info(f"Navigating to direct datetime URL: {datetime_url}")
            
            await page.goto(datetime_url, wait_until='networkidle')
            await page.wait_for_timeout(2000)
            await page.screenshot(path="method5_direct_url.png")
            logger.info(f"Current URL: {page.url}")
            
            # Check if we're on the form page
            form_fields = await page.query_selector_all('input[type="text"], input[type="email"], input[type="tel"]')
            logger.info(f"Found {len(form_fields)} form fields")
            
            if form_fields:
                logger.info("SUCCESS! Direct URL bypassed the overlay and reached the form!")
                
                # Log form field details
                for field in form_fields:
                    field_name = await field.get_attribute('name')
                    field_placeholder = await field.get_attribute('placeholder')
                    logger.info(f"  Field: name='{field_name}', placeholder='{field_placeholder}'")
                    
        except Exception as e:
            logger.error(f"Direct URL method failed: {e}")
        
        # Check current page state
        logger.info("\n=== Final page state check ===")
        
        # Check for rules text
        rules_visible = await page.query_selector('text="Reglamento del sistema de citas"')
        logger.info(f"Rules overlay visible: {rules_visible is not None}")
        
        # Check for time buttons
        time_buttons = await page.query_selector_all('button[class*="time"]')
        logger.info(f"Time buttons found: {len(time_buttons)}")
        
        # Check for form fields
        form_fields = await page.query_selector_all('input')
        logger.info(f"Input fields found: {len(form_fields)}")
        
        logger.info("\nBrowser will stay open for 30 seconds for manual inspection...")
        await page.wait_for_timeout(30000)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(fix_rules_overlay())
