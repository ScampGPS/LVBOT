#!/usr/bin/env python3
"""
Test reduced initial delay and pre-submit review times
Find the minimum safe values for these delays
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

async def test_with_reduced_delays(initial_delay_min: float, initial_delay_max: float, pre_submit_delay: float) -> Tuple[bool, float, bool, str]:
    """Test booking with reduced delays"""
    logger = logging.getLogger('ReducedDelayTest')
    
    print(f"\n{'='*60}")
    print(f"Testing: Initial {initial_delay_min}-{initial_delay_max}s, Pre-submit {pre_submit_delay}s")
    print(f"{'='*60}")
    
    # Temporarily modify the working executor delays
    import utils.working_booking_executor as executor_module
    
    # Store original values
    original_init_min = getattr(executor_module.WorkingBookingExecutor, 'INITIAL_DELAY_MIN', 3.0)
    original_init_max = getattr(executor_module.WorkingBookingExecutor, 'INITIAL_DELAY_MAX', 5.0)
    
    # Set new values
    executor_module.WorkingBookingExecutor.INITIAL_DELAY_MIN = initial_delay_min
    executor_module.WorkingBookingExecutor.INITIAL_DELAY_MAX = initial_delay_max
    
    # Also need to modify the pre-submit review delay in the code
    import shutil
    original_file = '/mnt/c/Documents/code/python/lvbot/utils/working_booking_executor.py'
    backup_file = original_file + '.backup_delays'
    
    # Backup original
    shutil.copy2(original_file, backup_file)
    
    try:
        # Read and modify the file
        with open(original_file, 'r') as f:
            content = f.read()
        
        # Replace pre-submit review delay
        modified_content = content.replace(
            "await asyncio.sleep(apply_speed(random.uniform(0.5, 1.0)))",
            f"await asyncio.sleep(apply_speed({pre_submit_delay}))"
        )
        
        with open(original_file, 'w') as f:
            f.write(modified_content)
        
        # Now run the test
        from utils.async_browser_pool import AsyncBrowserPool
        from utils.async_booking_executor import AsyncBookingExecutor
        from utils.court_availability import CourtAvailability
        
        user_info = {
            'user_id': 125763357,
            'first_name': 'Saul',
            'last_name': 'Campos',
            'email': 'msaulcampos@gmail.com',
            'phone': '31874277'
        }
        
        # Initialize browser pool
        browser_pool = AsyncBrowserPool()
        browser_pool.WARMUP_DELAY = 4.0  # Keep proven warmup
        await browser_pool.start()
        
        # Find available slots
        availability = CourtAvailability()
        tomorrow = datetime.now() + timedelta(days=1)
        tomorrow_str = tomorrow.strftime('%Y-%m-%d')
        
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
            except:
                pass
        
        if not available_slots:
            return False, 0, False, "No slots available"
        
        # Use first available slot
        slot = available_slots[0]
        logger.info(f"Using slot: Court {slot['court']} at {slot['time']}")
        
        # Execute booking
        executor = AsyncBookingExecutor(browser_pool, use_natural_flow=False)
        
        start_time = time.time()
        result = await executor.execute_booking(
            court_number=slot['court'],
            time_slot=slot['time'],
            user_info=user_info,
            target_date=slot['date']
        )
        execution_time = time.time() - start_time
        
        # Check for bot detection
        bot_detected = False
        error_msg = ""
        page = await browser_pool.get_page(slot['court'])
        if page:
            try:
                # Take screenshot
                screenshot_name = f"delay_test_{initial_delay_min}_{pre_submit_delay}.png"
                await page.screenshot(path=f'/mnt/c/Documents/code/python/lvbot/{screenshot_name}')
                
                # Check for errors
                error_element = await page.query_selector('p[role="alert"]')
                if error_element:
                    error_text = await error_element.inner_text()
                    if 'irregular' in error_text.lower() or 'detectó' in error_text.lower():
                        bot_detected = True
                        error_msg = error_text
                
                # Check page content
                if not bot_detected:
                    page_text = await page.inner_text('body')
                    if 'irregular' in page_text.lower():
                        bot_detected = True
                        error_msg = "Bot detection in page"
            except Exception as e:
                logger.warning(f"Error checking detection: {e}")
        
        # Cleanup
        await asyncio.sleep(2)  # Brief wait
        
        return result.success and not bot_detected, execution_time, bot_detected, error_msg
        
    finally:
        # Restore original file and values
        shutil.copy2(backup_file, original_file)
        import os
        os.remove(backup_file)
        
        executor_module.WorkingBookingExecutor.INITIAL_DELAY_MIN = original_init_min
        executor_module.WorkingBookingExecutor.INITIAL_DELAY_MAX = original_init_max

async def main():
    """Test progressively reduced delays"""
    
    print("\n" + "="*80)
    print("DELAY REDUCTION TEST")
    print("="*80)
    print("Testing reduced initial and pre-submit delays")
    print("Current: Initial 3-5s, Pre-submit 0.5-1.0s")
    print("="*80)
    
    # Test configurations: (initial_min, initial_max, pre_submit)
    test_configs = [
        # Start conservative
        (2.0, 3.0, 0.5, "Conservative reduction"),
        (1.5, 2.0, 0.5, "Target: 1.5s initial"),
        (1.5, 1.5, 0.3, "Fixed 1.5s + reduced pre-submit"),
        (1.0, 1.5, 0.3, "Aggressive: 1-1.5s initial"),
        (0.8, 1.2, 0.2, "Very aggressive: <1s initial"),
        (0.5, 1.0, 0.2, "Extreme: 0.5-1s initial"),
    ]
    
    results = []
    
    for initial_min, initial_max, pre_submit, name in test_configs:
        print(f"\n{name}")
        
        success, exec_time, bot_detected, error = await test_with_reduced_delays(
            initial_min, initial_max, pre_submit
        )
        
        results.append({
            'config': f"{initial_min}-{initial_max}s/{pre_submit}s",
            'name': name,
            'success': success,
            'time': exec_time,
            'bot_detected': bot_detected,
            'error': error
        })
        
        print(f"Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
        print(f"Execution time: {exec_time:.1f}s")
        if bot_detected:
            print(f"⚠️  Bot detected: {error}")
            break
        
        # Wait between tests
        print("Waiting 15s...")
        await asyncio.sleep(15)
    
    # Summary
    print("\n" + "="*80)
    print("DELAY TEST SUMMARY")
    print("="*80)
    print(f"{'Config':<15} {'Name':<30} {'Success':<10} {'Time':<10} {'Bot?':<10}")
    print("-"*80)
    
    safe_config = None
    fastest_time = float('inf')
    
    for r in results:
        success = "✅" if r['success'] else "❌"
        bot = "YES" if r['bot_detected'] else "NO"
        print(f"{r['config']:<15} {r['name']:<30} {success:<10} {r['time']:<10.1f} {bot:<10}")
        
        if r['success'] and not r['bot_detected'] and r['time'] < fastest_time:
            safe_config = r
            fastest_time = r['time']
    
    print("="*80)
    
    if safe_config:
        print(f"\n🎯 OPTIMAL CONFIGURATION:")
        print(f"   Config: {safe_config['config']}")
        print(f"   Name: {safe_config['name']}")
        print(f"   Time: {safe_config['time']:.1f}s")
        
        # Compare to baseline
        baseline = 40.2
        improvement = baseline - safe_config['time']
        print(f"\n📊 IMPROVEMENT:")
        print(f"   Baseline: {baseline:.1f}s")
        print(f"   Optimized: {safe_config['time']:.1f}s")
        print(f"   Saved: {improvement:.1f}s ({improvement/baseline*100:.1f}%)")

if __name__ == "__main__":
    asyncio.run(main())