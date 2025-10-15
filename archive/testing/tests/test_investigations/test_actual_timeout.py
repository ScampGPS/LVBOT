"""
Test if the code is actually stuck vs just slow
"""

import asyncio
import time
import sys
import logging
sys.path.append('/mnt/c/Documents/code/python/lvbot')

# Set up logging to match the bot
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_timeout_scenario():
    """Reproduce the exact timeout scenario"""
    from lvbot.utils.async_browser_pool import AsyncBrowserPool
    from lvbot.utils.experienced_booking_executor import ExperiencedBookingExecutor
    
    browser_pool = None
    
    try:
        print("=== REPRODUCING TIMEOUT SCENARIO ===")
        
        # Initialize browser pool like the bot does
        browser_pool = AsyncBrowserPool()
        await browser_pool.start()
        
        # Create executor
        executor = ExperiencedBookingExecutor(browser_pool)
        
        # Test user info (same as in the failed booking)
        user_info = {
            'first_name': 'Saul',
            'last_name': 'Campos',
            'phone': '12345678',
            'email': 'saul@example.com'
        }
        
        # Create the booking task with timeout
        print("\nStarting booking task with 60s timeout...")
        start_time = time.time()
        
        try:
            result = await asyncio.wait_for(
                executor.execute_booking(
                    court_number=3,
                    target_date=None,  # Not used in the code
                    time_slot="09:00",
                    user_info=user_info
                ),
                timeout=60.0
            )
            print(f"Booking completed in {time.time() - start_time:.1f}s")
            print(f"Result: {result}")
            
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            print(f"\nTIMEOUT after {elapsed:.1f}s!")
            print("The booking is stuck somewhere...")
            
            # Check what logs we got
            print("\nChecking last log entries...")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if browser_pool and hasattr(browser_pool, 'browser') and browser_pool.browser:
            await browser_pool.browser.close()

if __name__ == "__main__":
    asyncio.run(test_timeout_scenario())