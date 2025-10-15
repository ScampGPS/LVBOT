#!/usr/bin/env python3
"""
Simple test of availability checking without browser pool warm-up
"""

import asyncio
import logging
from playwright.async_api import async_playwright
from utils.availability_checker_v2 import AvailabilityCheckerV2

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_direct():
    """Test availability checking directly"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        
        try:
            # Test Court 3 directly
            page = await browser.new_page()
            court_url = "https://clublavilla.as.me/?appointmentType=16120442"
            
            logger.info(f"Navigating to Court 3: {court_url}")
            await page.goto(court_url, wait_until='domcontentloaded')
            await asyncio.sleep(2)
            
            # Check URL
            current_url = page.url
            logger.info(f"Current URL: {current_url}")
            
            # Check for time buttons
            buttons = await page.query_selector_all('button.time-selection')
            logger.info(f"Found {len(buttons)} time buttons")
            
            # Extract times
            times = []
            for button in buttons:
                text = await button.text_content()
                if text:
                    times.append(text.strip())
                    
            logger.info(f"Times found: {times}")
            
            # Check for no availability message
            no_avail = await page.query_selector_all('*:has-text("No hay citas disponibles")')
            if no_avail:
                logger.info("No availability message found")
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_direct())