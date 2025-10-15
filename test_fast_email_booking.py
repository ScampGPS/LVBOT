#!/usr/bin/env python3
"""
Test fast email typing in actual booking flow
Tests if faster email typing works in full booking context
"""

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

async def test_booking_with_fast_email(email_speed: float = 5.0):
    """Test booking with faster email typing speed"""
    logger = logging.getLogger('FastEmailBookingTest')
    
    print("\n" + "="*80)
    print(f"FAST EMAIL BOOKING TEST - {email_speed}x Email Speed")
    print("="*80)
    print(f"Testing full booking with {email_speed}x email typing speed")
    print(f"Other fields remain at 2.5x speed")
    print("="*80 + "\n")
    
    # First, let's modify the working executor to use faster email speed
    import shutil
    original_file = '/mnt/c/Documents/code/python/lvbot/utils/working_booking_executor.py'
    
    # Read the file
    with open(original_file, 'r') as f:
        content = f.read()
    
    # Find the email typing section and inject speed override
    modified_content = content.replace(
        """# Fill EMAIL
            self.logger.info("Typing EMAIL...")
            email = await page.query_selector('#client\\.email')
            if email:
                await human_type_with_mistakes(email, user_info.get('email', 'test@example.com'), 0.10)""",
        f"""# Fill EMAIL
            self.logger.info("Typing EMAIL...")
            email = await page.query_selector('#client\\.email')
            if email:
                # OPTIMIZED: Using {email_speed}x speed for email
                import asyncio
                import random
                
                await email.click()
                await asyncio.sleep(0.1)
                await email.fill('')
                
                email_text = user_info.get('email', 'test@example.com')
                email_start = time.time()
                
                # Type with {email_speed}x speed
                for char in email_text:
                    base_delay = random.randint(90, 220) / {email_speed}
                    await email.type(char, delay=max(10, int(base_delay)))
                    if random.random() < (0.1 / {email_speed}):
                        await asyncio.sleep(random.uniform(0.2, 0.5) / {email_speed})
                
                email_time = time.time() - email_start
                self.logger.info(f"Email typed in {{email_time:.2f}}s at {email_speed}x speed")"""
    )
    
    # Create backup and write modified version
    backup_file = original_file + '.bak'
    shutil.copy2(original_file, backup_file)
    
    try:
        with open(original_file, 'w') as f:
            f.write(modified_content)
        
        # Now run the actual booking test
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
        browser_pool.WARMUP_DELAY = 4.0
        await browser_pool.start()
        
        # Find available slots for tomorrow
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
            return False, 0, False
        
        # Use first available slot
        slot = available_slots[0]
        print(f"Testing with: Court {slot['court']} at {slot['time']} on {tomorrow_str}")
        
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
                await page.screenshot(path=f'/mnt/c/Documents/code/python/lvbot/fast_email_result_{email_speed}x.png')
                
                error_element = await page.query_selector('p[role="alert"]')
                if error_element:
                    error_text = await error_element.inner_text()
                    if 'irregular' in error_text.lower() or 'detectó' in error_text.lower():
                        bot_detected = True
                        logger.error(f"BOT DETECTED: {error_text}")
                
                page_text = await page.inner_text('body')
                if 'irregular' in page_text.lower() and not bot_detected:
                    bot_detected = True
            except:
                pass
        
        # Results
        print("\n" + "="*80)
        print("RESULTS:")
        print(f"Email speed: {email_speed}x")
        print(f"Total execution time: {execution_time:.1f}s")
        print(f"Bot detected: {'🚨 YES' if bot_detected else '✅ NO'}")
        print(f"Booking success: {'✅ YES' if result.success and not bot_detected else '❌ NO'}")
        
        if result.success and not bot_detected:
            print(f"Confirmation ID: {result.confirmation_id}")
            
            # Calculate improvement
            baseline_total = 40.2  # Our optimized baseline
            print(f"\n📊 PERFORMANCE:")
            print(f"   Baseline (2.5x email): {baseline_total:.1f}s")
            print(f"   With {email_speed}x email: {execution_time:.1f}s")
            print(f"   Time saved: {baseline_total - execution_time:.1f}s")
        else:
            if result.error_message:
                print(f"Error: {result.error_message}")
        
        print("="*80)
        
        return result.success and not bot_detected, execution_time, bot_detected
        
    finally:
        # Restore original file
        shutil.copy2(backup_file, original_file)
        import os
        os.remove(backup_file)

async def main():
    """Test different email speeds in full booking context"""
    
    # Test progressively faster speeds
    test_speeds = [5.0, 7.0, 10.0]
    
    for speed in test_speeds:
        success, exec_time, bot_detected = await test_booking_with_fast_email(speed)
        
        if bot_detected:
            print(f"\n⚠️ Bot detection at {speed}x! Stopping tests.")
            break
        
        if speed != test_speeds[-1]:
            print("\nWaiting 15 seconds before next test...")
            await asyncio.sleep(15)

if __name__ == "__main__":
    asyncio.run(main())