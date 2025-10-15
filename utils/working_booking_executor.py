"""
Working Booking Executor - Based on proven court_booking_final.py
This is a direct copy of the working solution with minimal adaptations for LVBOT
DO NOT CHANGE THE CORE LOGIC
"""

import asyncio
import random
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass
from playwright.async_api import Page

# SPEED MULTIPLIER - Proven to work reliably
SPEED_MULTIPLIER = 2.5

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
    return max(0.1, delay_seconds / SPEED_MULTIPLIER)

async def human_type_with_mistakes(element, text, mistake_prob=0.10):
    """Type with human-like mistakes and corrections - SPEED MULTIPLIER APPLIED."""
    await element.click()
    await asyncio.sleep(apply_speed(random.uniform(0.3, 0.8)))
    await element.fill('')  # Clear field
    await asyncio.sleep(apply_speed(random.uniform(0.2, 0.5)))
    
    # Type with occasional mistakes
    for i, char in enumerate(text):
        # Mistake probability (reduce mistakes at higher speeds)
        adjusted_mistake_prob = mistake_prob / max(1, SPEED_MULTIPLIER * 0.5)
        
        if random.random() < adjusted_mistake_prob and i > 0:
            # Type wrong character first
            wrong_chars = 'abcdefghijklmnopqrstuvwxyz'
            wrong_char = random.choice(wrong_chars)
            if wrong_char != char.lower():
                base_delay = random.randint(80, 180) / SPEED_MULTIPLIER
                await element.type(wrong_char, delay=max(20, int(base_delay)))
                await asyncio.sleep(apply_speed(random.uniform(0.1, 0.4)))
                
                # Realize mistake and backspace
                await element.press('Backspace')
                await asyncio.sleep(apply_speed(random.uniform(0.2, 0.6)))
        
        # Type correct character
        base_delay = random.randint(90, 220) / SPEED_MULTIPLIER
        await element.type(char, delay=max(20, int(base_delay)))
        
        # Random pauses while thinking (less frequent at higher speeds)
        if random.random() < (0.2 / SPEED_MULTIPLIER):
            await asyncio.sleep(apply_speed(random.uniform(0.3, 1.2)))


async def natural_mouse_movement(page: Page):
    """Natural mouse movement patterns - SPEED MULTIPLIER APPLIED."""
    # OPTIMIZED: Reduced movements from 2-4 to 1-2
    movement_count = max(1, int(random.randint(1, 2) / SPEED_MULTIPLIER))
    
    for _ in range(movement_count):
        x = random.randint(200, 1000)
        y = random.randint(200, 700)
        await page.mouse.move(x, y)
        # OPTIMIZED: Reduced delays from 0.5-1.5s to 0.2-0.5s
        await asyncio.sleep(apply_speed(random.uniform(0.2, 0.5)))
        
        # OPTIMIZED: Less frequent pauses
        if random.random() < (0.15 / SPEED_MULTIPLIER):
            await asyncio.sleep(apply_speed(random.uniform(0.5, 1.0)))


