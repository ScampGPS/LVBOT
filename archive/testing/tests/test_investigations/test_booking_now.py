"""
Test immediate booking execution with the event loop fix
"""
from utils.tracking import t

import asyncio
import sys
import logging
from datetime import datetime, timedelta
import pytz
sys.path.append('/mnt/c/Documents/code/python/lvbot')

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_immediate_booking():
    """Test booking execution in main event loop"""
    t('archive.testing.tests.test_investigations.test_booking_now.test_immediate_booking')
    from lvbot.utils.async_browser_pool import AsyncBrowserPool
    from lvbot.utils.reservation_scheduler import ReservationScheduler
    from lvbot.utils.reservation_queue import ReservationQueue
    from lvbot.utils.user_manager import UserManager
    
    browser_pool = None
    
    try:
        print("=== TESTING IMMEDIATE BOOKING WITH EVENT LOOP FIX ===")
        
        # Clear the queue first
        print("\n1. Clearing reservation queue...")
        with open('queue.json', 'w') as f:
            f.write('[]')
        print("✅ Queue cleared")
        
        # Initialize components
        print("\n2. Initializing browser pool...")
        browser_pool = AsyncBrowserPool()
        await browser_pool.start()
        print("✅ Browser pool initialized")
        
        print("\n3. Initializing reservation system...")
        queue = ReservationQueue()
        user_manager = UserManager()
        
        # Mock notification callback
        async def mock_notification(user_id, message):
            t('archive.testing.tests.test_investigations.test_booking_now.test_immediate_booking.mock_notification')
            print(f"\n[NOTIFICATION] User {user_id}: {message}")
        
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
        
        print("\n4. Adding test reservation for immediate execution...")
        # Add a reservation scheduled for "now" (within the window)
        mexico_tz = pytz.timezone('America/Mexico_City')
        now = datetime.now(mexico_tz)
        
        # Set execution time to 5 seconds from now
        execution_time = now + timedelta(seconds=5)
        
        reservation_data = {
            'user_id': 125763357,
            'target_date': "2025-07-31",
            'target_time': "09:00",
            'courts': [3],
            'priority': "REGULAR",
            'status': 'scheduled',
            'scheduled_execution': execution_time.isoformat()
        }
        
        reservation_id = queue.add_reservation(reservation_data)
        print(f"✅ Test reservation added with ID: {reservation_id}")
        print(f"   Scheduled for: {execution_time.strftime('%H:%M:%S')} (in 5 seconds)")
        
        print("\n5. Starting scheduler in main event loop...")
        # Create scheduler task
        scheduler_task = asyncio.create_task(scheduler.run_async())
        print("✅ Scheduler task created")
        
        # Wait for booking to execute
        print("\n6. Waiting 30 seconds for booking to execute...")
        await asyncio.sleep(30)
        
        print("\n7. Checking results...")
        # Check queue for results
        all_reservations = queue.queue
        for res in all_reservations:
            print(f"   Reservation {res['id'][:8]}... - Status: {res['status']}")
            if 'error' in res:
                print(f"   Error: {res['error']}")
        
        # Check scheduler stats
        print(f"\nScheduler stats: {scheduler.stats}")
        
        print("\n8. Stopping scheduler...")
        scheduler.running = False
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            print("✅ Scheduler task cancelled")
        
        print("\n✅ Test complete!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if browser_pool and hasattr(browser_pool, 'browser') and browser_pool.browser:
            print("\nClosing browser pool...")
            await browser_pool.browser.close()

if __name__ == "__main__":
    asyncio.run(test_immediate_booking())