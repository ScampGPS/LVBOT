#!/usr/bin/env python3
"""
Test a single timing configuration safely
Only books ONE slot for tomorrow
"""
from utils.tracking import t

import asyncio
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

async def test_single_timing(warmup_seconds: float, initial_delay_min: float, initial_delay_max: float):
    """Test a single timing configuration"""
    t('archive.testing.tests.test_single_timing.test_single_timing')
    logger = logging.getLogger('SingleTimingTest')
    
    print("\n" + "="*80)
    print("SINGLE TIMING TEST")
    print(f"Warm-up: {warmup_seconds}s | Initial delay: {initial_delay_min}-{initial_delay_max}s")
    print("="*80)
    print("This will book ONE slot for tomorrow as a test")
    print("="*80 + "\n")
    
    # User info
    user_info = {
        'user_id': 125763357,
        'first_name': 'Saul',
        'last_name': 'Campos',
        'email': 'msaulcampos@gmail.com',
        'phone': '31874277'
    }
    
    # Import modules
    from lvbot.utils.async_browser_pool import AsyncBrowserPool
    from lvbot.utils.async_booking_executor import AsyncBookingExecutor
    
    # Configure timing
    browser_pool = AsyncBrowserPool()
    browser_pool.WARMUP_DELAY = warmup_seconds
    
    # Initialize
    start_time = datetime.now()
    await browser_pool.start()
    
    # Configure executor timing
    executor = AsyncBookingExecutor(browser_pool, use_natural_flow=False)
    from lvbot.utils.working_booking_executor import WorkingBookingExecutor
    WorkingBookingExecutor.INITIAL_DELAY_MIN = initial_delay_min
    WorkingBookingExecutor.INITIAL_DELAY_MAX = initial_delay_max
    
    # Target tomorrow
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow_str = tomorrow.strftime('%Y-%m-%d')
    
    # Use the 12:00 slot on Court 1 (we already booked 10:00 and 11:00)
    target_time = '12:00'
    target_court = 1
    
    print(f"Target booking:")
    print(f"  Date: {tomorrow_str} (tomorrow)")
    print(f"  Time: {target_time}")
    print(f"  Court: {target_court}")
    print("="*80 + "\n")
    
    # SAFETY CHECK
    if tomorrow.date() <= datetime.now().date():
        logger.error("SAFETY: Attempted to book today or past!")
        return
    
    # Execute booking
    try:
        result = await executor.execute_booking(
            court_number=target_court,
            time_slot=target_time,
            user_info=user_info,
            target_date=tomorrow
        )
        
        total_time = (datetime.now() - start_time).total_seconds()
        
        # Check for bot detection
        bot_detected = False
        page = await browser_pool.get_page(target_court)
        if page:
            try:
                error_element = await page.query_selector('p[role="alert"]')
                if error_element:
                    error_text = await error_element.inner_text()
                    if 'irregular' in error_text.lower() or 'detectó' in error_text.lower():
                        bot_detected = True
                        logger.error(f"❌ BOT DETECTED: {error_text}")
            except:
                pass
        
        print("\n" + "="*80)
        print("RESULTS:")
        print(f"Total execution time: {total_time:.1f}s")
        print(f"Bot detected: {'YES 🚨' if bot_detected else 'No ✅'}")
        
        if result.success and not bot_detected:
            print("✅ BOOKING SUCCESSFUL!")
            if result.confirmation_id:
                print(f"Confirmation ID: {result.confirmation_id}")
        else:
            print("❌ BOOKING FAILED!")
            print(f"Reason: {result.error_message}")
        
        print("="*80)
        
    except Exception as e:
        logger.error(f"Test error: {e}")
        import traceback
        traceback.print_exc()
    
    # Keep browsers open briefly
    await asyncio.sleep(5)
    
    # Cleanup
    if hasattr(browser_pool, 'close'):
        await browser_pool.close()

async def main():
    """Run test with specified timing"""
    t('archive.testing.tests.test_single_timing.main')
    import sys
    
    if len(sys.argv) == 4:
        warmup = float(sys.argv[1])
        delay_min = float(sys.argv[2])
        delay_max = float(sys.argv[3])
    else:
        # Default conservative timing
        warmup = 8.0
        delay_min = 2.0
        delay_max = 4.0
        print(f"Using default timing: {warmup}s warmup, {delay_min}-{delay_max}s delay")
        print("Usage: python test_single_timing.py <warmup_seconds> <delay_min> <delay_max>")
    
    await test_single_timing(warmup, delay_min, delay_max)

if __name__ == "__main__":
    asyncio.run(main())