class WorkingBookingExecutor:
    """Working booking executor based on proven court_booking_final.py"""
    
    def __init__(self, browser_pool=None):
        self.browser_pool = browser_pool
        self.logger = logging.getLogger('WorkingBookingExecutor')
        
    async def execute_booking(
        self,
        court_number: int,
        target_date: datetime,
        time_slot: str,
        user_info: Dict[str, str]
    ) -> ExecutionResult:
        """Execute booking using the proven working method"""
        
        if not self.browser_pool:
            return ExecutionResult(
                success=False,
                error_message="Browser pool not initialized"
            )
        
        try:
            # Get page from browser pool
            page = await self.browser_pool.get_page(court_number)
            if not page:
                return ExecutionResult(
                    success=False,
                    error_message=f"Could not get page for court {court_number}"
                )
            
            # Execute the working booking flow
            return await self._execute_booking_internal(
                page, court_number, target_date, time_slot, user_info
            )
            
        except Exception as e:
            self.logger.error(f"Booking execution error: {e}")
            return ExecutionResult(
                success=False,
                error_message=str(e)
            )
    
    async def _execute_booking_internal(
        self,
        page: Page,
        court_number: int,
        target_date: datetime,
        time_slot: str,
        user_info: Dict[str, str]
    ) -> ExecutionResult:
        """Internal booking execution - EXACT COPY OF WORKING LOGIC"""
        
        try:
            self.logger.info(f"Starting booking: Court {court_number} at {time_slot} on {target_date}")
            
            # IMPORTANT: Initial delay to appear more human-like
            delay_min = getattr(self, 'INITIAL_DELAY_MIN', 3.0)  # Default 3s
            delay_max = getattr(self, 'INITIAL_DELAY_MAX', 5.0)  # Default 5s
            delay = random.uniform(delay_min, delay_max)
            self.logger.info(f"Initial human-like delay ({delay:.1f} seconds)...")
            await asyncio.sleep(delay)
            
            # Natural page exploration (from working solution)
            await natural_mouse_movement(page)
            
            # Step 1: Find and click target time slot (EXACT COPY)
            self.logger.info(f"Looking for {time_slot} time slot...")
            
            # Look for the target time button - EXACT selector from working solution
            time_button = await page.query_selector(f'button:has-text("{time_slot}")')
            
            if not time_button:
                # Try alternative time formats - EXACT logic from working solution
                alt_formats = [time_slot.replace(':00', ''), time_slot.split(':')[0]]
                for alt_time in alt_formats:
                    time_button = await page.query_selector(f'button:has-text("{alt_time}")')
                    if time_button:
                        self.logger.info(f"Found time button with format: {alt_time}")
                        break
            
            if not time_button:
                self.logger.error("Target time slot not found")
                return ExecutionResult(
                    success=False,
                    court_number=court_number,
                    error_message=f"Time slot {time_slot} not found"
                )
            
            self.logger.info(f"Found {time_slot} time slot!")
            
            # Natural approach to time button - OPTIMIZED
            await page.mouse.move(random.randint(400, 800), random.randint(300, 600))
            # OPTIMIZED: Reduced approach delay from 1-2s to 0.3-0.5s
            await asyncio.sleep(apply_speed(random.uniform(0.3, 0.5)))
            
            button_box = await time_button.bounding_box()
            if button_box:
                target_x = button_box['x'] + button_box['width'] / 2
                target_y = button_box['y'] + button_box['height'] / 2
                await page.mouse.move(target_x, target_y)
                # OPTIMIZED: Reduced approach delay from 1-2s to 0.3-0.5s
                await asyncio.sleep(apply_speed(random.uniform(0.3, 0.5)))
            
            # Click the time slot - OPTIMIZED
            self.logger.info("Clicking time slot...")
            await time_button.click()
            # OPTIMIZED: Reduced after-click delay from 3-5s to 2-3s
            await asyncio.sleep(apply_speed(random.uniform(2, 3)))
            
            # Step 2: Wait for booking form - EXACT copy
            self.logger.info("Waiting for booking form to load...")
            await page.wait_for_selector('#client\\.firstName', timeout=10000)
            await asyncio.sleep(apply_speed(random.uniform(2, 4)))
            
            self.logger.info("Booking form loaded successfully!")
            
            # Step 3: Form filling - EXACT copy with user_info
            form_start_time = time.time()
            self.logger.info(f"Filling booking form with {SPEED_MULTIPLIER}x speed...")
            
            # Fill NOMBRE
            self.logger.info("Typing NOMBRE...")
            firstName = await page.query_selector('#client\\.firstName')
            if firstName:
                await human_type_with_mistakes(firstName, user_info.get('first_name', 'Test'), 0.15)
                await asyncio.sleep(apply_speed(random.uniform(0.5, 1.5)))
            
            # Fill APELLIDOS  
            self.logger.info("Typing APELLIDOS...")
            lastName = await page.query_selector('#client\\.lastName')
            if lastName:
                await human_type_with_mistakes(lastName, user_info.get('last_name', 'User'), 0.15)
                await asyncio.sleep(apply_speed(random.uniform(0.5, 1.5)))
            
            # Fill TELÉFONO
            self.logger.info("Typing TELÉFONO...")
            phone = await page.query_selector('#client\\.phone')
            if phone:
                await phone.click()
                await asyncio.sleep(apply_speed(random.uniform(0.3, 0.7)))
                await phone.fill(user_info.get('phone', '12345678'))
                await asyncio.sleep(apply_speed(random.uniform(0.5, 1.0)))
            
            # Fill EMAIL
            self.logger.info("Typing EMAIL...")
            email = await page.query_selector('#client\\.email')
            if email:
                await human_type_with_mistakes(email, user_info.get('email', 'test@example.com'), 0.10)
                await asyncio.sleep(apply_speed(random.uniform(1, 2)))
            
            form_end_time = time.time()
            actual_form_time = form_end_time - form_start_time
            self.logger.info(f"Form filled in {actual_form_time:.1f} seconds")
            
            # Step 4: Submit - EXACT copy
            self.logger.info("Preparing for submission...")
            
            # Review form naturally
            await page.mouse.move(random.randint(300, 700), random.randint(600, 800))
            await asyncio.sleep(apply_speed(random.uniform(0.5, 1.0)))
            
            # Find and click submit button
            submit_button = await page.query_selector('button:has-text("CONFIRMAR CITA")')
            if submit_button:
                # Natural approach to submit button
                button_box = await submit_button.bounding_box()
                if button_box:
                    target_x = button_box['x'] + button_box['width'] / 2
                    target_y = button_box['y'] + button_box['height'] / 2
                    await page.mouse.move(target_x, target_y)
                    await asyncio.sleep(random.uniform(1, 2))
                
                self.logger.info("Submitting booking...")
                await submit_button.click()
                
                # Wait for response
                self.logger.info("Waiting for booking confirmation...")
                # OPTIMIZED: Reduced confirmation wait from 5s to 3s minimum
                await asyncio.sleep(max(3, apply_speed(random.uniform(5, 8))))
                
                # Check result - adapted for LVBOT
                current_url = page.url
                page_content = await page.content()
                
                # Extract confirmation ID from URL if present
                confirmation_id = None
                if '/confirmation/' in current_url:
                    try:
                        confirmation_id = current_url.split('/confirmation/')[1].split('/')[0].split('?')[0]
                    except:
                        pass
                
                # Check for success
                success_indicators = [
                    'confirmado' in page_content.lower(),
                    'confirmed' in page_content.lower(),
                    'reserva' in page_content.lower() and 'éxito' in page_content.lower(),
                    confirmation_id is not None
                ]
                
                if any(success_indicators):
                    self.logger.info("BOOKING SUCCESSFUL!")
                    
                    # Try to extract user name from confirmation
                    user_name = None
                    try:
                        import re
                        name_match = re.search(r'([A-Za-z]+),\s*¡Tu cita está confirmada!', page_content)
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
                    self.logger.warning("Booking status unclear")
                    return ExecutionResult(
                        success=False,
                        court_number=court_number,
                        error_message="Booking status unclear after submission"
                    )
            else:
                self.logger.error("Submit button not found")
                return ExecutionResult(
                    success=False,
                    court_number=court_number,
                    error_message="Submit button not found"
                )
                
        except Exception as e:
            self.logger.error(f"Internal booking error: {e}")
            return ExecutionResult(
                success=False,
                court_number=court_number,
                error_message=str(e)
            )