#!/usr/bin/env python3
"""
Quick test to check what URLs we're on after direct navigation
"""
from utils.tracking import t

import asyncio
import logging
from lvbot.utils.async_browser_pool import AsyncBrowserPool

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_urls():
    """Check what URLs we're on"""
    t('archive.testing.tests.test_check_urls.test_urls')
    browser_pool = AsyncBrowserPool()
    
    try:
        print("Starting browser pool...")
        await browser_pool.start()
        print("✅ Browser pool started")
        
        # Check URLs for each court
        for court_num in [1, 2, 3]:
            page = browser_pool.pages.get(court_num)
            if page:
                url = page.url
                print(f"\nCourt {court_num} URL: {url}")
                
                # Check if it contains the iframe pattern
                if "squarespacescheduling" in url:
                    print(f"  ✅ Already on Acuity page (no iframe needed)")
                else:
                    print(f"  ⚠️ On wrapper page (needs iframe)")
                    
                # Check for time buttons
                try:
                    buttons = await page.query_selector_all('button.time-selection')
                    print(f"  Found {len(buttons)} time buttons")
                except Exception as e:
                    print(f"  Error checking buttons: {e}")
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nClosing browser pool...")
        await browser_pool.stop()
        print("✅ Test completed")

if __name__ == "__main__":
    asyncio.run(test_urls())