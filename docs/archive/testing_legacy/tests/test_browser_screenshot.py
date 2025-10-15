#!/usr/bin/env python3
"""Take screenshots of browser pool state"""

import asyncio
import logging
from datetime import datetime
from lvbot.utils.async_browser_pool import AsyncBrowserPool

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def take_screenshots():
    """Take screenshots of all court browsers"""
    browser_pool = AsyncBrowserPool()
    
    try:
        # Start the browser pool
        print("Starting browser pool...")
        await browser_pool.start()
        print("Browser pool started successfully!")
        
        # Take screenshots of each court
        for court_num in [1, 2, 3]:
            page = await browser_pool.get_page(court_num)
            if page:
                screenshot_name = f"court_{court_num}_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await page.screenshot(path=screenshot_name)
                print(f"✅ Screenshot saved: {screenshot_name}")
                
                # Get current URL
                current_url = page.url
                print(f"   Court {court_num} URL: {current_url}")
                
                # Check for any visible errors
                try:
                    error_text = await page.locator('.error, .alert-danger, .message-error').text_content()
                    if error_text:
                        print(f"   ⚠️  Error visible: {error_text}")
                except:
                    pass
            else:
                print(f"❌ Court {court_num}: No page available")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser_pool.stop()

if __name__ == "__main__":
    asyncio.run(take_screenshots())