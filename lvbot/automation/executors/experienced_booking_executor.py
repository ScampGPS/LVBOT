"""
Experienced Booking Executor - Fast booking for frequent users
Based on working executor but with minimal delays
"""

import asyncio
import random
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from playwright.async_api import Page
import os
from .datetime_helpers import DateTimeHelpers

# Read production mode setting
PRODUCTION_MODE = os.getenv('PRODUCTION_MODE', 'true').lower() == 'true'

# Aggressive speed for experienced users
SPEED_MULTIPLIER = 3.0

async def take_screenshot_if_dev(page: Page, filename_prefix: str, court_number: int, logger: logging.Logger = None) -> Optional[str]:
    """Take screenshot only in development mode"""
    if PRODUCTION_MODE:
        if logger:
            logger.debug(f"Screenshot skipped in production mode: {filename_prefix}")
        return None
        
    try:
        screenshot_dir = os.path.join(os.path.dirname(__file__), '..', 'logs', 'screenshots')
        os.makedirs(screenshot_dir, exist_ok=True)
        screenshot_path = os.path.join(screenshot_dir, f'{filename_prefix}_court{court_number}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
        await page.screenshot(path=screenshot_path)
        if logger:
            logger.info(f"Screenshot saved: {screenshot_path}")
        return screenshot_path
    except Exception as e:
        if logger:
            logger.debug(f"Could not save screenshot: {e}")
        return None

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

async def find_time_slot_with_refresh(
    page: Page,
    time_slot: str,
    court_number: int,
    max_attempts: int = 5,
    refresh_delay: float = 1.5,
    logger: logging.Logger = None,
    target_datetime: Optional[datetime] = None
) -> Optional[object]:
    """
    Find time slot button, refreshing page if needed
    
    Args:
        page: Playwright page object
        time_slot: Target time (e.g., "10:00")
        court_number: Court number for logging
        max_attempts: Maximum refresh attempts
        refresh_delay: Delay between refreshes
        logger: Logger instance
        target_datetime: Target playing datetime to determine booking window
        
    Returns:
        Time button element or None if not found after max attempts
    """
    if not logger:
        logger = logging.getLogger('TimeSlotRefresher')
    
    # Check if we're in pre-window phase (30s before official opening)
    if target_datetime:
        booking_window_opens = DateTimeHelpers.get_booking_window_open_time(target_datetime, 48)
        current_time = datetime.now(target_datetime.tzinfo)
        
        # During the 30-second pre-window, continuously attempt booking without retry limit
        pre_window_attempts = 0
        while current_time < booking_window_opens:
            time_until_window = (booking_window_opens - current_time).total_seconds()
            
            # Log status
            if time_until_window <= 30:
                logger.info(f"Court {court_number}: PRE-WINDOW PHASE - Attempt #{pre_window_attempts + 1} "
                           f"({time_until_window:.1f}s until official window)")
                pre_window_attempts += 1
                
                # Try to find the time slot without counting as retry
                # First try the new selector format
                try:
                    time_button = await page.query_selector(f'button.time-selection:has(p:text("{time_slot}"))')
                    if time_button and await time_button.is_visible() and await time_button.is_enabled():
                        logger.info(f"Court {court_number}: TIME SLOT APPEARED EARLY! Found {time_slot} in pre-window")
                        logger.info(f"Court {court_number}: WAITING {time_until_window:.1f}s until official window to click...")
                        
                        # Wait until the official window opens
                        await asyncio.sleep(max(0, time_until_window))
                        
                        # Re-check the button is still there after waiting
                        if await time_button.is_visible() and await time_button.is_enabled():
                            logger.info(f"Court {court_number}: Window opened! Clicking {time_slot} now")
                            return time_button
                        else:
                            logger.warning(f"Court {court_number}: Button disappeared while waiting!")
                except:
                    pass
                
                # Then try text-based selectors
                for time_format in [time_slot, time_slot.replace(':00', '')]:
                    try:
                        time_button = await page.query_selector(f'button:has-text("{time_format}")')
                        if time_button and await time_button.is_visible() and await time_button.is_enabled():
                            logger.info(f"Court {court_number}: TIME SLOT APPEARED EARLY! Found {time_slot} in pre-window")
                            logger.info(f"Court {court_number}: WAITING {time_until_window:.1f}s until official window to click...")
                            
                            # Wait until the official window opens
                            await asyncio.sleep(max(0, time_until_window))
                            
                            # Re-check the button is still there after waiting
                            if await time_button.is_visible() and await time_button.is_enabled():
                                logger.info(f"Court {court_number}: Window opened! Clicking {time_slot} now")
                                return time_button
                            else:
                                logger.warning(f"Court {court_number}: Button disappeared while waiting!")
                    except:
                        pass
                
                # Quick refresh for next attempt
                try:
                    await page.reload(wait_until='domcontentloaded')
                    await asyncio.sleep(0.5)  # Quick 0.5s refresh during pre-window
                except Exception as e:
                    logger.debug(f"Pre-window refresh error: {e}")
                    await asyncio.sleep(0.5)
            else:
                # Too early, just wait
                logger.info(f"Court {court_number}: Waiting... Opens in {time_until_window:.0f}s")
                await asyncio.sleep(min(5.0, time_until_window - 30))
            
            current_time = datetime.now(target_datetime.tzinfo)
        
        logger.info(f"Court {court_number}: Booking window is now OFFICIALLY OPEN! Starting counted attempts...")
    
    attempt = 0
    
    # Time slot formats to try
    time_formats = [
        time_slot,                    # "10:00" - exact match for 24-hour format
        time_slot.replace(':00', ''), # "10" - sometimes displayed without minutes
    ]
    
    # Try the new selector first
    try:
        time_button = await page.query_selector(
            f'button.time-selection:has(p:text("{time_slot}"))'
        )
        if time_button and await time_button.is_visible() and await time_button.is_enabled():
            logger.info(f"Court {court_number}: Found {time_slot} using new selector")
            return time_button
    except:
        pass
    
    while attempt < max_attempts:
        attempt += 1
        logger.info(f"Court {court_number}: Attempt {attempt}/{max_attempts} to find {time_slot}")
        
        # Take screenshot for debugging (dev mode only)
        await take_screenshot_if_dev(page, f'time_search_attempt{attempt}', court_number, logger)
        
        # Try each format
        for time_format in time_formats:
            try:
                # Look for time button
                time_button = await page.query_selector(
                    f'button:has-text("{time_format}")'
                )
                
                if time_button:
                    # Verify button is visible and enabled
                    is_visible = await time_button.is_visible()
                    is_enabled = await time_button.is_enabled()
                    
                    if is_visible and is_enabled:
                        logger.info(f"Court {court_number}: Found {time_slot} (format: {time_format})")
                        return time_button
                    else:
                        logger.warning(f"Court {court_number}: Found {time_slot} but not clickable")
                        
            except Exception as e:
                logger.debug(f"Error checking format {time_format}: {e}")
        
        # If not found and not last attempt, refresh
        if attempt < max_attempts:
            logger.info(f"Court {court_number}: Time slot not found, refreshing page...")
            
            try:
                # Refresh the page
                await page.reload(wait_until='domcontentloaded')
                
                # Wait for time buttons to potentially load
                try:
                    await page.wait_for_selector(
                        'button.time-selection',  # Use the correct selector
                        timeout=5000,
                        state='visible'
                    )
                    # Give a moment for all buttons to load
                    await asyncio.sleep(0.5)
                except:
                    logger.debug("No time buttons found after wait")
                
                # Additional delay between refreshes
                await asyncio.sleep(refresh_delay)
                
            except Exception as e:
                logger.error(f"Court {court_number}: Refresh error: {e}")
                # Continue trying even if refresh fails
        
    logger.error(f"Court {court_number}: Could not find {time_slot} after {attempt} attempts")
    return None

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
            
            # Log current URL to debug navigation issues
            current_url = page.url
            self.logger.info(f"Current page URL: {current_url}")
            
            # Check if we're already on a booking form (datetime in URL)
            if '/datetime/' in current_url:
                self.logger.warning(f"UNEXPECTED: Already on booking form URL! Expected calendar page.")
                self.logger.warning(f"This suggests something navigated to a specific time slot before this executor ran.")
            
            # Minimal initial delay - experienced user knows the page
            delay = random.uniform(0.8, 1.2)
            self.logger.info(f"Minimal initial delay ({delay:.1f}s)")
            await asyncio.sleep(delay)
            
            # Quick mouse movement
            await minimal_mouse_movement(page)
            
            # Find time slot with refresh capability
            self.logger.info(f"Looking for {time_slot} time slot...")
            
            # Create target datetime with correct time for booking window calculation
            # Combine target date with the time slot to get the exact playing time
            time_parts = time_slot.split(':')
            hour = int(time_parts[0])
            minute = int(time_parts[1]) if len(time_parts) > 1 else 0
            
            # Handle both date and datetime objects
            if isinstance(target_date, datetime):
                target_datetime_with_time = target_date.replace(hour=hour, minute=minute)
            else:
                # If it's a date object, combine with time
                from datetime import time as dt_time
                target_datetime_with_time = datetime.combine(target_date, dt_time(hour, minute))
                # Preserve timezone if original datetime had one
                if hasattr(target_date, 'tzinfo') and target_date.tzinfo:
                    target_datetime_with_time = target_datetime_with_time.replace(tzinfo=target_date.tzinfo)
            
            # Find time slot with refresh
            time_button = await find_time_slot_with_refresh(
                page=page,
                time_slot=time_slot,
                court_number=court_number,
                max_attempts=5,
                refresh_delay=1.5,
                logger=self.logger,
                target_datetime=target_datetime_with_time
            )
            
            if not time_button:
                # Take screenshot when time slot not found (dev mode only)
                screenshot_path = await take_screenshot_if_dev(page, 'time_not_found', court_number, self.logger)
                if screenshot_path:
                    self.logger.error(f"Time slot not found - screenshot saved: {screenshot_path}")
                else:
                    self.logger.error(f"Time slot {time_slot} not found after refreshing")
                    
                return ExecutionResult(
                    success=False,
                    court_number=court_number,
                    error_message=f"Time slot {time_slot} not found after refreshing"
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
            try:
                await page.wait_for_selector('#client\\.firstName', timeout=10000)
                await asyncio.sleep(0.3)
                
                # Take screenshot of form (dev mode only)
                await take_screenshot_if_dev(page, 'booking_form', court_number, self.logger)
            except Exception as e:
                self.logger.error(f"Form wait failed: {e}")
                # Take error screenshot (dev mode only)
                await take_screenshot_if_dev(page, 'form_error', court_number, self.logger)
                raise
            
            self.logger.info("Booking form loaded!")
            
            # Fast form filling
            form_start = time.time()
            self.logger.info("Fast form filling (experienced user)...")
            
            # All fields with fast fill - check if pre-filled first
            firstName = await page.query_selector('#client\\.firstName')
            if firstName:
                current_first = await firstName.get_attribute('value') or ''
                expected_first = user_info.get('first_name', 'Test')
                if not current_first or current_first.strip() != expected_first:
                    await fast_fill(firstName, expected_first)
                else:
                    self.logger.info(f"First name already filled: {current_first}")
            
            lastName = await page.query_selector('#client\\.lastName')
            if lastName:
                current_last = await lastName.get_attribute('value') or ''
                expected_last = user_info.get('last_name', 'User')
                if not current_last or current_last.strip() != expected_last:
                    await fast_fill(lastName, expected_last)
                else:
                    self.logger.info(f"Last name already filled: {current_last}")
            
            phone = await page.query_selector('#client\\.phone')
            if phone:
                current_phone = await phone.get_attribute('value') or ''
                expected_phone = user_info.get('phone', '12345678')
                if not current_phone or current_phone.strip() != expected_phone:
                    await fast_fill(phone, expected_phone)
                else:
                    self.logger.info(f"Phone already filled: {current_phone}")
            
            email = await page.query_selector('#client\\.email')
            if email:
                # Check if email is already pre-filled with the correct value
                current_value = await email.get_attribute('value') or ''
                expected_email = user_info.get('email', 'test@example.com')
                
                # Only fill if empty or different from expected
                if not current_value or current_value.strip() != expected_email:
                    self.logger.info(f"Email field needs update: current='{current_value}', expected='{expected_email}'")
                    await fast_fill(email, expected_email)
                else:
                    self.logger.info(f"Email field already correctly filled with: {current_value}")
            
            form_time = time.time() - form_start
            self.logger.info(f"Form filled in {form_time:.1f} seconds")
            
            # Quick submit
            self.logger.info("Preparing submission...")
            await asyncio.sleep(0.2)
            
            submit_button = await page.query_selector('button:has-text("CONFIRMAR CITA")')
            if submit_button:
                self.logger.info("Submitting booking...")
                await submit_button.click()
                
                # Smart wait for confirmation page
                self.logger.info("Waiting for confirmation page...")
                try:
                    # Wait for either confirmation URL or confirmation text
                    await page.wait_for_function(
                        """() => {
                            // Check if URL contains confirmation
                            if (window.location.href.includes('/confirmation/')) return true;
                            
                            // Check if confirmation text appears
                            const pageText = document.body?.innerText || '';
                            if (pageText.toLowerCase().includes('confirmad')) return true;
                            if (pageText.toLowerCase().includes('confirmed')) return true;
                            
                            // Check for success icon or checkmark
                            const successElements = document.querySelectorAll('[class*="success"], [class*="confirm"], svg[class*="check"]');
                            if (successElements.length > 0) return true;
                            
                            return false;
                        }""",
                        timeout=10000  # 10 second timeout
                    )
                    
                    # Give a moment for any animations to complete
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    self.logger.warning(f"Confirmation wait timed out: {e}")
                
                # Now check result after page has loaded
                current_url = page.url
                self.logger.info(f"Post-submission URL: {current_url}")
                
                page_content = await page.content()
                
                # Log a preview of the page content for debugging
                text_preview = await page.evaluate('() => document.body?.innerText || ""')
                self.logger.info(f"Page text preview: {text_preview[:200]}...")
                
                confirmation_id = None
                if '/confirmation/' in current_url:
                    try:
                        confirmation_id = current_url.split('/confirmation/')[1].split('/')[0].split('?')[0]
                        self.logger.info(f"Extracted confirmation ID: {confirmation_id}")
                    except:
                        pass
                
                success_indicators = [
                    'confirmado' in page_content.lower(),
                    'confirmed' in page_content.lower(),
                    confirmation_id is not None
                ]
                
                self.logger.info(f"Success indicators: confirmado={success_indicators[0]}, confirmed={success_indicators[1]}, has_id={success_indicators[2]}")
                
                if any(success_indicators):
                    self.logger.info("BOOKING SUCCESSFUL!")
                    
                    # Take success screenshot (dev mode only)
                    await take_screenshot_if_dev(page, 'booking_success', court_number, self.logger)
                    
                    # Try to extract user name
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
                    # Take failure screenshot (dev mode only)
                    await take_screenshot_if_dev(page, 'booking_failed', court_number, self.logger)
                        
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
            # Take error screenshot (dev mode only)
            await take_screenshot_if_dev(page, 'booking_error', court_number, self.logger)
                
            return ExecutionResult(
                success=False,
                court_number=court_number,
                error_message=str(e)
            )
