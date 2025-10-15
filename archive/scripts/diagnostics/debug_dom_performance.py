"""
Debug script to investigate DOM query performance issues on Acuity booking page
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

async def test_dom_queries():
    """Test various DOM query methods and measure their performance"""
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(
            headless=False,  # Show browser for visual debugging
            args=['--disable-blink-features=AutomationControlled']
        )
        
        page = await browser.new_page()
        
        # Navigate to the booking page
        url = "https://clublavilla.as.me/schedule/7d558012/appointment/15970897/calendar/4282490?appointmentTypeIds[]=15970897"
        logger.info(f"Navigating to: {url}")
        
        start_nav = time.time()
        await page.goto(url, wait_until='networkidle')
        nav_time = time.time() - start_nav
        logger.info(f"Navigation took: {nav_time:.2f} seconds")
        
        # Wait a bit for any dynamic content
        await page.wait_for_timeout(2000)
        
        # Take screenshot of current state
        await page.screenshot(path="debug_booking_page_state.png")
        logger.info("Screenshot saved: debug_booking_page_state.png")
        
        # Test 1: Original problematic selector
        logger.info("\n=== Test 1: Original multi-selector query ===")
        start = time.time()
        try:
            elements = await page.query_selector_all('h2, h3, div[class*="date"], div[class*="calendar-day"]')
            elapsed = time.time() - start
            logger.info(f"query_selector_all with multiple selectors took: {elapsed:.2f}s")
            logger.info(f"Found {len(elements)} elements")
            
            # Log first few element texts
            for i, elem in enumerate(elements[:5]):
                text = await elem.text_content()
                logger.info(f"Element {i}: {text[:50] if text else 'No text'}")
        except Exception as e:
            logger.error(f"Error with multi-selector: {e}")
        
        # Test 2: Individual selectors
        logger.info("\n=== Test 2: Individual selector queries ===")
        selectors = ['h2', 'h3', 'div[class*="date"]', 'div[class*="calendar-day"]']
        
        for selector in selectors:
            start = time.time()
            try:
                elements = await page.query_selector_all(selector)
                elapsed = time.time() - start
                logger.info(f"'{selector}' took: {elapsed:.2f}s, found {len(elements)} elements")
            except Exception as e:
                logger.error(f"Error with '{selector}': {e}")
        
        # Test 3: Simpler selectors
        logger.info("\n=== Test 3: Simple selector queries ===")
        simple_selectors = ['button', 'div', 'h2', 'h3', 'a']
        
        for selector in simple_selectors:
            start = time.time()
            try:
                elements = await page.query_selector_all(selector)
                elapsed = time.time() - start
                logger.info(f"'{selector}' took: {elapsed:.2f}s, found {len(elements)} elements")
            except Exception as e:
                logger.error(f"Error with '{selector}': {e}")
        
        # Test 4: Check page content
        logger.info("\n=== Test 4: Page content analysis ===")
        
        # Get page title
        title = await page.title()
        logger.info(f"Page title: {title}")
        
        # Get page URL
        current_url = page.url
        logger.info(f"Current URL: {current_url}")
        
        # Check for any blocking or anti-bot measures
        logger.info("\n=== Test 5: Anti-bot detection check ===")
        
        # Check for common anti-bot elements
        anti_bot_selectors = [
            'div[class*="captcha"]',
            'div[class*="challenge"]',
            'div[class*="blocked"]',
            'div[class*="denied"]',
            'iframe[src*="captcha"]',
            'iframe[src*="challenge"]'
        ]
        
        for selector in anti_bot_selectors:
            elements = await page.query_selector_all(selector)
            if elements:
                logger.warning(f"Found potential anti-bot element: {selector} ({len(elements)} found)")
        
        # Test 6: JavaScript execution
        logger.info("\n=== Test 6: JavaScript execution test ===")
        start = time.time()
        try:
            # Simple JS execution
            result = await page.evaluate('() => document.querySelectorAll("h2").length')
            elapsed = time.time() - start
            logger.info(f"JS querySelectorAll('h2') took: {elapsed:.2f}s, found {result} elements")
        except Exception as e:
            logger.error(f"JS execution error: {e}")
        
        # Test 7: Look for actual date headers using JavaScript
        logger.info("\n=== Test 7: Finding date headers with JavaScript ===")
        start = time.time()
        try:
            date_info = await page.evaluate('''() => {
                const elements = [];
                // Look for elements that might contain dates
                const candidates = document.querySelectorAll('h1, h2, h3, h4, h5, h6, div, span');
                const datePattern = /(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\\s+(January|February|March|April|May|June|July|August|September|October|November|December)\\s+\\d{1,2}/i;
                
                for (const el of candidates) {
                    const text = el.textContent || '';
                    if (datePattern.test(text)) {
                        elements.push({
                            tag: el.tagName,
                            class: el.className,
                            text: text.trim().substring(0, 100)
                        });
                    }
                }
                return elements;
            }''')
            elapsed = time.time() - start
            logger.info(f"JS date search took: {elapsed:.2f}s")
            logger.info(f"Found {len(date_info)} date elements:")
            for item in date_info[:5]:
                logger.info(f"  {item['tag']}.{item['class']}: {item['text']}")
        except Exception as e:
            logger.error(f"JS date search error: {e}")
        
        # Test 8: Check for dynamic loading
        logger.info("\n=== Test 8: Dynamic content check ===")
        
        # Wait and check if content changes
        initial_html_length = len(await page.content())
        await page.wait_for_timeout(3000)
        final_html_length = len(await page.content())
        
        if final_html_length != initial_html_length:
            logger.info(f"Page content changed: {initial_html_length} -> {final_html_length} chars")
        else:
            logger.info("Page content appears static")
        
        # Final screenshot
        await page.screenshot(path="debug_booking_page_final.png")
        logger.info("Final screenshot saved: debug_booking_page_final.png")
        
        # Keep browser open for manual inspection
        logger.info("\nBrowser will stay open for 30 seconds for manual inspection...")
        await page.wait_for_timeout(30000)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_dom_queries())
