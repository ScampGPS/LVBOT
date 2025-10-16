#!/usr/bin/env python3
"""
Test the optimized timing configurations
Compares original vs optimized phase timings
"""
from utils.tracking import t

import asyncio
import logging
import time
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

async def test_optimized_timing():
    """Test optimized timing configuration"""
    t('archive.testing.tests.test_optimized_timing.test_optimized_timing')
    logger = logging.getLogger('OptimizedTimingTest')
    
    print("\n" + "="*80)
    print("OPTIMIZED TIMING TEST")
    print("="*80)
    print("Testing phase-optimized timings:")
    print("- Mouse movements: Reduced from 5s to ~2s")
    print("- Button approach: Reduced from 3.6s to ~1s")
    print("- After-click delay: Reduced from 5s to ~3s")
    print("- Confirmation wait: Reduced from 5s to ~3s")
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
    from lvbot.utils.court_availability import CourtAvailability
    
    # Initialize browser pool with proven timing
    browser_pool = AsyncBrowserPool()
    browser_pool.WARMUP_DELAY = 4.0  # Keep proven warmup
    
    await browser_pool.start()
    
    # Find available slots for tomorrow
    availability = CourtAvailability()
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow_str = tomorrow.strftime('%Y-%m-%d')
    
    print(f"Finding available slots for tomorrow ({tomorrow_str})...")
    available_slots = []
    
    # Check courts for availability
    for court_number in [1, 2, 3]:
        try:
            page = await browser_pool.get_page(court_number)
            if page and await availability.is_acuity_scheduling_page(page):
                times_by_day = await availability.extract_acuity_times_by_day(page)
                
                if tomorrow_str in times_by_day:
                    for time_slot in times_by_day[tomorrow_str]:
                        # Skip slots we've already booked
                        if time_slot not in ['10:00', '11:00', '12:00']:
                            available_slots.append({
                                'court': court_number,
                                'time': time_slot,
                                'date': tomorrow
                            })
        except Exception as e:
            logger.warning(f"Error checking court {court_number}: {e}")
    
    if not available_slots:
        print("No available slots found for tomorrow!")
        await browser_pool.close()
        return
    
    print(f"Found {len(available_slots)} available slots")
    
    # Use first available slot
    slot = available_slots[0]
    print(f"\nTesting with: Court {slot['court']} at {slot['time']} on {slot['date'].strftime('%Y-%m-%d')}")
    print("="*80 + "\n")
    
    # Track phase times
    phase_times = {}
    
    # Initialize executor
    executor = AsyncBookingExecutor(browser_pool, use_natural_flow=False)
    
    # Execute booking with timing
    start_time = time.time()
    
    try:
        result = await executor.execute_booking(
            court_number=slot['court'],
            time_slot=slot['time'],
            user_info=user_info,
            target_date=slot['date']
        )
        
        total_time = time.time() - start_time
        
        # Check for bot detection
        bot_detected = False
        page = await browser_pool.get_page(slot['court'])
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
        
        # Display results
        print("\n" + "="*80)
        print("OPTIMIZED TIMING RESULTS:")
        print("="*80)
        print(f"Total execution time: {total_time:.1f}s")
        print(f"Bot detected: {'YES 🚨' if bot_detected else 'No ✅'}")
        
        if result.success and not bot_detected:
            print("✅ BOOKING SUCCESSFUL WITH OPTIMIZED TIMING!")
            if result.confirmation_id:
                print(f"Confirmation ID: {result.confirmation_id}")
            
            # Compare with typical timing
            typical_time = 57.4  # From our previous successful test
            speedup = ((typical_time - total_time) / typical_time) * 100
            time_saved = typical_time - total_time
            
            print(f"\n🚀 PERFORMANCE IMPROVEMENT:")
            print(f"   Previous: {typical_time:.1f}s")
            print(f"   Optimized: {total_time:.1f}s")
            print(f"   Time saved: {time_saved:.1f}s ({speedup:.1f}% faster)")
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
    await browser_pool.close()

async def main():
    """Run the optimized timing test"""
    t('archive.testing.tests.test_optimized_timing.main')
    await test_optimized_timing()

if __name__ == "__main__":
    asyncio.run(main())