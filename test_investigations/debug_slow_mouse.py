"""
Debug why mouse movement is taking 3.4 seconds instead of 0.7s
"""

import asyncio
import time
import sys
sys.path.append('/mnt/c/Documents/code/python/lvbot')
from utils.async_browser_pool import AsyncBrowserPool
from playwright.async_api import async_playwright

async def test_slow_mouse():
    """Test mouse move timing on different pages"""
    browser_pool = None
    
    try:
        print("=== DEBUGGING SLOW MOUSE MOVEMENT ===")
        
        # Test 1: Browser pool page (the slow one)
        print("\n1. Testing with browser pool page...")
        browser_pool = AsyncBrowserPool()
        await browser_pool.start()
        
        page = await browser_pool.get_page(3)
        print(f"   Page URL: {page.url}")
        
        # Get current mouse position
        mouse_pos = await page.evaluate("() => ({ x: 0, y: 0 })")
        print(f"   Starting position: {mouse_pos}")
        
        # Test move
        start = time.time()
        await page.mouse.move(427, 346)
        end = time.time()
        print(f"   Mouse move took: {end - start:.3f}s")
        
        # Check page state
        print("\n2. Checking page state...")
        
        # Is page responsive?
        start = time.time()
        result = await page.evaluate("2 + 2")
        end = time.time()
        print(f"   Page evaluate took: {end - start:.3f}s, result: {result}")
        
        # Check for heavy elements
        button_count = await page.evaluate("() => document.querySelectorAll('button').length")
        print(f"   Number of buttons on page: {button_count}")
        
        # Check for animations/transitions
        animations = await page.evaluate("""
            () => {
                const styles = window.getComputedStyle(document.body);
                return {
                    transition: styles.transition,
                    animation: styles.animation
                };
            }
        """)
        print(f"   Page animations: {animations}")
        
        # Test 3: Create a fresh page for comparison
        print("\n3. Testing with fresh blank page...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            fresh_page = await browser.new_page()
            await fresh_page.goto("about:blank")
            
            start = time.time()
            await fresh_page.mouse.move(427, 346)
            end = time.time()
            print(f"   Fresh page mouse move took: {end - start:.3f}s")
            
            await browser.close()
        
        # Test 4: Multiple moves on pool page
        print("\n4. Testing multiple moves on pool page...")
        for i in range(3):
            start = time.time()
            await page.mouse.move(400 + i*50, 300 + i*50)
            end = time.time()
            print(f"   Move #{i+1} took: {end - start:.3f}s")
        
        # Test 5: Check CPU/memory
        print("\n5. System resource check...")
        import psutil
        print(f"   CPU usage: {psutil.cpu_percent(interval=1)}%")
        print(f"   Memory usage: {psutil.virtual_memory().percent}%")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if browser_pool and hasattr(browser_pool, 'browser') and browser_pool.browser:
            await browser_pool.browser.close()

if __name__ == "__main__":
    asyncio.run(test_slow_mouse())