"""
Test that the scheduler now runs in the main event loop and bookings work
"""
from utils.tracking import t

import asyncio
import sys
import logging
from datetime import datetime
sys.path.append('/mnt/c/Documents/code/python/lvbot')

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_scheduler_in_main_loop():
    """Test scheduler running in main event loop"""
    t('archive.testing.tests.test_investigations.test_event_loop_fix.test_scheduler_in_main_loop')
    from lvbot.utils.async_browser_pool import AsyncBrowserPool
    from lvbot.utils.reservation_scheduler import ReservationScheduler
    from lvbot.utils.reservation_queue import ReservationQueue
    from lvbot.utils.user_manager import UserManager
    
    browser_pool = None
    
    try:
        print("=== TESTING SCHEDULER IN MAIN EVENT LOOP ===")
        
        # Initialize components
        print("\n1. Initializing browser pool...")
        browser_pool = AsyncBrowserPool()
        await browser_pool.start()
        print("✅ Browser pool initialized")
        
        print("\n2. Initializing reservation system...")
        queue = ReservationQueue()
        user_manager = UserManager()
        
        # Mock notification callback
        async def mock_notification(user_id, message):
            t('archive.testing.tests.test_investigations.test_event_loop_fix.test_scheduler_in_main_loop.mock_notification')
            print(f"[NOTIFICATION] User {user_id}: {message}")
        
        # Create scheduler with required parameters
        class MockConfig:
            timezone = 'America/Mexico_City'
            
        config = MockConfig()
        scheduler = ReservationScheduler(
            config=config,
            queue=queue,
            notification_callback=mock_notification,
            bot_handler=None,
            browser_pool=browser_pool
        )
        print("✅ Reservation system initialized")
        
        print("\n3. Adding test reservation...")
        # Add a test reservation that should execute immediately
        reservation_id = queue.add_reservation({
            'user_id': 125763357,
            'target_date': "2025-07-31",
            'target_time': "09:00",
            'courts': [3],
            'priority': "normal",
            'status': 'scheduled'
        })
        print(f"✅ Test reservation added with ID: {reservation_id}")
        
        print("\n4. Starting scheduler in main event loop...")
        # Create scheduler task
        scheduler_task = asyncio.create_task(scheduler.run_async())
        print("✅ Scheduler task created")
        
        # Let it run for 30 seconds to see if booking executes
        print("\n5. Waiting 30 seconds for booking to execute...")
        await asyncio.sleep(30)
        
        print("\n6. Checking results...")
        # Check queue for results
        pending = queue.get_pending_reservations()
        print(f"Pending reservations: {len(pending)}")
        
        # Check scheduler stats
        print(f"Scheduler stats: {scheduler.stats}")
        
        print("\n7. Stopping scheduler...")
        scheduler.running = False
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            print("✅ Scheduler task cancelled")
        
        print("\nTest complete!")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if browser_pool and hasattr(browser_pool, 'browser') and browser_pool.browser:
            await browser_pool.browser.close()

if __name__ == "__main__":
    asyncio.run(test_scheduler_in_main_loop())