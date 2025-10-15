"""
Async Booking Executor - Direct booking using AsyncBrowserPool
This bridges the gap between AsyncBrowserPool and booking execution
"""

import asyncio
import logging
import time
import random
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from lvbot.utils.acuity_booking_form import AcuityBookingForm
from lvbot.utils.async_browser_pool import AsyncBrowserPool
from lvbot.utils.tennis_executor import ExecutionResult
from lvbot.utils.acuity_page_validator import AcuityPageValidator
from lvbot.utils.time_order_extraction import AcuityTimeParser

logger = logging.getLogger(__name__)


class AsyncBookingExecutor:
    """Execute bookings directly using AsyncBrowserPool with progressive timeouts"""
    
    # Progressive timeout configuration
    TIMEOUTS = {
        'navigation': 15,       # 15 seconds for navigation operations
        'form_detection': 10,   # 10 seconds for form detection  
        'form_submission': 15,  # 15 seconds for form submission
        'health_check': 3,      # 3 seconds for browser health checks
        'total_execution': 60   # 60 seconds total execution limit (for complete natural flow)
    }
    
    def __init__(self, browser_pool: AsyncBrowserPool, use_javascript_forms=True, use_natural_flow=False):
        """
        Initialize with async browser pool
        
        Args:
            browser_pool: AsyncBrowserPool instance
            use_javascript_forms: If True, use JavaScript for form filling. If False, use native Playwright methods.
            use_natural_flow: If True, use natural human-like form filling. If False, use direct form filling.
        """
        self.browser_pool = browser_pool
        self.form_handler = AcuityBookingForm(use_javascript=use_javascript_forms)
        self.use_natural_flow = use_natural_flow  # NEW FEATURE FLAG
        self.logger = logger
    
    async def execute_booking(
        self, 
        court_number: int,
        time_slot: str,
        user_info: Dict[str, str],
        target_date: datetime
    ) -> ExecutionResult:
        """
        Execute a booking for a specific court and time with progressive timeouts
        
        Args:
            court_number: Court to book (1, 2, or 3)
            time_slot: Time to book (e.g., "10:00")
            user_info: User information dict with first_name, last_name, email, phone
            target_date: Date to book
            
        Returns:
            ExecutionResult with booking outcome
        """
        execution_start = time.time()
        
        try:
            # Set critical operation flag to prevent refresh during booking
            await self.browser_pool.set_critical_operation(True)
            
            # Enforce total execution timeout
            result = await asyncio.wait_for(
                self._execute_booking_internal(
                    court_number, time_slot, user_info, target_date
                ),
                timeout=self.TIMEOUTS['total_execution']
            )
            return result
            
        except asyncio.TimeoutError:
            execution_time = time.time() - execution_start
            error_msg = f"Booking execution timed out after {execution_time:.1f}s (limit: {self.TIMEOUTS['total_execution']}s)"
            self.logger.error(error_msg)
            
            return ExecutionResult(
                success=False,
                error_message=error_msg,
                court_attempted=court_number
            )
        except asyncio.CancelledError:
            execution_time = time.time() - execution_start
            self.logger.warning(f"Booking task was cancelled externally after {execution_time:.1f}s")
            raise  # Re-raise to maintain cancellation signal
        except Exception as e:
            execution_time = time.time() - execution_start
            self.logger.error(f"Booking execution failed after {execution_time:.1f}s: {e}", exc_info=True)
            
            return ExecutionResult(
                success=False,
                error_message=str(e),
                court_attempted=court_number
            )
        finally:
            # CRITICAL: Always clear the flag regardless of outcome
            try:
                await self.browser_pool.set_critical_operation(False)
                self.logger.info("Critical operation flag cleared")
            except Exception as cleanup_error:
                self.logger.error(f"Failed to clear critical operation flag: {cleanup_error}")
    
    async def _execute_booking_internal(
        self, 
        court_number: int,
        time_slot: str,
        user_info: Dict[str, str],
        target_date: datetime
    ) -> ExecutionResult:
        """
        Internal booking execution with detailed timeout handling
        """
        internal_start_time = time.time()  # Track time for internal execution
        
        try:
            # Check for cancellation at the start
            if asyncio.current_task().cancelled():
                self.logger.warning("Task already cancelled at start of internal execution")
                raise asyncio.CancelledError()
            # Validate browser pool health before proceeding  
            health_check_result = await self._validate_browser_pool_health(court_number)
            if not health_check_result['healthy']:
                return ExecutionResult(
                    success=False,
                    error_message=f"Browser pool health check failed: {health_check_result['error']}"
                )
            
            # Get the page for the specific court with health check
            page = await asyncio.wait_for(
                self.browser_pool.get_page(court_number),
                timeout=self.TIMEOUTS['health_check']
            )
            
            if not page:
                return ExecutionResult(
                    success=False,
                    error_message=f"Court {court_number} page not available"
                )
            
            # Double-check page connection health with timeout
            try:
                current_url = await asyncio.wait_for(
                    self._get_page_url_safely(page),
                    timeout=self.TIMEOUTS['health_check']
                )
                self.logger.info(f"Page connection healthy for Court {court_number}, current URL: {current_url}")
            except asyncio.TimeoutError:
                self.logger.error(f"Page health check timed out for Court {court_number}")
                return ExecutionResult(
                    success=False,
                    error_message=f"Court {court_number} page health check timed out"
                )
            except Exception as e:
                self.logger.error(f"Page connection test failed for Court {court_number}: {e}")
                return ExecutionResult(
                    success=False,
                    error_message=f"Court {court_number} page connection dead: {e}"
                )
            
            # Check for cancellation before starting navigation
            if asyncio.current_task().cancelled():
                self.logger.warning("Task cancelled before navigation")
                raise asyncio.CancelledError()
                
            self.logger.info(f"Starting booking: Court {court_number} at {time_slot} on {target_date}")
            
            # Check if we should use natural flow or traditional click method
            if self.use_natural_flow:
                self.logger.info(f"Starting natural browsing flow for Court {court_number}")
                
                # Natural navigation with progressive timeouts
                nav_start_time = time.time()
                
                try:
                    # Step 1: Navigate to the specific time slot using natural interaction
                    # Use total_execution timeout for natural flow (60s) instead of navigation timeout (15s)
                    success = await asyncio.wait_for(
                        self._navigate_to_time_slot_naturally(page, court_number, target_date, time_slot),
                        timeout=self.TIMEOUTS['total_execution'] - (time.time() - internal_start_time)  # Remaining time from total
                    )
                    
                    if not success:
                        return ExecutionResult(
                            success=False,
                            error_message=f"Failed to navigate to time slot naturally for Court {court_number}"
                        )
                    
                    navigation_time = time.time() - nav_start_time
                    self.logger.info(f"Natural navigation completed in {navigation_time:.2f}s")
                    
                    # Continue with the same page - we're already on the booking form
                    self.logger.info(f"✅ Continuing with current page for Court {court_number}")
                        
                except asyncio.TimeoutError:
                    navigation_time = time.time() - nav_start_time
                    error_msg = f"Navigation timed out after {navigation_time:.1f}s (limit: {self.TIMEOUTS['navigation']}s)"
                    self.logger.error(error_msg)
                    return ExecutionResult(
                        success=False,
                        error_message=error_msg
                    )
                except Exception as nav_error:
                    self.logger.error(f"Navigation failed: {nav_error}")
                    return ExecutionResult(
                        success=False,
                        error_message=f"Navigation failed: {nav_error}"
                    )
            else:
                # Use the PROVEN WORKING METHOD from court_booking_final.py
                self.logger.info(f"Using WORKING solution from court_booking_final.py for Court {court_number}")
                
                # Import and use the working executor
                from .working_booking_executor import WorkingBookingExecutor
                working_executor = WorkingBookingExecutor(self.browser_pool)
                
                # Delegate to the working executor
                working_result = await working_executor.execute_booking(
                    court_number=court_number,
                    target_date=target_date,
                    time_slot=time_slot,
                    user_info=user_info
                )
                
                # Convert WorkingExecutionResult to ExecutionResult
                if working_result.success:
                    return ExecutionResult(
                        success=True,
                        message=f"Successfully booked {time_slot} on Court {court_number}",
                        confirmation_url=working_result.confirmation_url,
                        confirmation_id=working_result.confirmation_id,
                        user_name=working_result.user_name
                    )
                else:
                    return ExecutionResult(
                        success=False,
                        error_message=working_result.error_message
                    )
            
            # The rest of this method is old code for natural flow - not used when use_natural_flow=False
            # Since we're using the working executor, we should never reach here
            return ExecutionResult(
                success=False,
                error_message="Unexpected: Reached unreachable code after working executor"
            )
                
                if not form_detected:
                    self.logger.warning("Form not immediately detected, proceeding with filling attempt")
                else:
                    self.logger.info("Form detected successfully")
                        
            except asyncio.TimeoutError:
                self.logger.warning("Page validation timed out, proceeding with form filling")
            except Exception as page_check_error:
                self.logger.error(f"Page check failed: {page_check_error}")
                return ExecutionResult(
                    success=False,
                    error_message=f"Page check failed: {page_check_error}"
                )
            
            # Check for cancellation before form filling (the longest operation)
            if asyncio.current_task().cancelled():
                self.logger.warning("Task cancelled before form filling")
                raise asyncio.CancelledError()
                
            # Skip form loading wait - form should be ready after time button click
            self.logger.info("🚀 Proceeding to form filling process")
            
            # Fill the booking form with updated field names
            self.logger.info("📝 Preparing user data for form filling...")
            user_data = {
                'client.firstName': user_info.get('first_name', ''),
                'client.lastName': user_info.get('last_name', ''),
                'client.phone': user_info.get('phone', ''),
                'client.email': user_info.get('email', '')
            }
            self.logger.info(f"📝 User data prepared: {list(user_data.keys())}")
            
            self.logger.info("🚀 Starting form filling process with timeout...")
            
            # Execute form filling - choose method based on feature flag
            try:
                if self.use_natural_flow:
                    # Use natural form flow (Phases 4-6 from working solution)
                    self.logger.info("🎯 Using natural form flow with 2.5x speed optimization")
                    success, message = await self._execute_natural_form_flow(page, {
                        'firstName': user_info.get('first_name', ''),
                        'lastName': user_info.get('last_name', ''),
                        'phone': user_info.get('phone', ''),
                        'email': user_info.get('email', '')
                    })
                else:
                    # Use existing direct form filling
                    self.logger.info("📝 Using direct form filling method")
                    success, message = await asyncio.wait_for(
                        self.form_handler.fill_booking_form(
                            page,
                            user_data,
                            wait_for_navigation=True
                        ),
                        timeout=self.TIMEOUTS['form_submission']
                    )
                    
                self.logger.info(f"📝 Form filling completed - Success: {success}, Message: {message[:100]}...")
                
            except asyncio.TimeoutError:
                error_msg = f"Form submission timed out after {self.TIMEOUTS['form_submission']}s"
                self.logger.error(error_msg)
                return ExecutionResult(
                    success=False,
                    error_message=error_msg
                )
            
            if not success:
                return ExecutionResult(
                    success=False,
                    error_message=message
                )
            
            # Check booking success with timeout
            try:
                booking_success, confirmation_msg = await asyncio.wait_for(
                    self.form_handler.check_booking_success(page),
                    timeout=self.TIMEOUTS['health_check']
                )
            except asyncio.TimeoutError:
                self.logger.warning("Booking success check timed out, assuming failure")
                booking_success = False
                confirmation_msg = "Booking success check timed out"
            
            if booking_success:
                self.logger.info(f"Booking successful: {confirmation_msg}")
                return ExecutionResult(
                    success=True,
                    court_reserved=court_number,
                    time_reserved=time_slot,
                    message=confirmation_msg
                )
            else:
                return ExecutionResult(
                    success=False,
                    error_message=confirmation_msg,
                    court_attempted=court_number
                )
                
        except asyncio.CancelledError:
            self.logger.warning(f"Internal booking execution cancelled for court {court_number}")
            raise  # Re-raise to propagate cancellation
        except Exception as e:
            self.logger.error(f"Internal booking error: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                error_message=f"Internal error: {str(e)}",
                court_attempted=court_number
            )
    
    async def _validate_browser_pool_health(self, court_number: int) -> Dict[str, Any]:
        """
        Validate browser pool health before booking execution
        
        Args:
            court_number: Court number to validate
            
        Returns:
            Dict with 'healthy' bool and 'error' message if unhealthy
        """
        try:
            # Check if browser pool is initialized
            if not self.browser_pool.browser:
                return {'healthy': False, 'error': 'Browser pool not initialized'}
            
            # Check if the specific court page exists
            if court_number not in self.browser_pool.pages:
                return {'healthy': False, 'error': f'Court {court_number} page not available'}
            
            # Quick connection test with timeout
            page = self.browser_pool.pages[court_number]
            if not page:
                return {'healthy': False, 'error': f'Court {court_number} page is None'}
            
            # Test page responsiveness
            try:
                await asyncio.wait_for(
                    page.evaluate('() => document.readyState'),
                    timeout=2.0
                )
            except:
                return {'healthy': False, 'error': f'Court {court_number} page unresponsive'}
            
            return {'healthy': True, 'error': None}
            
        except Exception as e:
            return {'healthy': False, 'error': f'Health check failed: {str(e)}'}
    
    async def _get_page_url_safely(self, page) -> str:
        """
        Safely get page URL with error handling
        
        Args:
            page: Playwright page object
            
        Returns:
            Page URL string
        """
        try:
            return page.url
        except Exception as e:
            self.logger.warning(f"Failed to get page URL: {e}")
            return "unknown"
    
    async def _quick_form_detection(self, page) -> bool:
        """
        Quick form detection without complex operations
        
        Args:
            page: Playwright page object
            
        Returns:
            True if form elements detected
        """
        try:
            # Look for any form field quickly
            form_fields = await page.query_selector_all('input[name*="client."]')
            return len(form_fields) > 0
        except Exception:
            return False
    
    def _apply_speed(self, base_delay: float) -> float:
        """
        Apply 2.5x speed multiplier for optimized natural flow
        
        Args:
            base_delay: Base delay in seconds
            
        Returns:
            Adjusted delay with speed optimization
        """
        return base_delay / 2.5
    
    async def _human_type_with_mistakes(self, page, selector: str, text: str) -> bool:
        """
        Type text naturally with occasional mistakes and corrections (2.5x speed optimized)
        
        Args:
            page: Playwright page object
            selector: CSS selector for input field
            text: Text to type
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Wait for element and focus
            element = await page.wait_for_selector(selector, timeout=5000)
            await element.focus()
            await asyncio.sleep(self._apply_speed(0.1))
            
            # Clear existing content
            await element.fill('')
            await asyncio.sleep(self._apply_speed(0.05))
            
            # Type with natural patterns (optimized speed)
            for i, char in enumerate(text):
                # Random mistake probability (reduced for speed)
                if random.random() < 0.03 and i > 2:  # 3% chance
                    # Type wrong character
                    wrong_char = random.choice('abcdefghijklmnopqrstuvwxyz')
                    await element.type(wrong_char)
                    await asyncio.sleep(self._apply_speed(random.uniform(0.05, 0.15)))
                    
                    # Quick correction
                    await page.keyboard.press('Backspace')
                    await asyncio.sleep(self._apply_speed(random.uniform(0.05, 0.1)))
                
                # Type correct character
                await element.type(char)
                await asyncio.sleep(self._apply_speed(random.uniform(0.02, 0.08)))
            
            # Brief pause after typing
            await asyncio.sleep(self._apply_speed(random.uniform(0.1, 0.3)))
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to type in {selector}: {e}")
            return False
    
    async def _natural_mouse_movement(self, page, selector: str) -> bool:
        """
        Move mouse naturally to element before clicking (2.5x speed optimized)
        
        Args:
            page: Playwright page object
            selector: CSS selector for target element
            
        Returns:
            True if successful, False otherwise
        """
        try:
            element = await page.wait_for_selector(selector, timeout=5000)
            box = await element.bounding_box()
            
            if box:
                # Calculate target position with slight randomness
                target_x = box['x'] + box['width'] / 2 + random.uniform(-10, 10)
                target_y = box['y'] + box['height'] / 2 + random.uniform(-5, 5)
                
                # Natural mouse movement (optimized speed)
                await page.mouse.move(target_x, target_y)
                await asyncio.sleep(self._apply_speed(random.uniform(0.05, 0.15)))
                
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Failed mouse movement to {selector}: {e}")
            return False
    
    async def _navigate_to_time_slot_naturally(self, page, court_number: int, target_date: datetime, time_slot: str) -> bool:
        """
        Navigate to a specific time slot using direct URL navigation
        
        Args:
            page: Playwright page object (already on court calendar page)
            court_number: Court number (1, 2, or 3)
            target_date: Target booking date
            time_slot: Time slot to book (e.g., "08:00")
            
        Returns:
            True if successful navigation, False otherwise
        """
        try:
            self.logger.info(f"🎯 Direct navigation to Court {court_number} time slot {time_slot}")
            
            # Format date for URL
            date_str = target_date.strftime("%Y-%m-%d")
            self.logger.info(f"📅 Target date: {date_str}")
            
            # Get appointment type ID based on court number
            appointment_type_ids = {
                1: "15970897",
                2: "16021953",
                3: "16120442"
            }
            
            appointment_type_id = appointment_type_ids.get(court_number)
            if not appointment_type_id:
                self.logger.error(f"Invalid court number: {court_number}")
                return False
            
            # Construct direct URL to the booking form
            # Format: /datetime/{date}T{time}:00-06:00?appointmentTypeIds[]={appointment_type_id}
            base_url = "https://clublavilla.as.me/schedule/7d558012/appointment"
            calendar_id = "4291312"  # This seems consistent across courts
            
            # Format the datetime part
            datetime_str = f"{date_str}T{time_slot}:00-06:00"
            
            # Construct the full URL
            direct_url = f"{base_url}/{appointment_type_id}/calendar/{calendar_id}/datetime/{datetime_str}?appointmentTypeIds[]={appointment_type_id}"
            
            self.logger.info(f"🚀 Navigating directly to: {direct_url}")
            
            # Simple direct navigation with minimal wait
            self.logger.info("🌐 Starting direct navigation...")
            try:
                # Navigate with domcontentloaded (faster than networkidle)
                await page.goto(direct_url, wait_until='domcontentloaded', timeout=8000)
                self.logger.info("✅ Navigation completed successfully")
            except Exception as e:
                self.logger.warning(f"⚠️ Navigation warning: {e} - continuing anyway")
            
            # Wait a moment for the form to load
            await asyncio.sleep(self._apply_speed(1.0))
            self.logger.info("✅ Post-navigation wait completed")
            
            # Check if we successfully navigated to the booking form
            current_url = page.url
            self.logger.info(f"📍 After navigation URL: {current_url}")
            
            # SUCCESS: If URL contains 'datetime' and the correct date, we've navigated successfully
            if '/datetime/' in current_url and date_str in current_url:
                self.logger.info("✅ Successfully navigated to booking form via direct URL")
                
                # Quick check for form fields to ensure we're on the right page
                try:
                    self.logger.info("🔍 Looking for form fields...")
                    form_element = await page.wait_for_selector('input[name*="client."]', timeout=5000)
                    if form_element:
                        self.logger.info("✅ Booking form detected")
                    else:
                        self.logger.warning("⚠️ Form selector returned null")
                except Exception as e:
                    self.logger.warning(f"⚠️ Form fields not immediately visible: {e}")
                
                return True
            else:
                self.logger.error(f"❌ Direct navigation failed - wrong URL: {current_url}")
                return False
            
        except Exception as e:
            self.logger.error(f"❌ Direct navigation failed: {e}", exc_info=True)
            
            # Fallback to clicking time slots on calendar page
            self.logger.info("🔄 Falling back to calendar click method...")
            
            # Step 3: Look for the time slot button (original approach)
            time_selectors = [
                f'button:has-text("{time_slot}")',
                f'[data-time="{time_slot}"]',
                f'.time-slot:has-text("{time_slot}")',
                f'.available-time:has-text("{time_slot}")',
                f'button[title*="{time_slot}"]'
            ]
            
            time_element = None
            found_selector = None
            
            # If we know the date section, try to find the time slot within that section first
            if date_section:
                self.logger.info(f"🔍 Looking for {time_slot} button in {date_section} section...")
                
                # First, try to find all time buttons and filter by section
                all_time_buttons = await page.query_selector_all(f'button:has-text("{time_slot}")')
                
                for button in all_time_buttons:
                    try:
                        # Check if this button is in the correct date section
                        is_in_section = await button.evaluate(f'''(element) => {{
                            // Look for parent section containing the date header
                            let parent = element.closest('div, section, article');
                            while (parent) {{
                                if (parent.textContent.includes('{date_section}')) {{
                                    return true;
                                }}
                                parent = parent.parentElement;
                            }}
                            return false;
                        }}''')
                        
                        if is_in_section and await button.is_visible():
                            time_element = button
                            found_selector = f'button:has-text("{time_slot}") in {date_section} section'
                            self.logger.info(f"✅ Found time slot {time_slot} in correct date section: {date_section}")
                            break
                    except Exception as e:
                        self.logger.debug(f"Error checking button section: {e}")
            
            # If not found in specific section, fall back to parallel search
            if not time_element:
                self.logger.info(f"⚠️ Could not find {time_slot} in {date_section} section, trying general search...")
                
                # OPTIMIZATION: Try all selectors in parallel instead of sequential (22s → 3s)
                async def try_selector(selector):
                    try:
                        element = await page.wait_for_selector(selector, timeout=3000)
                        if element and await element.is_visible():
                            return (selector, element)
                    except:
                        pass
                    return None
                
                # Run all selector searches in parallel
                tasks = [try_selector(selector) for selector in time_selectors]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Find the first successful result
                for result in results:
                    if result and not isinstance(result, Exception):
                        found_selector, time_element = result
                        self.logger.info(f"✅ Found clickable time slot with selector: {found_selector}")
                        break
            
            if not time_element:
                self.logger.error(f"❌ Could not find clickable time slot for {time_slot}")
                return False
            
            # Step 4: Ultra-fast click on time slot (63s → 3s)
            self.logger.info(f"🎯 Clicking on time slot {time_slot}")
            await self._natural_mouse_movement(page, found_selector)  # Use found selector directly
            await asyncio.sleep(self._apply_speed(0.1))  # Minimal hesitation
            
            # Click the time slot
            await time_element.click()
            
            # Step 5: Minimal wait for navigation (63s → 3s optimization)
            await asyncio.sleep(self._apply_speed(0.5))  # Just 0.5s wait
            
            # Quick URL check (skip expensive form detection)
            current_url = page.url
            self.logger.info(f"📍 After time slot click URL: {current_url}")
            
            # SUCCESS: If URL contains 'datetime', we've navigated successfully
            if '/datetime/' in current_url or 'appointmentTypeIds' in current_url:
                self.logger.info("✅ Successfully navigated to booking form (URL-based detection)")
                return True
            
            # Fallback: Quick single form check if URL detection fails
            try:
                form_element = await page.wait_for_selector('input[name*="client."]', timeout=1000)
                if form_element:
                    self.logger.info("✅ Booking form detected via fallback")
                    return True
            except:
                pass
            
            self.logger.warning("⚠️ Form not detected but proceeding anyway")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Natural navigation failed: {e}", exc_info=True)
            return False

    async def _execute_natural_form_flow(self, page, form_data: Dict[str, str]) -> Tuple[bool, str]:
        """
        Execute natural form filling workflow with 2.5x speed optimization
        
        Args:
            page: Playwright page object
            form_data: Dictionary with firstName, lastName, phone, email
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            self.logger.info("🎯 Starting natural form flow (Phase 4: Form Detection)")
            
            # Phase 4: Enhanced Form Detection with optimized timing
            form_selectors = {
                'firstName': 'input[name="client.firstName"]',
                'lastName': 'input[name="client.lastName"]',
                'phone': 'input[name="client.phone"]',
                'email': 'input[name="client.email"]'
            }
            
            # Wait for form to be ready (optimized timing)
            await asyncio.sleep(self._apply_speed(1.0))
            
            # Verify all form fields are present
            missing_fields = []
            for field_name, selector in form_selectors.items():
                try:
                    await page.wait_for_selector(selector, timeout=3000)
                    self.logger.info(f"✅ Form field found: {field_name}")
                except Exception:
                    missing_fields.append(field_name)
                    self.logger.warning(f"❌ Form field missing: {field_name}")
            
            if missing_fields:
                return False, f"Missing form fields: {missing_fields}"
            
            self.logger.info("🎯 All form fields detected, starting Phase 5: Natural Form Filling")
            
            # Phase 5: Natural Form Filling with optimized speed
            form_fill_sequence = [
                ('firstName', form_data.get('firstName', '')),
                ('lastName', form_data.get('lastName', '')),
                ('email', form_data.get('email', '')),
                ('phone', form_data.get('phone', ''))
            ]
            
            for field_name, value in form_fill_sequence:
                if not value:
                    self.logger.warning(f"Skipping empty field: {field_name}")
                    continue
                    
                selector = form_selectors[field_name]
                self.logger.info(f"📝 Filling {field_name}: {value}")
                
                # Natural mouse movement and typing
                await self._natural_mouse_movement(page, selector)
                success = await self._human_type_with_mistakes(page, selector, value)
                
                if not success:
                    return False, f"Failed to fill field: {field_name}"
                
                # Brief pause between fields (optimized)
                await asyncio.sleep(self._apply_speed(random.uniform(0.2, 0.5)))
            
            self.logger.info("🎯 Form filling complete, starting Phase 6: Natural Submission")
            
            # Phase 6: Natural Submission Process with optimized timing
            # Look for submit button
            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Schedule")',
                'button:has-text("Book")',
                'button:has-text("Confirm")',
                '.acuity-btn-primary'
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = await page.wait_for_selector(selector, timeout=2000)
                    if submit_button:
                        self.logger.info(f"✅ Submit button found: {selector}")
                        break
                except Exception:
                    continue
            
            if not submit_button:
                return False, "Submit button not found"
            
            # Natural submission flow (optimized)
            await self._natural_mouse_movement(page, submit_selectors[0])  # Move to found selector
            await asyncio.sleep(self._apply_speed(random.uniform(0.2, 0.5)))
            
            # Click submit
            self.logger.info("🎯 Clicking submit button")
            await submit_button.click()
            
            # Wait for response (optimized timing)
            await asyncio.sleep(self._apply_speed(2.0))
            
            # Check for success indicators
            current_url = page.url
            self.logger.info(f"📍 Post-submission URL: {current_url}")
            
            if 'confirmation' in current_url.lower():
                return True, "✅ Booking confirmed via URL detection"
            
            # Check for success text
            success_indicators = [
                'confirmada',
                'confirmed',
                'success',
                'scheduled'
            ]
            
            page_content = await page.content()
            for indicator in success_indicators:
                if indicator.lower() in page_content.lower():
                    return True, f"✅ Booking confirmed via text detection: {indicator}"
            
            return True, "✅ Natural form flow completed successfully"
            
        except Exception as e:
            self.logger.error(f"Natural form flow failed: {e}", exc_info=True)
            return False, f"Natural form flow error: {str(e)}"
    
