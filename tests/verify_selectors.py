#!/usr/bin/env python3
"""
Quick test to verify the correct selectors for time buttons
"""

import asyncio
from playwright.async_api import async_playwright

async def test_selectors():
    """Test different selectors to find time buttons"""
    print("Testing time button selectors...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Navigate to Court 3
        url = "https://clublavilla.as.me/schedule/7d558012/appointment/16120442/calendar/4307254?appointmentTypeIds[]=16120442"
        await page.goto(url, wait_until='networkidle')
        await asyncio.sleep(3)  # Wait for dynamic content
        
        # Test selectors
        selectors = [
            'button.time-selection',  # The actual class used
            'button:has(p:text("06:00"))',  # Button containing 06:00
            'button[aria-label*="06:00"]',  # Aria label contains 06:00
            '.css-m4syaq',  # The CSS module class
            'button:has-text("06:00")',  # Playwright's has-text
        ]
        
        print("\nTesting selectors:")
        for selector in selectors:
            try:
                buttons = await page.query_selector_all(selector)
                if buttons:
                    print(f"✅ {selector}: Found {len(buttons)} buttons")
                    # Test clicking the first one
                    if "06:00" in selector:
                        first_text = await buttons[0].text_content()
                        print(f"   First button text: '{first_text}'")
                else:
                    print(f"❌ {selector}: No buttons found")
            except Exception as e:
                print(f"❌ {selector}: Error - {e}")
        
        # Find all time buttons
        time_buttons = await page.query_selector_all('button.time-selection')
        print(f"\nTotal time buttons found: {len(time_buttons)}")
        
        # List all times
        print("\nAvailable times:")
        for button in time_buttons:
            time_text = await button.text_content()
            aria_label = await button.get_attribute('aria-label')
            print(f"  - {time_text.strip()} (aria: {aria_label})")
        
        # Check if 06:00 exists
        six_am_button = await page.query_selector('button:has(p:text("06:00"))')
        if six_am_button:
            print("\n✅ Found 06:00 AM button!")
            print("   Can click it for booking")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_selectors())