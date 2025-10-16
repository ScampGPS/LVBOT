"""
Investigate why mouse.move is taking so long
"""
from utils.tracking import t

import asyncio
import time
import sys
sys.path.append('/mnt/c/Documents/code/python/lvbot')
from lvbot.utils.async_browser_pool import AsyncBrowserPool

async def test_mouse_move():
    """Test mouse move timing"""
    t('archive.testing.tests.test_investigations.investigate_mouse_move.test_mouse_move')
    browser_pool = None
    
    try:
        print("=== TESTING MOUSE MOVE TIMING ===")
        
        # Initialize browser pool
        browser_pool = AsyncBrowserPool()
        await browser_pool.start()
        
        # Get page
        page = await browser_pool.get_page(3)
        print(f"Got page: {page.url}")
        
        # Test different mouse move operations
        print("\n1. Testing simple mouse.move()...")
        start = time.time()
        await page.mouse.move(400, 300)
        end = time.time()
        print(f"   Simple move took: {end - start:.3f}s")
        
        print("\n2. Testing mouse.move() with steps...")
        start = time.time()
        await page.mouse.move(600, 400, steps=10)
        end = time.time()
        print(f"   Move with 10 steps took: {end - start:.3f}s")
        
        print("\n3. Testing mouse.move() without any steps...")
        start = time.time()
        await page.mouse.move(500, 350, steps=1)
        end = time.time()
        print(f"   Move with 1 step took: {end - start:.3f}s")
        
        print("\n4. Testing multiple quick moves...")
        start = time.time()
        for i in range(5):
            await page.mouse.move(400 + i*20, 300 + i*20)
        end = time.time()
        print(f"   5 moves took: {end - start:.3f}s")
        
        print("\n5. Testing mouse move after page interaction...")
        # First interact with the page
        await page.evaluate("window.scrollTo(0, 100)")
        start = time.time()
        await page.mouse.move(450, 350)
        end = time.time()
        print(f"   Move after scroll took: {end - start:.3f}s")
        
        # Check if page is responsive
        print("\n6. Testing page responsiveness...")
        start = time.time()
        result = await page.evaluate("1 + 1")
        end = time.time()
        print(f"   Page evaluate took: {end - start:.3f}s, result: {result}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if browser_pool and hasattr(browser_pool, 'browser') and browser_pool.browser:
            await browser_pool.browser.close()

if __name__ == "__main__":
    asyncio.run(test_mouse_move())