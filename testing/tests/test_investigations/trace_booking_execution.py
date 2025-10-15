"""
Trace the exact execution path during booking to find where it's getting stuck
"""

import asyncio
import logging
import time
from datetime import datetime
from lvbot.utils.async_booking_executor import AsyncBookingExecutor
from lvbot.utils.async_browser_pool import AsyncBrowserPool

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def trace_booking_execution():
    """Trace exactly where the booking is getting stuck"""
    
    browser_pool = None
    start_time = time.time()
    
    try:
        print("=== STARTING BOOKING EXECUTION TRACE ===")
        
        # Initialize browser pool
        print(f"[{time.time() - start_time:.1f}s] Initializing browser pool...")
        browser_pool = AsyncBrowserPool(headless=False)
        await browser_pool.start()
        print(f"[{time.time() - start_time:.1f}s] Browser pool initialized")
        
        # Create executor
        print(f"[{time.time() - start_time:.1f}s] Creating AsyncBookingExecutor...")
        executor = AsyncBookingExecutor(browser_pool)
        print(f"[{time.time() - start_time:.1f}s] Executor created")
        
        # Test user info
        user_info = {
            'first_name': 'Saul',
            'last_name': 'Campos',
            'phone': '12345678',
            'email': 'saul@example.com'
        }
        
        # Try booking
        print(f"[{time.time() - start_time:.1f}s] Calling executor.execute_booking...")
        print(f"  Court: 3")
        print(f"  Date: 2025-07-31")
        print(f"  Time: 09:00")
        print(f"  Method: traditional")
        
        # Add more detailed logging around the executor call
        print(f"[{time.time() - start_time:.1f}s] About to await execute_booking...")
        
        # Create a task so we can monitor it
        booking_task = asyncio.create_task(
            executor.execute_booking(
                target_courts=[3],
                target_date=datetime(2025, 7, 31),
                time_slot="09:00",
                user_info=user_info,
                method='traditional'
            )
        )
        
        # Monitor the task with periodic checks
        check_interval = 2.0
        max_checks = 30  # 60 seconds total
        
        for i in range(max_checks):
            if booking_task.done():
                print(f"[{time.time() - start_time:.1f}s] Task completed!")
                result = await booking_task
                print(f"Result: {result}")
                break
            else:
                print(f"[{time.time() - start_time:.1f}s] Task still running... (check {i+1}/{max_checks})")
                await asyncio.sleep(check_interval)
        else:
            print(f"[{time.time() - start_time:.1f}s] Task still running after 60s - cancelling...")
            booking_task.cancel()
            try:
                await booking_task
            except asyncio.CancelledError:
                print("Task cancelled")
        
        print(f"[{time.time() - start_time:.1f}s] Execution trace complete")
        
    except Exception as e:
        print(f"[{time.time() - start_time:.1f}s] ERROR: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if browser_pool:
            print(f"[{time.time() - start_time:.1f}s] Closing browser pool...")
            await browser_pool.close()
            print(f"[{time.time() - start_time:.1f}s] Browser pool closed")

if __name__ == "__main__":
    asyncio.run(trace_booking_execution())