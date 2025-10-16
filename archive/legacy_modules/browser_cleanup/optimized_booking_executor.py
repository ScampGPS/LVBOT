#!/usr/bin/env python3
"""
Optimized Booking Executor - Faster version based on phase analysis
Targets the slowest phases identified in analysis
"""

import asyncio
import random
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Speed configuration based on analysis
SPEED_CONFIG = {
    # Original settings
    'SPEED_MULTIPLIER': 2.5,
    'WARMUP_DELAY': 4.0,
    'INITIAL_DELAY_MIN': 1.0,
    'INITIAL_DELAY_MAX': 2.0,
    
    # New optimizations
    'MOUSE_MOVEMENTS': 1,  # Reduced from 2-4
    'MOUSE_MOVE_DELAY': 0.2,  # Reduced from 0.5-1.5
    'APPROACH_BUTTON_DELAY': 0.3,  # Reduced from 1-2s
    'AFTER_CLICK_DELAY': 2.0,  # Reduced from 3-5s
    'FORM_WAIT_DELAY': 1.0,  # Reduced from 2-4s
    'PRE_SUBMIT_DELAY': 0.5,  # Reduced from 1s
    'SUBMIT_APPROACH_DELAY': 0.3,  # Reduced from 0.5s
    'CONFIRMATION_WAIT': 3.0,  # Reduced from 5s
    'TYPING_SPEED_MULTIPLIER': 3.5,  # Increased from 2.5
}

@dataclass
class OptimizedExecutionResult:
    """Result of an optimized booking execution"""
    success: bool
    court_number: Optional[int] = None
    error_message: Optional[str] = None
    confirmation_url: Optional[str] = None
    confirmation_id: Optional[str] = None
    user_name: Optional[str] = None
    execution_time: Optional[float] = None
    phase_times: Optional[Dict[str, float]] = None

def apply_speed(delay_seconds):
    """Apply speed multiplier to delay times"""
    return max(0.1, delay_seconds / SPEED_CONFIG['SPEED_MULTIPLIER'])

async def optimized_mouse_movement(page):
    """Optimized mouse movement - fewer, faster movements"""
    for _ in range(SPEED_CONFIG['MOUSE_MOVEMENTS']):
        x = random.randint(400, 800)
        y = random.randint(300, 600)
        await page.mouse.move(x, y)
        await asyncio.sleep(SPEED_CONFIG['MOUSE_MOVE_DELAY'])

async def optimized_typing(element, text, mistake_prob=0.05):
    """Optimized typing - faster with fewer mistakes"""
    await element.click()
    await asyncio.sleep(0.1)
    await element.fill('')
    
    # Type faster with typing speed multiplier
    for i, char in enumerate(text):
        # Reduce mistakes at high speed
        adjusted_mistake_prob = mistake_prob / SPEED_CONFIG['TYPING_SPEED_MULTIPLIER']
        
        if random.random() < adjusted_mistake_prob and i > 0:
            # Quick mistake and correction
            wrong_char = random.choice('abcdefghijklmnopqrstuvwxyz')
            if wrong_char != char.lower():
                await element.type(wrong_char, delay=20)
                await asyncio.sleep(0.1)
                await element.press('Backspace')
                await asyncio.sleep(0.1)
        
        # Type with faster speed
        base_delay = random.randint(30, 60) / SPEED_CONFIG['TYPING_SPEED_MULTIPLIER']
        await element.type(char, delay=max(15, int(base_delay * 1000)))

