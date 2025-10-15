#!/usr/bin/env python3
"""
Test experienced user pattern with minimal delays
Simulating a frequent user who knows exactly where everything is
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
import random

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

# Create the experienced user executor
experienced_executor_content = '''"""
Experienced User Executor - Minimal delays for frequent users
Based on working executor but with aggressive timing
"""

import asyncio
import random
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass
from playwright.async_api import Page

# AGGRESSIVE SPEED for experienced users
SPEED_MULTIPLIER = 5.0  # Much faster

@dataclass
class ExecutionResult:
    """Result of a booking execution."""
    success: bool
    court_number: Optional[int] = None
    error_message: Optional[str] = None
    confirmation_url: Optional[str] = None
    confirmation_id: Optional[str] = None
    user_name: Optional[str] = None

def apply_speed(delay_seconds):
    """Apply speed multiplier to delay times."""
    return max(0.05, delay_seconds / SPEED_MULTIPLIER)

async def fast_paste(element, text):
    """Fast paste for experienced users"""
    await element.click()
    await asyncio.sleep(0.05)
    await element.fill('')
    await asyncio.sleep(0.05)
    await element.fill(text)
    await asyncio.sleep(0.1)

async def minimal_mouse_movement(page: Page):
    """Minimal mouse movement for experienced users"""
    # Just one quick movement
    x = random.randint(400, 800)
    y = random.randint(300, 600)
    await page.mouse.move(x, y)
    await asyncio.sleep(0.1)

class ExperiencedUserExecutor:
    """Executor for experienced users with minimal delays"""
    
    def __init__(self, browser_pool=None):
        self.browser_pool = browser_pool
        self.logger = logging.getLogger('ExperiencedUserExecutor')
        
    async def execute_booking(
        self,
        court_number: int,
        target_date: datetime,
        time_slot: str,
        user_info: Dict[str, str]
    ) -> ExecutionResult:
        """Execute booking with experienced user timing"""
        
        if not self.browser_pool:
            return ExecutionResult(
                success=False,
                error_message="Browser pool not initialized"
            )
        
        try:
            page = await self.browser_pool.get_page(court_number)
            if not page:
                return ExecutionResult(
                    success=False,
                    error_message=f"Could not get page for court {court_number}"
                )
            
            self.logger.info(f"EXPERIENCED USER booking: Court {court_number} at {time_slot}")
            
            # MINIMAL initial delay - experienced user knows the page
            delay = random.uniform(0.8, 1.2)
            self.logger.info(f"Minimal initial delay ({delay:.1f}s)")
            await asyncio.sleep(delay)
            
            # Quick mouse movement
            await minimal_mouse_movement(page)
            
            # Find and click time slot FAST
            self.logger.info(f"Quick click on {time_slot}...")
            time_button = await page.query_selector(f'button:has-text("{time_slot}")')
            
            if not time_button:
                alt_formats = [time_slot.replace(':00', ''), time_slot.split(':')[0]]
                for alt_time in alt_formats:
                    time_button = await page.query_selector(f'button:has-text("{alt_time}")')
                    if time_button:
                        break
            
            if not time_button:
                return ExecutionResult(
                    success=False,
                    court_number=court_number,
                    error_message=f"Time slot {time_slot} not found"
                )
            
            # Quick approach and click
            button_box = await time_button.bounding_box()
            if button_box:
                target_x = button_box['x'] + button_box['width'] / 2
                target_y = button_box['y'] + button_box['height'] / 2
                await page.mouse.move(target_x, target_y)
                await asyncio.sleep(0.1)  # Minimal delay
            
            await time_button.click()
            await asyncio.sleep(1.5)  # Reduced wait
            
            # Wait for form
            await page.wait_for_selector('#client\\\\.firstName', timeout=10000)
            await asyncio.sleep(0.3)  # Minimal wait
            
            # FAST FORM FILLING - like autofill
            form_start = time.time()
            self.logger.info("Fast form filling (paste-like)...")
            
            # All fields with paste behavior
            firstName = await page.query_selector('#client\\\\.firstName')
            if firstName:
                await fast_paste(firstName, user_info.get('first_name', 'Test'))
            
            lastName = await page.query_selector('#client\\\\.lastName')
            if lastName:
                await fast_paste(lastName, user_info.get('last_name', 'User'))
            
            phone = await page.query_selector('#client\\\\.phone')
            if phone:
                await fast_paste(phone, user_info.get('phone', '12345678'))
            
            email = await page.query_selector('#client\\\\.email')
            if email:
                await fast_paste(email, user_info.get('email', 'test@example.com'))
            
            form_time = time.time() - form_start
            self.logger.info(f"Form filled in {form_time:.1f}s")
            
            # Quick submit
            await asyncio.sleep(0.2)  # Minimal review
            
            submit_button = await page.query_selector('button:has-text("CONFIRMAR CITA")')
            if submit_button:
                await submit_button.click()
                
                # Reduced confirmation wait
                await asyncio.sleep(2.0)
                
                # Check result
                current_url = page.url
                page_content = await page.content()
                
                confirmation_id = None
                if '/confirmation/' in current_url:
                    try:
                        confirmation_id = current_url.split('/confirmation/')[1].split('/')[0].split('?')[0]
                    except:
                        pass
                
                success_indicators = [
                    'confirmado' in page_content.lower(),
                    'confirmed' in page_content.lower(),
                    confirmation_id is not None
                ]
                
                if any(success_indicators):
                    self.logger.info("BOOKING SUCCESSFUL!")
                    return ExecutionResult(
                        success=True,
                        court_number=court_number,
                        confirmation_url=current_url,
                        confirmation_id=confirmation_id
                    )
                else:
                    return ExecutionResult(
                        success=False,
                        court_number=court_number,
                        error_message="Booking status unclear"
                    )
            else:
                return ExecutionResult(
                    success=False,
                    court_number=court_number,
                    error_message="Submit button not found"
                )
                
        except Exception as e:
            self.logger.error(f"Booking error: {e}")
            return ExecutionResult(
                success=False,
                court_number=court_number,
                error_message=str(e)
            )
'''

async def test_experienced_user():
    """Test with experienced user timing"""
    logger = logging.getLogger('ExperiencedUserTest')
    
    print("\n" + "="*80)
    print("EXPERIENCED USER PATTERN TEST")
    print("="*80)
    print("Testing minimal delays - simulating frequent user")
    print("- Minimal initial delay (0.8-1.2s)")
    print("- Quick navigation")
    print("- Fast form filling (paste-like)")
    print("- Reduced waits throughout")
    print("="*80 + "\n")
    
    # Write the experienced user executor
    with open('/mnt/c/Documents/code/python/lvbot/experienced_user_executor.py', 'w') as f:
        f.write(experienced_executor_content)
    
    try:
        # Import and use it
        import sys
        sys.path.insert(0, '/mnt/c/Documents/code/python/lvbot')
        from experienced_user_executor import ExperiencedUserExecutor
        
        from lvbot.utils.async_browser_pool import AsyncBrowserPool
        from lvbot.utils.court_availability import CourtAvailability
        
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
        
        # Find slot
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
        
        slot = available_slots[0]
        print(f"Using: Court {slot['court']} at {slot['time']} on {tomorrow_str}")
        print("="*80 + "\n")
        
        # Execute with experienced user executor
        executor = ExperiencedUserExecutor(browser_pool)
        
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
                await page.screenshot(path='/mnt/c/Documents/code/python/lvbot/experienced_user_result.png')
                
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
                logger.warning(f"Error checking detection: {e}")
        
        # Results
        print("\n" + "="*80)
        print("RESULTS:")
        print(f"Execution time: {execution_time:.1f}s")
        print(f"Bot detected: {'🚨 YES' if bot_detected else '✅ NO'}")
        print(f"Booking success: {'✅ YES' if result.success and not bot_detected else '❌ NO'}")
        
        if result.success and not bot_detected:
            print(f"Confirmation ID: {result.confirmation_id}")
            
            # Compare to baseline
            baseline = 40.2
            improvement = baseline - execution_time
            print(f"\n📊 PERFORMANCE:")
            print(f"   Baseline: {baseline:.1f}s")
            print(f"   Experienced user: {execution_time:.1f}s")
            print(f"   Time saved: {improvement:.1f}s ({improvement/baseline*100:.1f}% faster)")
        else:
            if result.error_message:
                print(f"Error: {result.error_message}")
            if error_msg:
                print(f"Detection: {error_msg}")
        
        print("="*80)
        
        # Brief wait before cleanup
        await asyncio.sleep(5)
        
        return result.success and not bot_detected, execution_time, bot_detected, error_msg
        
    finally:
        # Cleanup
        import os
        if os.path.exists('/mnt/c/Documents/code/python/lvbot/experienced_user_executor.py'):
            os.remove('/mnt/c/Documents/code/python/lvbot/experienced_user_executor.py')

async def main():
    """Run experienced user test"""
    await test_experienced_user()

if __name__ == "__main__":
    asyncio.run(main())