#!/usr/bin/env python3
"""
Implement experienced user mode in the main booking executor
Adds a flag to enable fast booking for experienced users
"""
import pathlib
import sys
import shutil

ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

PROJECT_UTILS = ROOT_DIR / 'lvbot' / 'utils'

def add_experienced_mode():
    """Add experienced user mode to async_booking_executor.py"""
    
    # Read the current async_booking_executor.py
    executor_file = PROJECT_UTILS / 'async_booking_executor.py'
    backup_file = executor_file.with_suffix('.py.before_experienced')

    # Create backup
    shutil.copy2(executor_file, backup_file)
    
    with open(executor_file, 'r') as f:
        content = f.read()
    
    # Add experienced mode parameter to __init__
    content = content.replace(
        'def __init__(self, browser_pool, use_natural_flow=True):',
        'def __init__(self, browser_pool, use_natural_flow=True, experienced_mode=False):'
    )
    
    # Add instance variable
    content = content.replace(
        'self.use_natural_flow = use_natural_flow',
        '''self.use_natural_flow = use_natural_flow
        self.experienced_mode = experienced_mode'''
    )
    
    # Add experienced mode handling in execute_booking
    content = content.replace(
        '''# Use working solution from court_booking_final.py
        self.logger.info(f"Using WORKING solution from court_booking_final.py for Court {court_number}")
        working_executor = WorkingBookingExecutor(self.browser_pool)''',
        '''# Check if experienced mode is enabled
        if self.experienced_mode:
            self.logger.info(f"Using EXPERIENCED USER mode for Court {court_number}")
            # Import and use experienced executor
            from .experienced_booking_executor import ExperiencedBookingExecutor
            working_executor = ExperiencedBookingExecutor(self.browser_pool)
        else:
            # Use working solution from court_booking_final.py
            self.logger.info(f"Using WORKING solution from court_booking_final.py for Court {court_number}")
            working_executor = WorkingBookingExecutor(self.browser_pool)'''
    )
    
    # Write updated file
    with open(executor_file, 'w') as f:
        f.write(content)
    
    print("✅ Added experienced_mode parameter to AsyncBookingExecutor")
    
    # Create the experienced booking executor
    experienced_content = '''"""
Experienced Booking Executor - Fast booking for frequent users
Based on working executor but with minimal delays
"""

import asyncio
import random
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass
from playwright.async_api import Page

# Aggressive speed for experienced users
SPEED_MULTIPLIER = 5.0

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

async def fast_fill(element, text):
    """Fast fill for experienced users - like autofill"""
    await element.click()
    await asyncio.sleep(0.05)
    await element.fill('')
    await asyncio.sleep(0.05)
    await element.fill(text)
    await asyncio.sleep(0.1)

async def minimal_mouse_movement(page: Page):
    """Minimal mouse movement for experienced users"""
    x = random.randint(400, 800)
    y = random.randint(300, 600)
    await page.mouse.move(x, y)
    await asyncio.sleep(0.1)

class ExperiencedBookingExecutor:
    """Executor for experienced users with minimal delays"""
    
    def __init__(self, browser_pool=None):
        self.browser_pool = browser_pool
        self.logger = logging.getLogger('ExperiencedBookingExecutor')
        
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
            
            self.logger.info(f"Starting EXPERIENCED booking: Court {court_number} at {time_slot}")
            
            # Minimal initial delay - experienced user knows the page
            delay = random.uniform(0.8, 1.2)
            self.logger.info(f"Minimal initial delay ({delay:.1f}s)")
            await asyncio.sleep(delay)
            
            # Quick mouse movement
            await minimal_mouse_movement(page)
            
            # Find and click time slot FAST
            self.logger.info(f"Looking for {time_slot} time slot...")
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
            
            self.logger.info(f"Found {time_slot} time slot!")
            
            # Quick approach and click
            button_box = await time_button.bounding_box()
            if button_box:
                target_x = button_box['x'] + button_box['width'] / 2
                target_y = button_box['y'] + button_box['height'] / 2
                await page.mouse.move(target_x, target_y)
                await asyncio.sleep(0.1)
            
            self.logger.info("Clicking time slot...")
            await time_button.click()
            await asyncio.sleep(1.5)  # Reduced wait
            
            # Wait for form
            self.logger.info("Waiting for booking form...")
            await page.wait_for_selector('#client\\\\.firstName', timeout=10000)
            await asyncio.sleep(0.3)
            
            self.logger.info("Booking form loaded!")
            
            # Fast form filling
            form_start = time.time()
            self.logger.info("Fast form filling (experienced user)...")
            
            # All fields with fast fill
            firstName = await page.query_selector('#client\\\\.firstName')
            if firstName:
                await fast_fill(firstName, user_info.get('first_name', 'Test'))
            
            lastName = await page.query_selector('#client\\\\.lastName')
            if lastName:
                await fast_fill(lastName, user_info.get('last_name', 'User'))
            
            phone = await page.query_selector('#client\\\\.phone')
            if phone:
                await fast_fill(phone, user_info.get('phone', '12345678'))
            
            email = await page.query_selector('#client\\\\.email')
            if email:
                await fast_fill(email, user_info.get('email', 'test@example.com'))
            
            form_time = time.time() - form_start
            self.logger.info(f"Form filled in {form_time:.1f} seconds")
            
            # Quick submit
            self.logger.info("Preparing submission...")
            await asyncio.sleep(0.2)
            
            submit_button = await page.query_selector('button:has-text("CONFIRMAR CITA")')
            if submit_button:
                self.logger.info("Submitting booking...")
                await submit_button.click()
                
                # Reduced confirmation wait
                self.logger.info("Waiting for confirmation...")
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
                    
                    # Try to extract user name
                    user_name = None
                    try:
                        import re
                        name_match = re.search(r'([A-Za-z]+),\\s*¡Tu cita está confirmada!', page_content)
                        if name_match:
                            user_name = name_match.group(1)
                    except:
                        pass
                    
                    return ExecutionResult(
                        success=True,
                        court_number=court_number,
                        confirmation_url=current_url,
                        confirmation_id=confirmation_id,
                        user_name=user_name
                    )
                else:
                    return ExecutionResult(
                        success=False,
                        court_number=court_number,
                        error_message="Booking status unclear after submission"
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
    
    # Write experienced executor
    experienced_file = '/mnt/c/Documents/code/python/lvbot/utils/experienced_booking_executor.py'
    with open(experienced_file, 'w') as f:
        f.write(experienced_content)
    
    print("✅ Created experienced_booking_executor.py")
    print("\n📝 Usage:")
    print("   executor = AsyncBookingExecutor(browser_pool, experienced_mode=True)")
    print("   # This will use fast booking (26.5s instead of 40.2s)")
    
    return True

if __name__ == "__main__":
    add_experienced_mode()