class OptimizedBookingExecutor:
    """Optimized executor with faster phase timings"""
    
    def __init__(self, browser_pool=None):
        self.browser_pool = browser_pool
        self.logger = logging.getLogger('OptimizedExecutor')
        self.phase_times = {}
        
    def start_phase(self, phase_name: str):
        """Track phase start time"""
        self.phase_times[phase_name] = time.time()
        
    def end_phase(self, phase_name: str) -> float:
        """Track phase end time and return duration"""
        if phase_name in self.phase_times:
            duration = time.time() - self.phase_times[phase_name]
            self.phase_times[phase_name] = duration
            return duration
        return 0
    
    async def execute_booking(
        self,
        court_number: int,
        target_date: datetime,
        time_slot: str,
        user_info: Dict[str, str]
    ) -> OptimizedExecutionResult:
        """Execute optimized booking"""
        
        start_time = time.time()
        
        if not self.browser_pool:
            return OptimizedExecutionResult(
                success=False,
                error_message="Browser pool not initialized"
            )
        
        try:
            # Get page
            page = await self.browser_pool.get_page(court_number)
            if not page:
                return OptimizedExecutionResult(
                    success=False,
                    error_message=f"Could not get page for court {court_number}"
                )
            
            self.logger.info(f"Starting OPTIMIZED booking: Court {court_number} at {time_slot}")
            
            # Phase 1: Initial delay (OPTIMIZED)
            self.start_phase("initial_delay")
            delay = random.uniform(SPEED_CONFIG['INITIAL_DELAY_MIN'], SPEED_CONFIG['INITIAL_DELAY_MAX'])
            self.logger.info(f"Initial delay: {delay:.1f}s")
            await asyncio.sleep(delay)
            self.end_phase("initial_delay")
            
            # Phase 2: Mouse movement (OPTIMIZED - reduced movements)
            self.start_phase("mouse_movement")
            await optimized_mouse_movement(page)
            self.end_phase("mouse_movement")
            
            # Phase 3: Find time slot (already fast)
            self.start_phase("find_time_slot")
            self.logger.info(f"Looking for {time_slot} time slot...")
            time_button = await page.query_selector(f'button:has-text("{time_slot}")')
            
            if not time_button:
                alt_formats = [time_slot.replace(':00', ''), time_slot.split(':')[0]]
                for alt_time in alt_formats:
                    time_button = await page.query_selector(f'button:has-text("{alt_time}")')
                    if time_button:
                        break
            self.end_phase("find_time_slot")
            
            if not time_button:
                return OptimizedExecutionResult(
                    success=False,
                    court_number=court_number,
                    error_message=f"Time slot {time_slot} not found"
                )
            
            self.logger.info(f"Found {time_slot} time slot!")
            
            # Phase 4: Approach button (OPTIMIZED - faster approach)
            self.start_phase("approach_button")
            button_box = await time_button.bounding_box()
            if button_box:
                target_x = button_box['x'] + button_box['width'] / 2
                target_y = button_box['y'] + button_box['height'] / 2
                await page.mouse.move(target_x, target_y)
                await asyncio.sleep(SPEED_CONFIG['APPROACH_BUTTON_DELAY'])
            self.end_phase("approach_button")
            
            # Phase 5: Click time slot (OPTIMIZED - reduced wait)
            self.start_phase("click_time_slot")
            self.logger.info("Clicking time slot...")
            await time_button.click()
            await asyncio.sleep(SPEED_CONFIG['AFTER_CLICK_DELAY'])
            self.end_phase("click_time_slot")
            
            # Phase 6: Wait for form (OPTIMIZED - reduced wait)
            self.start_phase("wait_for_form")
            self.logger.info("Waiting for booking form...")
            await page.wait_for_selector('#client\\.firstName', timeout=10000)
            await asyncio.sleep(SPEED_CONFIG['FORM_WAIT_DELAY'])
            self.end_phase("wait_for_form")
            
            self.logger.info("Booking form loaded!")
            
            # Phase 7: Form filling (OPTIMIZED - faster typing)
            self.start_phase("form_filling")
            self.logger.info(f"Filling form with {SPEED_CONFIG['TYPING_SPEED_MULTIPLIER']}x typing speed...")
            
            # First name
            firstName = await page.query_selector('#client\\.firstName')
            if firstName:
                await optimized_typing(firstName, user_info.get('first_name', 'Test'))
                await asyncio.sleep(0.3)
            
            # Last name
            lastName = await page.query_selector('#client\\.lastName')
            if lastName:
                await optimized_typing(lastName, user_info.get('last_name', 'User'))
                await asyncio.sleep(0.3)
            
            # Phone (direct fill - already fast)
            phone = await page.query_selector('#client\\.phone')
            if phone:
                await phone.click()
                await asyncio.sleep(0.1)
                await phone.fill(user_info.get('phone', '12345678'))
                await asyncio.sleep(0.3)
            
            # Email
            email = await page.query_selector('#client\\.email')
            if email:
                await optimized_typing(email, user_info.get('email', 'test@example.com'))
            
            self.end_phase("form_filling")
            
            # Phase 8: Pre-submit review (OPTIMIZED)
            self.start_phase("pre_submit_review")
            await page.mouse.move(random.randint(400, 600), random.randint(700, 800))
            await asyncio.sleep(SPEED_CONFIG['PRE_SUBMIT_DELAY'])
            self.end_phase("pre_submit_review")
            
            # Phase 9: Submit
            submit_button = await page.query_selector('button:has-text("CONFIRMAR CITA")')
            if submit_button:
                # Approach submit (OPTIMIZED)
                self.start_phase("approach_submit")
                button_box = await submit_button.bounding_box()
                if button_box:
                    target_x = button_box['x'] + button_box['width'] / 2
                    target_y = button_box['y'] + button_box['height'] / 2
                    await page.mouse.move(target_x, target_y)
                    await asyncio.sleep(SPEED_CONFIG['SUBMIT_APPROACH_DELAY'])
                self.end_phase("approach_submit")
                
                # Click submit
                self.start_phase("click_submit")
                self.logger.info("Submitting booking...")
                await submit_button.click()
                self.end_phase("click_submit")
                
                # Wait for confirmation (OPTIMIZED)
                self.start_phase("wait_confirmation")
                self.logger.info("Waiting for confirmation...")
                await asyncio.sleep(SPEED_CONFIG['CONFIRMATION_WAIT'])
                self.end_phase("wait_confirmation")
                
                # Check result
                current_url = page.url
                page_content = await page.content()
                
                # Extract confirmation
                confirmation_id = None
                if '/confirmation/' in current_url:
                    try:
                        confirmation_id = current_url.split('/confirmation/')[1].split('/')[0].split('?')[0]
                    except:
                        pass
                
                # Check success
                success_indicators = [
                    'confirmado' in page_content.lower(),
                    'confirmed' in page_content.lower(),
                    confirmation_id is not None
                ]
                
                execution_time = time.time() - start_time
                
                if any(success_indicators):
                    self.logger.info(f"BOOKING SUCCESSFUL in {execution_time:.1f}s!")
                    
                    return OptimizedExecutionResult(
                        success=True,
                        court_number=court_number,
                        confirmation_url=current_url,
                        confirmation_id=confirmation_id,
                        execution_time=execution_time,
                        phase_times=self.phase_times
                    )
                else:
                    return OptimizedExecutionResult(
                        success=False,
                        court_number=court_number,
                        error_message="Booking status unclear",
                        execution_time=execution_time,
                        phase_times=self.phase_times
                    )
            else:
                return OptimizedExecutionResult(
                    success=False,
                    court_number=court_number,
                    error_message="Submit button not found"
                )
                
        except Exception as e:
            self.logger.error(f"Booking error: {e}")
            return OptimizedExecutionResult(
                success=False,
                court_number=court_number,
                error_message=str(e),
                execution_time=time.time() - start_time,
                phase_times=self.phase_times
            )