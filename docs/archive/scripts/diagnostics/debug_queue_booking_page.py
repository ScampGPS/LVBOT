#!/usr/bin/env python3
"""
Debug script to take screenshots of what's actually on the page during queue booking
"""
import pathlib
from pathlib import Path
import sys

ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


import asyncio
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lvbot.utils.async_browser_pool import AsyncBrowserPool
from datetime import datetime
import pytz

async def debug_queue_booking_page():
    """Take screenshots to see what's actually on each court page"""
    browser_pool = None
    
    try:
        print("🚀 Starting browser pool...")
        browser_pool = AsyncBrowserPool()
        await browser_pool.start()
        
        print("✅ Browser pool initialized")
        
        # Get Mexico timezone
        mst = pytz.timezone("America/Denver")
        now = datetime.now(mst)
        
        print(f"\n📅 Current time in Mexico: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"📅 Today is: {now.strftime('%A, %B %d, %Y')}")
        
        # Take screenshots of all 3 courts
        for court_num in [1, 2, 3]:
            print(f"\n🎾 Checking Court {court_num}...")
            
            page = await browser_pool.get_page(court_num)
            if not page:
                print(f"❌ Could not get page for court {court_num}")
                continue
                
            # Take screenshot
            screenshot_path = f"court_{court_num}_page_state.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"📸 Screenshot saved: {screenshot_path}")
            
            # Check what's visible on the page
            print(f"\n📊 Analyzing Court {court_num} page content...")
            
            # Check for day labels
            day_labels = []
            for selector in ['.css-yl3rn6', 'div:has-text("HOY")', 'div:has-text("MAÑANA")', 'div:has-text("ESTA SEMANA")']:
                try:
                    elements = await page.query_selector_all(selector)
                    for elem in elements:
                        text = await elem.text_content()
                        if text and text.strip():
                            day_labels.append(text.strip())
                except:
                    pass
                    
            if day_labels:
                print(f"📅 Day labels found: {day_labels}")
            else:
                print("❌ No day labels found")
                
            # Check for time buttons
            time_buttons = await page.query_selector_all('button.time-selection')
            if time_buttons:
                print(f"⏰ Found {len(time_buttons)} time buttons")
                
                # Get first few time slots
                times = []
                for i, button in enumerate(time_buttons[:5]):
                    try:
                        time_text = await button.text_content()
                        if time_text:
                            times.append(time_text.strip())
                    except:
                        pass
                        
                if times:
                    print(f"⏰ First few times: {times}")
                    
                # Check specifically for 09:00
                nine_am_found = False
                for button in time_buttons:
                    try:
                        time_text = await button.text_content()
                        if time_text and "09:00" in time_text:
                            nine_am_found = True
                            break
                    except:
                        pass
                        
                if nine_am_found:
                    print("✅ 09:00 time slot IS visible on the page")
                else:
                    print("❌ 09:00 time slot NOT found on current page")
                    
            else:
                print("❌ No time buttons found")
                
            # Check current URL
            current_url = page.url
            print(f"🔗 Current URL: {current_url}")
            
            # Check for any error messages
            error_selectors = [
                'text="No hay disponibilidad"',
                'text="No available"',
                '.error-message',
                '.no-availability'
            ]
            
            for selector in error_selectors:
                try:
                    error = await page.query_selector(selector)
                    if error:
                        error_text = await error.text_content()
                        print(f"⚠️ Error message found: {error_text}")
                except:
                    pass
                    
        print("\n✅ Debug complete! Check the screenshots to see actual page state.")
        
    except Exception as e:
        print(f"\n❌ Error during debug: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if browser_pool:
            print("\n🧹 Closing browser pool...")
            await browser_pool.stop()

if __name__ == "__main__":
    asyncio.run(debug_queue_booking_page())
