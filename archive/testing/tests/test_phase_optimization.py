#!/usr/bin/env python3
"""
Test the phase-optimized booking executor
Compares current timing vs optimized phase timing
"""
from tracking import t

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

async def test_phase_optimization():
    """Test optimized phase timings"""
    t('archive.testing.tests.test_phase_optimization.test_phase_optimization')
    logger = logging.getLogger('PhaseOptimizationTest')
    
    print("\n" + "="*80)
    print("PHASE OPTIMIZATION TEST")
    print("="*80)
    print("Testing phase-optimized executor vs current working executor")
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
    from archive.legacy_modules.browser_cleanup.optimized_booking_executor import OptimizedBookingExecutor
    from lvbot.utils.court_availability import CourtAvailability
    
    # Initialize browser pool with optimized settings
    browser_pool = AsyncBrowserPool()
    browser_pool.WARMUP_DELAY = 4.0  # Keep the proven 4s warmup
    
    await browser_pool.start()
    
    # Find available slots for tomorrow
    availability = CourtAvailability()
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow_str = tomorrow.strftime('%Y-%m-%d')
    
    print(f"Finding available slots for tomorrow ({tomorrow_str})...")
    available_slots = []
    
    for court_number in [1, 2, 3]:
        try:
            page = await browser_pool.get_page(court_number)
            if page and await availability.is_acuity_scheduling_page(page):
                times_by_day = await availability.extract_acuity_times_by_day(page)
                
                if tomorrow_str in times_by_day:
                    for time_slot in times_by_day[tomorrow_str]:
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
    
    # Test with first available slot
    slot = available_slots[0]
    print(f"\nTesting with: Court {slot['court']} at {slot['time']} on {slot['date'].strftime('%Y-%m-%d')}")
    print("="*80 + "\n")
    
    # Create optimized executor
    optimized_executor = OptimizedBookingExecutor(browser_pool)
    
    # Execute booking with phase tracking
    start_time = time.time()
    
    try:
        result = await optimized_executor.execute_booking(
            court_number=slot['court'],
            target_date=slot['date'],
            time_slot=slot['time'],
            user_info=user_info
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
        print("PHASE TIMING BREAKDOWN:")
        print("="*80)
        
        if result.phase_times:
            print(f"{'Phase':<25} {'Duration (s)':<15} {'% of Total':<15}")
            print("-"*80)
            
            phase_total = 0
            for phase, duration in sorted(result.phase_times.items()):
                percentage = (duration / total_time) * 100
                print(f"{phase:<25} {duration:>8.2f}s      {percentage:>6.1f}%")
                phase_total += duration
            
            print("-"*80)
            print(f"{'Phase Total':<25} {phase_total:>8.2f}s")
            print(f"{'Total Execution':<25} {total_time:>8.2f}s")
        
        print("\n" + "="*80)
        print("BOOKING RESULT:")
        print(f"Success: {'✅ YES' if result.success and not bot_detected else '❌ NO'}")
        print(f"Bot Detected: {'🚨 YES' if bot_detected else '✅ NO'}")
        print(f"Total Time: {total_time:.1f}s")
        
        if result.success and not bot_detected:
            print(f"Confirmation ID: {result.confirmation_id}")
            
            # Compare with typical timing
            typical_time = 61.0  # From analyze_booking_phases.py
            speedup = ((typical_time - total_time) / typical_time) * 100
            print(f"\n🚀 PERFORMANCE IMPROVEMENT: {speedup:.1f}% faster than typical booking!")
            print(f"   Typical: ~{typical_time:.0f}s → Optimized: {total_time:.1f}s")
        
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
    """Run the phase optimization test"""
    t('archive.testing.tests.test_phase_optimization.main')
    await test_phase_optimization()

if __name__ == "__main__":
    asyncio.run(main())
