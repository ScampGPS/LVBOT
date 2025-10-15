"""
Smart Async Booking Executor with Progressive Timeout and Retry Logic
=====================================================================

PURPOSE: Enhanced booking executor with smart timeout management and retry capability
FEATURES: 
  - Progressive timeout extension based on loading progress
  - Automatic retry on timeout with exponential backoff
  - Detailed progress monitoring for debugging
  - Graceful degradation on failures
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Set
from datetime import datetime
import pytz

from lvbot.automation.forms.acuity_booking_form import AcuityBookingForm
from lvbot.automation.browser.async_browser_pool import AsyncBrowserPool
from lvbot.automation.executors.tennis_executor import ExecutionResult
from lvbot.infrastructure.constants import BrowserTimeouts

logger = logging.getLogger(__name__)


class SmartAsyncBookingExecutor:
    """Execute bookings with smart timeout management and retry logic"""
    
    # Timeout configuration
    BASE_TIMEOUT = 15.0  # 15 seconds base
    EXTENSION_TIMEOUT = 10.0  # 10 seconds per extension
    MAX_EXTENSIONS = 6  # Max 6 extensions = 75s total
    MAX_RETRIES = 10  # Maximum booking retry attempts
    POST_TARGET_DELAY = 2.0  # Delay between retries after target time passes
    
    # Phase-based timeout configuration
    PHASE_TIMEOUTS = {
        'initial': 1.5,           # Base timeout
        'document_response': 1.5,  # Document loaded
        'resources_loading': 1.5,  # CSS/JS loading
        'dom_ready': 2.0,         # DOM ready, form should appear
        'form_check': 1.5,        # Final form check window
        'form_detected': 2.0      # Form interaction ready
    }
    
    def __init__(self, browser_pool: AsyncBrowserPool):
        """
        Initialize with async browser pool
        
        Args:
            browser_pool: AsyncBrowserPool instance
        """
        self.browser_pool = browser_pool
        self.form_handler = AcuityBookingForm(use_javascript=True)  # Default to JavaScript for now
        self.logger = logger
    
    async def execute_booking_with_retry(
        self, 
        court_number: int,
        time_slot: str,
        user_info: Dict[str, str],
        target_date: datetime
    ) -> ExecutionResult:
        """
        Execute booking with automatic retry on failure
        
        Args:
            court_number: Court to book (1, 2, or 3)
            time_slot: Time to book (e.g., "10:00", "18:15")
            user_info: User information dict
            target_date: Date to book
            
        Returns:
            ExecutionResult with booking outcome
        """
        # Wrap entire retry loop in a timeout
        try:
            return await asyncio.wait_for(
                self._execute_booking_with_retry_internal(court_number, time_slot, user_info, target_date),
                timeout=85  # 85 seconds total, leaves 5s buffer for scheduler
            )
        except asyncio.TimeoutError:
            self.logger.error(f"Booking executor timed out after 85 seconds for Court {court_number} at {time_slot}")
            # Create a failed result
            return ExecutionResult(
                success=False,
                error_message="Booking executor timed out after 85 seconds",
                court_reserved=None,
                time_reserved=None,
                details={}
            )
    
    async def _execute_booking_with_retry_internal(
        self, 
        court_number: int,
        time_slot: str,
        user_info: Dict[str, str],
        target_date: datetime
    ) -> ExecutionResult:
        """
        Internal retry logic implementation
        """
        last_error = None
        
        # Parse target time for comparison (in Mexico City timezone)
        mexico_tz = pytz.timezone('America/Mexico_City')
        hour, minute = map(int, time_slot.split(':'))
        
        # Make target_date timezone-aware if it isn't already
        if target_date.tzinfo is None:
            target_date = mexico_tz.localize(target_date)
        
        target_datetime = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        for attempt in range(self.MAX_RETRIES):
            current_time = datetime.now(mexico_tz)
            self.logger.info(f"Booking attempt {attempt + 1}/{self.MAX_RETRIES} for Court {court_number} at {time_slot}")
            self.logger.info(f"Current time: {current_time.strftime('%H:%M:%S')} MX, Target time: {time_slot}:00")
            
            try:
                result = await self._execute_booking_with_smart_timeout(
                    court_number, time_slot, user_info, target_date
                )
                
                if result.success:
                    self.logger.info(f"Booking successful on attempt {attempt + 1}")
                    return result
                
                # Check if error is retryable
                error_msg = result.error_message or ""
                if "not available" in error_msg.lower() or "unavailable" in error_msg.lower():
                    # Time slot genuinely not available, no point retrying
                    self.logger.warning(f"Time slot {time_slot} not available, not retrying")
                    return result
                
                last_error = result.error_message
                
                # Determine retry delay
                if attempt < self.MAX_RETRIES - 1:
                    current_time = datetime.now(mexico_tz)
                    
                    # If we're before the target time, retry immediately
                    if current_time < target_datetime:
                        self.logger.warning(f"Attempt {attempt + 1} failed: {last_error}. Retrying immediately (before target time)...")
                        await asyncio.sleep(0.1)  # Tiny delay to prevent CPU spinning
                    else:
                        # After target time, use fixed delay
                        self.logger.warning(f"Attempt {attempt + 1} failed: {last_error}. Retrying in {self.POST_TARGET_DELAY}s (after target time)...")
                        await asyncio.sleep(self.POST_TARGET_DELAY)
                    
            except Exception as e:
                last_error = str(e)
                self.logger.error(f"Attempt {attempt + 1} failed with exception: {e}")
                
                if attempt < self.MAX_RETRIES - 1:
                    current_time = datetime.now(mexico_tz)
                    
                    if current_time < target_datetime:
                        await asyncio.sleep(0.1)  # Immediate retry before target time
                    else:
                        await asyncio.sleep(self.POST_TARGET_DELAY)
        
        # All retries failed
        return ExecutionResult(
            success=False,
            error_message=f"Failed after {self.MAX_RETRIES} attempts. Last error: {last_error}",
            court_attempted=court_number
        )
    
    async def _execute_booking_with_smart_timeout(
        self,
        court_number: int,
        time_slot: str,
        user_info: Dict[str, str],
        target_date: datetime
    ) -> ExecutionResult:
        """
        Execute booking with smart timeout management
        """
        # Set critical operation flag
        await self.browser_pool.set_critical_operation(True)
        
        try:
            
            # Get the page for the specific court with health check
            page = await self.browser_pool.get_page(court_number)
            if not page:
                return ExecutionResult(
                    success=False,
                    error_message=f"Court {court_number} page not available"
                )
            
            # Double-check page connection health before proceeding
            try:
                current_url = page.url  # This will fail if connection is dead
                self.logger.info(f"Page connection healthy for Court {court_number}, current URL: {current_url}")
            except Exception as connection_error:
                self.logger.warning(f"Court {court_number} page connection is dead: {connection_error}. Recreating...")
                # Recreate the page connection
                page = await self.browser_pool.get_page(court_number)
                if not page:
                    return ExecutionResult(
                        success=False,
                        error_message=f"Court {court_number} page recreation failed"
                    )
                current_url = page.url
                self.logger.info(f"✅ Court {court_number} page recreated successfully")
            
            self.logger.info(f"Starting smart booking: Court {court_number} at {time_slot} on {target_date}")
            
            # Construct direct URL to booking form
            court_urls = {
                1: "https://clublavilla.as.me/schedule/7d558012/appointment/15970897/calendar/4282490",
                2: "https://clublavilla.as.me/schedule/7d558012/appointment/16021953/calendar/4291312", 
                3: "https://clublavilla.as.me/schedule/7d558012/appointment/16120442/calendar/4307254"
            }
            
            date_str = target_date.strftime("%Y-%m-%d")
            appointment_type_id = court_urls[court_number].split('/appointment/')[1].split('/')[0]
            direct_url = f"{court_urls[court_number]}/datetime/{date_str}T{time_slot}:00-06:00?appointmentTypeIds[]={appointment_type_id}"
            
            # Check if we're already on the target URL
            if current_url == direct_url:
                self.logger.info("Already on target URL, skipping navigation and checking for form")
                # Skip problematic refresh - just check for form directly
                navigation_result = await self._navigate_with_smart_timeout(page, direct_url, skip_navigation=True)
                
                if not navigation_result['success']:
                    return ExecutionResult(
                        success=False,
                        error_message=navigation_result['error']
                    )
            else:
                self.logger.info(f"Navigating to: {direct_url}")
                
                # Execute navigation with smart timeout
                navigation_result = await self._navigate_with_smart_timeout(page, direct_url)
                
                if not navigation_result['success']:
                    return ExecutionResult(
                        success=False,
                        error_message=navigation_result['error']
                    )
            
            # Check if form was detected (common for both paths)
            if not navigation_result.get('form_ready', False):
                reason = navigation_result.get('reason', 'unknown')
                if reason == 'no_form_after_dom_ready':
                    self.logger.info(f"Time slot {time_slot} appears unavailable - no booking form found")
                    await self.browser_pool.set_critical_operation(False)
                    return ExecutionResult(
                        success=False,
                        error_message=f"Time slot {time_slot} not available - no booking form",
                        court_attempted=court_number
                    )
                elif reason == 'unavailable_message_found':
                    self.logger.info(f"Time slot {time_slot} explicitly marked as unavailable")
                    await self.browser_pool.set_critical_operation(False)
                    return ExecutionResult(
                        success=False,
                        error_message=f"Time slot {time_slot} not available",
                        court_attempted=court_number
                    )
            
            # Only wait if form was detected (no need to wait if unavailable)
            if navigation_result.get('form_ready', False):
                # Brief wait for form to be fully interactive
                await page.wait_for_timeout(500)
            
            # Recreate page connection after navigation to avoid hangs (critical fix)
            self.logger.info("Recreating page connection after navigation to ensure stability...")
            try:
                fresh_page = await self.browser_pool.get_page(court_number)
                page = fresh_page
                self.logger.info("✅ Using fresh page connection for form filling")
            except Exception as e:
                self.logger.warning(f"Page recreation failed: {e}, proceeding with existing page")
            
            # Fill the booking form
            user_data = {
                'client.firstName': user_info.get('first_name', ''),
                'client.lastName': user_info.get('last_name', ''),
                'client.phone': user_info.get('phone', ''),
                'client.email': user_info.get('email', '')
            }
            
            success, message = await self.form_handler.fill_booking_form(
                page,
                user_data,
                wait_for_navigation=True
            )
            
            if not success:
                await self.browser_pool.set_critical_operation(False)
                return ExecutionResult(
                    success=False,
                    error_message=message
                )
            
            # Check booking success
            booking_success, confirmation_msg = await self.form_handler.check_booking_success(page)
            
            # Navigate back to court page for next booking
            await self._navigate_back_to_court_page(page, court_number)
            
            await self.browser_pool.set_critical_operation(False)
            
            if booking_success:
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
                
        except Exception as e:
            self.logger.error(f"Booking error: {e}", exc_info=True)
            
            # Try to navigate back to court page even on error
            try:
                await self._navigate_back_to_court_page(page, court_number)
            except:
                pass
                
            return ExecutionResult(
                success=False,
                error_message=str(e),
                court_attempted=court_number
            )
        finally:
            # Always clear critical operation flag
            try:
                await self.browser_pool.set_critical_operation(False)
            except Exception as e:
                self.logger.warning(f"Failed to clear critical operation flag: {e}")
    
    async def _navigate_with_smart_timeout(self, page, url: str, skip_navigation: bool = False) -> Dict[str, Any]:
        """
        Navigate with smart timeout that extends based on progress
        
        Args:
            page: Playwright page object
            url: Target URL to navigate to
            skip_navigation: If True, skip the actual navigation and just check form availability
        
        Returns:
            Dict with success status and error message if failed
        """
        start_time = time.time()
        active_requests: Set[str] = set()
        last_progress_time = start_time
        timeout_extensions = 0
        progress_events = []
        
        # Phase tracking
        current_phase = 'initial'
        phase_start_time = start_time
        current_timeout = self.PHASE_TIMEOUTS['initial']
        total_timeout = current_timeout
        dom_ready = False
        document_received = False
        core_resources_loading = False
        
        def log_progress(event: str):
            nonlocal last_progress_time
            elapsed = time.time() - start_time
            progress_events.append((elapsed, event))
            self.logger.debug(f"Navigation progress at {elapsed:.1f}s: {event}")
            last_progress_time = time.time()
        
        # Track network activity
        def on_request(request):
            active_requests.add(request.url)
            log_progress(f"Request: {request.url[:50]}...")
        
        def on_response(response):
            nonlocal document_received, core_resources_loading, current_phase, total_timeout
            
            if response.url in active_requests:
                active_requests.remove(response.url)
            log_progress(f"Response {response.status}: {response.url[:50]}...")
            
            # Phase detection
            if response.url == url and not document_received:
                document_received = True
                current_phase = 'document_response'
                total_timeout += self.PHASE_TIMEOUTS['document_response']
                log_progress(f"PHASE: Document response - extending timeout by {self.PHASE_TIMEOUTS['document_response']}s")
            
            # Detect core resources
            if not core_resources_loading and any(resource in response.url for resource in ['main.css', 'main.js', 'main.es']):
                core_resources_loading = True
                current_phase = 'resources_loading'
                total_timeout += self.PHASE_TIMEOUTS['resources_loading']
                log_progress(f"PHASE: Core resources loading - extending timeout by {self.PHASE_TIMEOUTS['resources_loading']}s")
        
        def on_domcontentloaded():
            nonlocal dom_ready, current_phase, total_timeout
            dom_ready = True
            current_phase = 'dom_ready'
            total_timeout += self.PHASE_TIMEOUTS['dom_ready']
            log_progress(f"PHASE: DOM Ready - extending timeout by {self.PHASE_TIMEOUTS['dom_ready']}s for form appearance")
        
        def on_load():
            log_progress("Page Load Event")
        
        # Attach event listeners
        page.on("request", on_request)
        page.on("response", on_response)
        page.on("domcontentloaded", on_domcontentloaded)
        page.on("load", on_load)
        
        try:
            # Start navigation task or skip if we're already on the page
            if skip_navigation:
                # Create a dummy completed task since we're skipping navigation
                async def dummy_navigation():
                    return None
                navigation_task = asyncio.create_task(dummy_navigation())
                log_progress("Skipped navigation - already on target page")
                dom_ready = True  # Assume DOM is ready since we're already on the page
                document_received = True
            else:
                # Setup event-driven navigation to bypass Playwright hanging
                dom_ready_event = asyncio.Event()
                
                def on_dom_ready():
                    dom_ready_time = time.time() - start_time
                    self.logger.info(f"[SMART NAV] DOM ready at {dom_ready_time:.2f}s")
                    dom_ready_event.set()
                
                # Attach event listener
                page.on('domcontentloaded', on_dom_ready)
                
                try:
                    # Start navigation with minimal wait condition
                    navigation_task = asyncio.create_task(
                        page.goto(url, wait_until='commit', timeout=5000)  # 5s timeout
                    )
                    
                    # Wait for DOM ready event with timeout
                    try:
                        await asyncio.wait_for(dom_ready_event.wait(), timeout=15)
                        dom_ready = True
                        document_received = True
                        self.logger.info(f"[SMART NAV] DOM ready detected via event")
                        
                        # Try to wait for navigation task completion, but don't block
                        try:
                            await asyncio.wait_for(navigation_task, timeout=2.0)
                        except asyncio.TimeoutError:
                            # Navigation hanging, cancel and proceed
                            self.logger.warning(f"[SMART NAV] Navigation task hanging, proceeding anyway")
                            navigation_task.cancel()
                            
                    except asyncio.TimeoutError:
                        # DOM never loaded
                        self.logger.error(f"[SMART NAV] DOM never loaded after 15s")
                        navigation_task.cancel()
                        return {
                            'success': False,
                            'response': None,
                            'time': time.time() - start_time,
                            'extensions': 0,
                            'form_ready': False,
                            'reason': 'dom_load_timeout'
                        }
                        
                finally:
                    # Clean up event listener
                    try:
                        page.remove_listener('domcontentloaded', on_dom_ready)
                    except:
                        pass
                
                # Skip the monitoring loop since we handled navigation above
                navigation_task = asyncio.create_task(asyncio.sleep(0))  # Dummy completed task
            
            # Monitor progress with phase-based smart timeout
            form_detected = False
            form_check_started = False
            
            while not navigation_task.done():
                await asyncio.sleep(0.1)  # Check more frequently
                
                elapsed = time.time() - start_time
                
                # Phase-based timeout check
                if elapsed > total_timeout:
                    # If DOM is ready and we're past form check window, assume unavailable
                    if dom_ready and current_phase in ['dom_ready', 'form_check']:
                        self.logger.info(f"No form detected after {elapsed:.1f}s (phase: {current_phase}) - slot likely unavailable")
                        navigation_task.cancel()
                        return {
                            'success': True,  # Navigation succeeded
                            'response': None,
                            'time': elapsed,
                            'extensions': 0,
                            'form_ready': False,
                            'reason': 'no_form_after_dom_ready'
                        }
                    else:
                        self.logger.error(f"Navigation timeout at phase '{current_phase}' after {elapsed:.1f}s")
                        navigation_task.cancel()
                        return {
                            'success': False,
                            'error': f'Navigation timeout at phase {current_phase} after {elapsed:.1f}s'
                        }
                
                # Form detection check
                try:
                    if not form_detected:
                        # Check for Acuity booking form fields
                        form_fields = await page.locator('input[name="client.firstName"], input[name="client.lastName"]').count()
                        if form_fields > 0:
                            log_progress("PHASE: Form detected!")
                            form_detected = True
                            current_phase = 'form_detected'
                            total_timeout += self.PHASE_TIMEOUTS['form_detected']
                            # Give form time to be interactive
                            if elapsed > 2:  # Minimum time for stability
                                self.logger.info(f"Form ready after {elapsed:.1f}s")
                                await asyncio.sleep(0.5)  # Brief wait for form readiness
                                break
                    
                    # Start form check phase after DOM ready
                    if dom_ready and not form_check_started and elapsed > (phase_start_time + self.PHASE_TIMEOUTS['dom_ready'] - 0.5):
                        form_check_started = True
                        current_phase = 'form_check'
                        total_timeout += self.PHASE_TIMEOUTS['form_check']
                        log_progress(f"PHASE: Form check window - final {self.PHASE_TIMEOUTS['form_check']}s to detect form")
                    
                    # Check for unavailable indicators
                    unavailable = await page.locator('.unavailable-message, [data-unavailable="true"], .no-availability').count()
                    if unavailable > 0:
                        log_progress("Unavailable indicator detected")
                        return {
                            'success': True,
                            'response': None,
                            'time': elapsed,
                            'extensions': 0,
                            'form_ready': False,
                            'reason': 'unavailable_message_found'
                        }
                except:
                    pass
            
            # Get result if not already broken out
            if not navigation_task.done():
                response = await navigation_task
            else:
                try:
                    response = navigation_task.result()
                except:
                    response = None
                    
            elapsed_time = time.time() - start_time
            self.logger.info(f"Navigation completed in {elapsed_time:.1f}s with {timeout_extensions} extensions")
            
            # Clean up event listeners
            page.remove_listener("request", on_request)
            page.remove_listener("response", on_response)
            page.remove_listener("domcontentloaded", on_domcontentloaded)
            page.remove_listener("load", on_load)
            
            # Quick final check for form availability
            if form_detected:
                try:
                    # Wait a bit for form to be fully interactive
                    await page.wait_for_selector('input[name="client.firstName"]', state='visible', timeout=5000)
                    self.logger.info("Form is visible and ready for interaction")
                except:
                    self.logger.warning("Form detected but not yet visible")
            
            return {
                'success': True,
                'response': response,
                'time': elapsed_time,
                'extensions': timeout_extensions,
                'form_ready': form_detected
            }
            
        except asyncio.CancelledError:
            return {
                'success': False,
                'error': 'Navigation cancelled'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _navigate_back_to_court_page(self, page, court_number: int):
        """
        Navigate back to the base court page after booking attempt
        
        Args:
            page: Page instance
            court_number: Court number (1, 2, or 3)
        """
        court_urls = {
            1: "https://clublavilla.as.me/schedule/7d558012/appointment/15970897/calendar/4282490",
            2: "https://clublavilla.as.me/schedule/7d558012/appointment/16021953/calendar/4291312", 
            3: "https://clublavilla.as.me/schedule/7d558012/appointment/16120442/calendar/4307254"
        }
        
        base_url = court_urls.get(court_number)
        if not base_url:
            return
        
        current_url = page.url
        # Only navigate if we're not already on the base court page
        if not current_url.startswith(base_url) or 'datetime' in current_url:
            try:
                self.logger.info(f"Navigating back to court {court_number} base page")
                
                # Use event-driven navigation to avoid hanging
                nav_dom_ready = asyncio.Event()
                def on_nav_dom_ready():
                    nav_dom_ready.set()
                
                page.on('domcontentloaded', on_nav_dom_ready)
                
                try:
                    nav_task = asyncio.create_task(
                        page.goto(base_url, wait_until='commit', timeout=5000)
                    )
                    
                    # Wait for DOM or timeout
                    await asyncio.wait_for(nav_dom_ready.wait(), timeout=10)
                    
                    # Try to complete navigation task
                    try:
                        await asyncio.wait_for(nav_task, timeout=2.0)
                    except asyncio.TimeoutError:
                        nav_task.cancel()
                        
                finally:
                    try:
                        page.remove_listener('domcontentloaded', on_nav_dom_ready)
                    except:
                        pass
                        
                self.logger.info(f"Successfully navigated back to court {court_number} page")
            except Exception as e:
                self.logger.warning(f"Failed to navigate back to court page: {e}")