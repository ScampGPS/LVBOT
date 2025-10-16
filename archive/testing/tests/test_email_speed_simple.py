#!/usr/bin/env python3
"""
Simple test for email typing speed limits
Modifies the working executor directly for each test
"""
from tracking import t

import asyncio
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
import random
import shutil

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

async def test_with_email_speed(email_speed_multiplier: float):
    """Test booking with specific email typing speed"""
    t('archive.testing.tests.test_email_speed_simple.test_with_email_speed')
    logger = logging.getLogger('EmailSpeedTest')
    
    print(f"\n{'='*60}")
    print(f"Testing email typing at {email_speed_multiplier}x speed")
    print(f"{'='*60}")
    
    # Create a temporary modified version of working_booking_executor
    repo_root = Path(__file__).resolve().parents[3]
    original_file = repo_root / 'automation' / 'executors' / 'booking.py'
    backup_file = original_file.with_suffix(original_file.suffix + '.backup')
    
    # Backup original file
    shutil.copy2(original_file, backup_file)
    
    try:
        # Read the original file
        with open(original_file, 'r') as f:
            content = f.read()
        
        # Create modified version with custom email speed
        modified_content = content.replace(
            "await _working_human_type_with_mistakes(email_field, email)",
            f"""# TESTING: Using {email_speed_multiplier}x speed for email\n        original_speed = SPEED_MULTIPLIER\n        import automation.executors.booking as booking_module\n        booking_module.SPEED_MULTIPLIER = {email_speed_multiplier}\n        await _working_human_type_with_mistakes(email_field, email)\n        booking_module.SPEED_MULTIPLIER = original_speed"""
        )
        
        # Write modified version
        with open(original_file, 'w') as f:
            f.write(modified_content)
        
        # User info
        user_info = {
            'user_id': 125763357,
            'first_name': 'Saul',
            'last_name': 'Campos',
            'email': 'msaulcampos@gmail.com',
            'phone': '31874277'
        }
        
        # Import modules (will use modified version)
        from lvbot.utils.async_browser_pool import AsyncBrowserPool
        from lvbot.utils.async_booking_executor import AsyncBookingExecutor
        from lvbot.utils.court_availability import CourtAvailability
        
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
                            available_slots.append({
                                'court': court_number,
                                'time': time_slot,
                                'date': tomorrow
                            })
            except:
                pass
        
        if not available_slots:
            logger.error("No available slots")
            return False, 0, False, "No slots"
        
        # Pick a random slot to avoid conflicts
        slot = random.choice(available_slots)
        print(f"Using slot: Court {slot['court']} at {slot['time']}")
        
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
                # Take screenshot for analysis
                screenshot_path = f'/mnt/c/Documents/code/python/lvbot/email_speed_test_{email_speed_multiplier}x.png'
                await page.screenshot(path=screenshot_path)
                
                # Check for anti-bot message
                error_element = await page.query_selector('p[role="alert"]')
                if error_element:
                    error_text = await error_element.inner_text()
                    if 'irregular' in error_text.lower() or 'detectó' in error_text.lower():
                        bot_detected = True
                        error_msg = error_text
                        logger.error(f"BOT DETECTED: {error_text}")
                
                # Also check page content
                if not bot_detected:
                    page_text = await page.inner_text('body')
                    if 'irregular' in page_text.lower():
                        bot_detected = True
                        error_msg = "Bot detection in page content"
            except Exception as e:
                logger.warning(f"Error checking bot detection: {e}")
        
        # Cleanup
        await browser_pool.close()
        
        return result.success and not bot_detected, execution_time, bot_detected, error_msg
        
    finally:
        # Restore original file
        shutil.copy2(backup_file, original_file)
        import os
        os.remove(backup_file)

async def main():
    """Run email speed tests"""
    t('archive.testing.tests.test_email_speed_simple.main')
    
    print("\n" + "="*80)
    print("EMAIL TYPING SPEED LIMIT TEST")
    print("="*80)
    print("Testing different email typing speeds to find the limit")
    print("Current safe speed: 2.5x")
    print("="*80)
    
    # Test speeds
    test_speeds = [2.5, 3.0, 3.5, 4.0, 5.0]
    
    results = []
    
    for speed in test_speeds:
        success, exec_time, bot_detected, error_msg = await test_with_email_speed(speed)
        
        results.append({
            'speed': speed,
            'success': success,
            'time': exec_time,
            'bot_detected': bot_detected,
            'error': error_msg
        })
        
        print(f"\nResult:")
        print(f"  Success: {'✅ YES' if success else '❌ NO'}")
        print(f"  Bot detected: {'🚨 YES' if bot_detected else '✅ NO'}")
        print(f"  Execution time: {exec_time:.1f}s")
        if error_msg:
            print(f"  Error: {error_msg}")
        
        # Stop if bot detected
        if bot_detected:
            print("\n⚠️  Bot detection triggered! Stopping tests.")
            break
        
        # Wait between tests
        if speed != test_speeds[-1]:
            print("\nWaiting 15 seconds before next test...")
            await asyncio.sleep(15)
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"{'Speed':<10} {'Success':<10} {'Bot Detected':<15} {'Time (s)':<10}")
    print("-"*80)
    
    max_safe_speed = 2.5
    for r in results:
        success = "✅" if r['success'] else "❌"
        bot = "🚨 YES" if r['bot_detected'] else "NO"
        print(f"{r['speed']:<10} {success:<10} {bot:<15} {r['time']:<10.1f}")
        
        if r['success'] and not r['bot_detected']:
            max_safe_speed = r['speed']
    
    print("="*80)
    print(f"\n🎯 MAXIMUM SAFE EMAIL SPEED: {max_safe_speed}x")
    
    # Calculate potential savings
    if max_safe_speed > 2.5:
        # Email takes ~10.4s at 2.5x
        email_time_current = 10.4
        email_time_optimized = email_time_current * (2.5 / max_safe_speed)
        time_saved = email_time_current - email_time_optimized
        
        print(f"\n📊 TIME SAVINGS ANALYSIS:")
        print(f"   Current (2.5x): {email_time_current:.1f}s")
        print(f"   Optimized ({max_safe_speed}x): {email_time_optimized:.1f}s")
        print(f"   Saved: {time_saved:.1f}s")
        print(f"   New total: ~{40.2 - time_saved:.1f}s (from 40.2s)")

if __name__ == "__main__":
    asyncio.run(main())
