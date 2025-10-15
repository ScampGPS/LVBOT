"""
Test booking in scheduler context to understand the hang
"""

import asyncio
import time
import sys
import logging
import threading
sys.path.append('/mnt/c/Documents/code/python/lvbot')

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(threadName)s] %(message)s'
)

async def simulate_scheduler_booking():
    """Simulate how the scheduler runs bookings"""
    from utils.async_browser_pool import AsyncBrowserPool
    from utils.async_booking_executor import AsyncBookingExecutor
    
    browser_pool = None
    
    try:
        print(f"=== SIMULATING SCHEDULER CONTEXT ===")
        print(f"Main thread: {threading.current_thread().name}")
        print(f"Event loop: {id(asyncio.get_running_loop())}")
        
        # Initialize browser pool (simulating main thread init)
        browser_pool = AsyncBrowserPool()
        await browser_pool.start()
        print(f"Browser pool initialized in thread: {threading.current_thread().name}")
        print(f"Browser pool event loop: {id(asyncio.get_running_loop())}")
        
        # Simulate scheduler creating booking task
        async def execute_single_booking():
            print(f"\nBooking task thread: {threading.current_thread().name}")
            print(f"Booking task event loop: {id(asyncio.get_running_loop())}")
            
            executor = AsyncBookingExecutor(browser_pool, use_natural_flow=False)
            
            result = await executor.execute_booking(
                court_number=3,
                time_slot="09:00",
                user_info={
                    'first_name': 'Test',
                    'last_name': 'User',
                    'email': 'test@example.com',
                    'phone': '12345678'
                },
                target_date=None
            )
            return result
        
        # Create task like scheduler does
        print("\nCreating booking task...")
        booking_task = asyncio.create_task(execute_single_booking())
        
        # Wait with timeout like scheduler
        print("Waiting for task with 60s timeout...")
        done, pending = await asyncio.wait(
            [booking_task],
            return_when=asyncio.ALL_COMPLETED,
            timeout=60.0
        )
        
        if pending:
            print("TIMEOUT! Task didn't complete in 60s")
            booking_task.cancel()
            try:
                await booking_task
            except asyncio.CancelledError:
                print("Task cancelled")
        else:
            result = await booking_task
            print(f"Task completed! Result: {result}")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if browser_pool and hasattr(browser_pool, 'browser') and browser_pool.browser:
            await browser_pool.browser.close()

if __name__ == "__main__":
    asyncio.run(simulate_scheduler_booking())