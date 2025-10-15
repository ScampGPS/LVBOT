#!/usr/bin/env python3
"""
Test email typing speed limits to find the threshold for bot detection
Tests progressively faster speeds until detection occurs
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import random

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

async def test_email_speed(speed_multiplier: float) -> Tuple[bool, float, bool]:
    """
    Test a specific email typing speed
    Returns: (success, execution_time, bot_detected)
    """
    logger = logging.getLogger('EmailSpeedTest')
    
    # User info
    user_info = {
        'user_id': 125763357,
        'first_name': 'Saul',
        'last_name': 'Campos',
        'email': 'msaulcampos@gmail.com',
        'phone': '31874277'
    }
    
    # Import modules
    from utils.async_browser_pool import AsyncBrowserPool
    from utils.async_booking_executor import AsyncBookingExecutor
    from utils.working_booking_executor import WorkingBookingExecutor
    from utils.court_availability import CourtAvailability
    
    # Temporarily override the typing function with custom speed
    original_human_type = WorkingBookingExecutor.__dict__['_WorkingBookingExecutor__module__'].__dict__['human_type_with_mistakes']
    
    async def fast_email_type(element, text, mistake_prob=0.10):
        """Custom typing function with configurable speed for email only"""
        await element.click()
        await asyncio.sleep(max(0.1, random.uniform(0.3, 0.8) / speed_multiplier))
        await element.fill('')  # Clear field
        await asyncio.sleep(max(0.1, random.uniform(0.2, 0.5) / speed_multiplier))
        
        # Type with adjusted speed
        for i, char in enumerate(text):
            # Reduce mistakes at higher speeds
            adjusted_mistake_prob = mistake_prob / max(1, speed_multiplier * 0.5)
            
            if random.random() < adjusted_mistake_prob and i > 0:
                # Type wrong character first
                wrong_chars = 'abcdefghijklmnopqrstuvwxyz'
                wrong_char = random.choice(wrong_chars)
                if wrong_char != char.lower():
                    base_delay = random.randint(80, 180) / speed_multiplier
                    await element.type(wrong_char, delay=max(15, int(base_delay)))
                    await asyncio.sleep(max(0.05, random.uniform(0.1, 0.4) / speed_multiplier))
                    
                    # Realize mistake and backspace
                    await element.press('Backspace')
                    await asyncio.sleep(max(0.05, random.uniform(0.2, 0.6) / speed_multiplier))
            
            # Type correct character with FASTER speed
            base_delay = random.randint(90, 220) / speed_multiplier
            await element.type(char, delay=max(10, int(base_delay)))
            
            # Reduce thinking pauses at higher speeds
            if random.random() < (0.2 / speed_multiplier):
                await asyncio.sleep(max(0.1, random.uniform(0.3, 1.2) / speed_multiplier))
    
    try:
        # Initialize browser pool
        browser_pool = AsyncBrowserPool()
        browser_pool.WARMUP_DELAY = 4.0
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
                            # Skip already booked slots
                            if time_slot not in ['10:00', '11:00', '12:00', '20:15']:
                                available_slots.append({
                                    'court': court_number,
                                    'time': time_slot,
                                    'date': tomorrow
                                })
            except:
                pass
        
        if not available_slots:
            logger.error("No available slots")
            await browser_pool.close()
            return False, 0, False
        
        slot = available_slots[0]
        
        # Patch the email typing specifically
        class PatchedExecutor(WorkingBookingExecutor):
            async def _execute_booking_internal(self, page, court_number, target_date, time_slot, user_info_param):
                # Store original method
                original_method = super()._execute_booking_internal
                
                # Call original but intercept email field
                result = await original_method(page, court_number, target_date, time_slot, user_info_param)
                return result
        
        # Monkey patch the specific email typing
        import utils.working_booking_executor as executor_module
        original_func = executor_module.human_type_with_mistakes
        
        async def patched_human_type(element, text, mistake_prob=0.10):
            # Check if this is the email field by the text content
            if '@' in text and '.com' in text:
                logger.info(f"Using {speed_multiplier}x speed for email field")
                await fast_email_type(element, text, mistake_prob)
            else:
                # Use normal speed for other fields
                await original_func(element, text, mistake_prob)
        
        executor_module.human_type_with_mistakes = patched_human_type
        
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
        page = await browser_pool.get_page(slot['court'])
        if page:
            try:
                # Check for anti-bot message
                error_element = await page.query_selector('p[role="alert"]')
                if error_element:
                    error_text = await error_element.inner_text()
                    if 'irregular' in error_text.lower() or 'detectó' in error_text.lower():
                        bot_detected = True
                        logger.error(f"BOT DETECTED: {error_text}")
                
                # Also check page content
                page_text = await page.inner_text('body')
                if 'irregular' in page_text.lower() and not bot_detected:
                    bot_detected = True
            except:
                pass
        
        # Restore original function
        executor_module.human_type_with_mistakes = original_func
        
        # Cleanup
        await browser_pool.close()
        
        return result.success and not bot_detected, execution_time, bot_detected
        
    except Exception as e:
        logger.error(f"Test error: {e}")
        return False, 0, False

async def run_speed_limit_tests():
    """Run progressive speed tests to find the limit"""
    logger = logging.getLogger('SpeedLimitTest')
    
    print("\n" + "="*80)
    print("EMAIL TYPING SPEED LIMIT TEST")
    print("="*80)
    print("Testing progressively faster email typing speeds")
    print("Current baseline: 2.5x (safe)")
    print("="*80 + "\n")
    
    # Test configurations (speed multiplier, name)
    test_speeds = [
        (2.5, "Baseline (current)"),
        (3.0, "Moderate increase"),
        (3.5, "Faster"),
        (4.0, "Fast"),
        (5.0, "Very fast"),
        (7.0, "Extreme"),
        (10.0, "Ultra extreme")
    ]
    
    results = []
    
    for speed, name in test_speeds:
        print(f"\n{'='*60}")
        print(f"Testing {name}: {speed}x speed")
        print(f"{'='*60}")
        
        success, exec_time, bot_detected = await test_email_speed(speed)
        
        results.append({
            'speed': speed,
            'name': name,
            'success': success,
            'execution_time': exec_time,
            'bot_detected': bot_detected
        })
        
        print(f"\nResult: {'✅ SUCCESS' if success else '❌ FAILED'}")
        print(f"Bot detected: {'🚨 YES' if bot_detected else '✅ NO'}")
        print(f"Execution time: {exec_time:.1f}s")
        
        # Stop if bot detected
        if bot_detected:
            print("\n⚠️  Bot detection triggered! Stopping tests.")
            break
        
        # Wait between tests
        await asyncio.sleep(10)
    
    # Display summary
    print("\n" + "="*80)
    print("EMAIL SPEED TEST SUMMARY")
    print("="*80)
    print(f"{'Speed':<10} {'Name':<25} {'Success':<10} {'Bot Detected':<15} {'Time (s)':<10}")
    print("-"*80)
    
    safe_speed = 2.5
    for result in results:
        status = "✅" if result['success'] else "❌"
        bot = "🚨 YES" if result['bot_detected'] else "NO"
        time_str = f"{result['execution_time']:.1f}" if result['execution_time'] > 0 else "N/A"
        
        print(f"{result['speed']:<10} {result['name']:<25} {status:<10} {bot:<15} {time_str:<10}")
        
        if result['success'] and not result['bot_detected']:
            safe_speed = result['speed']
    
    print("="*80)
    print(f"\n🎯 MAXIMUM SAFE EMAIL SPEED: {safe_speed}x")
    
    # Calculate time savings
    if safe_speed > 2.5:
        # Email takes ~10.4s at 2.5x speed
        original_email_time = 10.4
        new_email_time = original_email_time * (2.5 / safe_speed)
        time_saved = original_email_time - new_email_time
        
        print(f"\n📊 POTENTIAL TIME SAVINGS:")
        print(f"   Current email time (2.5x): {original_email_time:.1f}s")
        print(f"   Optimized email time ({safe_speed}x): {new_email_time:.1f}s")
        print(f"   Time saved: {time_saved:.1f}s")
        print(f"   Total booking time: ~{40.2 - time_saved:.1f}s (from 40.2s)")

async def main():
    """Run the email speed limit tests"""
    await run_speed_limit_tests()

if __name__ == "__main__":
    asyncio.run(main())