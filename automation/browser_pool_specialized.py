#!/usr/bin/env python3
"""
Specialized Browser Pool - One Browser Per Court
Each browser is pre-positioned on a specific court for instant booking
"""

import threading
import time
import logging
import queue
import asyncio
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Frame, Playwright

from lvbot.infrastructure.constants import (
    BOOKING_URL, DEFAULT_BROWSER_POOL_SIZE, MAX_BROWSER_AGE_MINUTES,
    MAX_BROWSER_USES, BROWSER_HEALTH_CHECK_INTERVAL, SCHEDULING_IFRAME_URL_PATTERN,
    court_number_to_index, AVAILABLE_COURT_NUMBERS, DEFAULT_COURT_PREFERENCES,
    FAST_POLL_INTERVAL, DEFAULT_WAIT_INTERVAL, RESERVATION_RETRY_DELAY,
    MAX_SINGLE_COURT_CHECK_TIME, MAX_NAVIGATION_WAIT_TIME, TARGET_AVAILABILITY_CHECK_TIME
)
from lvbot.automation.forms.acuity_booking_form import AcuityBookingForm

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@dataclass
class SpecializedBrowser:
    """Browser instance specialized for a specific court"""
    browser: Browser
    context: BrowserContext
    page: Page
    court_number: int  # 1, 2, or 3 (human-readable)
    court_index: int   # 0, 1, or 2 (for clicking)
    is_positioned: bool = False
    is_healthy: bool = True
    created_at: datetime = None
    last_used: datetime = None
    use_count: int = 0
    id: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.last_used is None:
            self.last_used = datetime.now()
        if self.id is None:
            self.id = f"court{self.court_number}_{int(time.time() * 1000)}"


class SpecializedBrowserPool:
    """
    Maintains persistent specialized browsers for tennis court bookings
    Supports dynamic court switching with 2-browser limit for GCE
    """
    
    def __init__(self, 
                 courts_needed: List[int] = None,  # Which courts to create browsers for
                 headless: bool = True,
                 booking_url: str = BOOKING_URL,
                 max_age_minutes: int = MAX_BROWSER_AGE_MINUTES,
                 max_uses: int = MAX_BROWSER_USES,
                 low_resource_mode: bool = True,  # Enable for GCE
                 persistent: bool = True,  # Keep browsers alive between bookings
                 max_browsers: int = 2):  # Maximum concurrent browsers (GCE optimized)
        
        self.logger = logging.getLogger('SpecializedBrowserPool')
        self.logger.debug(f"Initializing SpecializedBrowserPool with: courts_needed={courts_needed}, "
                         f"headless={headless}, low_resource_mode={low_resource_mode}, "
                         f"persistent={persistent}, max_browsers={max_browsers}")
        
        self.courts_needed = courts_needed or DEFAULT_COURT_PREFERENCES[:2]  # Default to first two preferred courts
        self.headless = headless
        self.booking_url = booking_url
        self.max_age = timedelta(minutes=max_age_minutes)
        self.max_uses = max_uses
        self.low_resource_mode = low_resource_mode
        self.persistent = persistent
        self.max_browsers = max_browsers
        
        # Browser storage - now by ID, not court
        self.browsers: Dict[str, SpecializedBrowser] = {}  # browser_id -> browser
        self.lock = threading.Lock()
        
        # Court management
        from lvbot.utils.court_pool_manager import CourtPoolManager
        from lvbot.utils.browser_court_switcher import BrowserCourtSwitcher
        self.court_manager = CourtPoolManager(primary_courts=courts_needed[:2], fallback_court=2)
        self.court_switcher = BrowserCourtSwitcher(booking_url)
        
        # Direct Playwright instance for browser creation
        # We manage our own instance to avoid thread-local issues
        self.playwright_instance: Optional[Playwright] = None
        
        # Control flags
        self.running = False
        self.maintenance_thread: Optional[threading.Thread] = None
        
        # Readiness tracking
        self._ready_event = asyncio.Event() # Changed to asyncio.Event
        self._initialization_error: Optional[str] = None
        
        # Statistics
        self.stats = {
            'browsers_created': 0,
            'browsers_recycled': 0,
            'positioning_failures': 0,
            'total_bookings': 0,
            'successful_bookings': 0
        }
        
        self.logger = logging.getLogger('SpecializedBrowserPool')
        
        # Browser configuration - optimized for low resources
        # Merged and prioritized arguments from OptimizedBrowserPool
        if self.low_resource_mode:
            self.browser_args = [
                '--single-process',  # Critical for 1 CPU
                '--disable-gpu',
                '--disable-dev-shm-usage',  # Use disk instead of /dev/shm
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=site-per-process',  # Fewer processes
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-images',  # Save bandwidth and memory
                '--disable-software-rasterizer',
                '--window-size=1280,720',
                '--disable-logging',
                '--disable-permissions-api',
                '--max_old_space_size=512',  # Limit V8 heap to 512MB
                '--js-flags=--max-old-space-size=512',
                '--no-first-run', # From OptimizedBrowserPool
                '--no-default-browser-check', # From OptimizedBrowserPool
                '--disable-ipc-flooding-protection' # From OptimizedBrowserPool
            ]
        else:
            # Original args for systems with more resources, merged with OptimizedBrowserPool
            self.browser_args = [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
                '--disable-backgrounding-occluded-windows',
                '--metrics-recording-only',
                '--no-first-run', # From OptimizedBrowserPool
                '--no-default-browser-check', # From OptimizedBrowserPool
                '--disable-ipc-flooding-protection' # From OptimizedBrowserPool
            ]
        
        # Merged context options from OptimizedBrowserPool
        self.context_options = {
            'viewport': {'width': 1280, 'height': 720},
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'bypass_csp': True,
            'ignore_https_errors': True,
            'java_script_enabled': True,
            'extra_http_headers': { # From OptimizedBrowserPool
                'Accept-Language': 'en-US,en;q=0.9'
            }
        }
    
    async def start(self):
        """Start the specialized browser pool"""
        self.logger.info(f"Starting specialized browser pool for courts: {self.courts_needed}")
        self.running = True
        
        # Start Playwright instance
        self.playwright_instance = await async_playwright().start()

        # Initialize browsers in the main thread to avoid threading issues
        if self.persistent:
            self.logger.info("Persistent pool mode - initializing browsers now in main thread")
            await self._initialize_court_browsers()
        else:
            self.logger.info("Non-persistent pool mode - initializing browsers in background")
            # For non-persistent mode, still use background thread, but ensure async operations are awaited
            asyncio.create_task(self._initialize_court_browsers())
        
        self.logger.info("Specialized browser pool started")
    
    async def stop(self):
        """Stop the pool and clean up"""
        self.logger.info("Stopping specialized browser pool")
        self.running = False
        
        # Close all browsers
        with self.lock:
            for browser_id, browser in self.browsers.items():
                try:
                    if browser.page and not browser.page.is_closed():
                        await browser.page.close()
                    if browser.context:
                        await browser.context.close()
                    if browser.browser:
                        await browser.browser.close()
                except Exception as e:
                    self.logger.debug(f"Error closing browser {browser_id}: {e}")
            self.browsers.clear()
        
        # Reset court manager
        self.court_manager.reset()
        
        # Cleanup Playwright instance
        try:
            if self.playwright_instance:
                await self.playwright_instance.stop()
                self.playwright_instance = None
        except Exception as e:
            self.logger.debug(f"Error cleaning up playwright: {e}")
        
        self.logger.info("Specialized browser pool stopped")
    
    def is_ready(self) -> bool:
        """Check if browser pool is ready for use"""
        return self._ready_event.is_set() and bool(self.browsers)
    
    def get_browser_count(self) -> int:
        """Get the number of active browsers in the pool"""
        with self.lock:
            return len(self.browsers)
    
    async def wait_until_ready(self, timeout: float = 30) -> bool:
        """
        Wait until browser pool is ready or timeout occurs
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if ready, False if timeout or error
        """
        try:
            await asyncio.wait_for(self._ready_event.wait(), timeout=timeout)
            if self._initialization_error:
                self.logger.error(f"Browser pool initialization failed: {self._initialization_error}")
                return False
            return bool(self.browsers)
        except asyncio.TimeoutError:
            self.logger.error(f"Browser pool initialization timed out after {timeout}s")
            return False
        except Exception as e:
            self.logger.error(f"Error waiting for browser pool to be ready: {e}")
            return False
    
    def get_initialization_error(self) -> Optional[str]:
        """Get initialization error if any"""
        return self._initialization_error
    
    async def _initialize_court_browsers(self):
        """Create and position browsers for needed courts only (max 2 browsers)"""
        courts_to_init = self.courts_needed[:self.max_browsers]  # Limit to max_browsers
        self.logger.info(f"Creating {len(courts_to_init)} browsers for courts: {courts_to_init}")
        
        try:
            # Create browsers - sequential in low resource mode, parallel otherwise
            if self.low_resource_mode:
                # Sequential creation for 1 CPU
                for i, court_num in enumerate(courts_to_init):
                    try:
                        browser = await self._create_and_position_browser(court_num)
                        if browser:
                            with self.lock:
                                self.browsers[browser.id] = browser
                                self.court_manager.assign_browser_to_court(browser.id, court_num)
                            self.logger.info(f"✓ Browser {browser.id} ready on court {court_num}")
                        else:
                            self.logger.error(f"✗ Failed to create browser for court {court_num}")
                    except Exception as e:
                        self.logger.error(f"✗ Error creating browser for court {court_num}: {e}")
            else:
                # Parallel creation for multi-core systems
                tasks = []
                for court_num in courts_to_init:
                    tasks.append(self._create_and_position_browser(court_num))
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for i, browser in enumerate(results):
                    court_num = courts_to_init[i]
                    if isinstance(browser, SpecializedBrowser):
                        with self.lock:
                            self.browsers[browser.id] = browser
                            self.court_manager.assign_browser_to_court(browser.id, court_num)
                        self.logger.info(f"✓ Browser {browser.id} ready on court {court_num}")
                    else:
                        self.logger.error(f"✗ Failed to create browser for court {court_num}: {browser}")
            
            # Signal readiness if we created at least one browser
            if self.browsers:
                self._ready_event.set()
                self.logger.info(f"Browser pool is ready with {len(self.browsers)} browsers")
            else:
                self._initialization_error = "Failed to create any browsers"
                self._ready_event.set()  # Set event even on failure so waiters don't hang
                
        except Exception as e:
            self.logger.error(f"Fatal error during browser initialization: {e}", exc_info=True)
            self._initialization_error = str(e)
            self._ready_event.set()  # Set event even on failure
    
    async def _create_and_position_browser(self, court_number: int) -> Optional[SpecializedBrowser]:
        """Create a browser and pre-position it on a specific court"""
        try:
            start_time = time.time()
            self.logger.info(f"Creating browser for court {court_number}...")
            self.logger.debug(f"Thread: {threading.current_thread().name}")
            self.logger.debug(f"Browser config: headless={self.headless}, args={self.browser_args}")
            
            # Launch browser directly
            self.logger.debug("Launching Chromium browser...")
            browser = await self.playwright_instance.chromium.launch(
                headless=self.headless,
                args=self.browser_args
            )
            self.logger.debug("Browser launched successfully")
            
            # Create context
            context = await browser.new_context(**self.context_options)
            context.set_default_timeout(int(MAX_SINGLE_COURT_CHECK_TIME * 1000))  # Convert to milliseconds
            
            # Create page
            page = await context.new_page()
            
            # Create specialized browser instance
            court_index = court_number_to_index(court_number)  # Convert to 0-based
            specialized = SpecializedBrowser(
                browser=browser,
                context=context,
                page=page,
                court_number=court_number,
                court_index=court_index
            )
            
            # Navigate and position on court
            if await self._position_on_court(specialized):
                specialized.is_positioned = True
                self.stats['browsers_created'] += 1
                creation_time = time.time() - start_time
                self.logger.info(f"Court {court_number} browser created and positioned in {creation_time:.2f}s")
                return specialized
            else:
                self.logger.error(f"Failed to position browser on court {court_number}")
                await self._close_browser(specialized)
                self.stats['positioning_failures'] += 1
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to create browser for court {court_number}: {e}", exc_info=True)
            return None
    
    async def _position_on_court(self, browser: SpecializedBrowser) -> bool:
        """Navigate to booking page and position on specific court"""
        try:
            # Navigate to booking page
            self.logger.debug(f"Navigating to {self.booking_url}")
            await browser.page.goto(self.booking_url, wait_until='domcontentloaded', timeout=int(MAX_SINGLE_COURT_CHECK_TIME * 1000))
            self.logger.debug(f"Navigation complete, current URL: {browser.page.url}")
            
            # Wait for iframe
            iframe_found = False
            start_time = time.time()
            
            while time.time() - start_time < TARGET_AVAILABILITY_CHECK_TIME:
                frames = browser.page.frames
                if len(frames) > 1:
                    for frame in frames:
                        if SCHEDULING_IFRAME_URL_PATTERN in frame.url:
                            iframe_found = True
                            break
                    if iframe_found:
                        break
                await asyncio.sleep(FAST_POLL_INTERVAL)
            
            if not iframe_found:
                self.logger.error(f"Iframe not found for court {browser.court_number}")
                self.logger.debug(f"Found {len(browser.page.frames)} frames total")
                for i, frame in enumerate(browser.page.frames):
                    self.logger.debug(f"Frame {i}: {frame.url}")
                return False
            
            # Click on the specific court
            await asyncio.sleep(DEFAULT_WAIT_INTERVAL * 2)  # Let iframe stabilize
            
            # Find the iframe with booking interface
            booking_frame = None
            for frame in browser.page.frames:
                if SCHEDULING_IFRAME_URL_PATTERN in frame.url:
                    booking_frame = frame
                    break
            
            if not booking_frame:
                return False
            
            # Click the RESERVAR button for this court using proper tennis court detection
            js_code = f"""
            () => {{
                const buttons = Array.from(document.querySelectorAll('button'));
                const tennisCourtButtons = [];
                
                // Find all "Reservar" buttons and check if they belong to tennis courts
                buttons.forEach((btn, idx) => {{
                    const btnText = btn.innerText.trim();
                    if (btnText === 'Reservar' || btnText === 'RESERVAR') {{
                        // Check parent elements for tennis court info
                        let parent = btn.parentElement;
                        let depth = 5;
                        let courtInfo = null;
                        
                        while (parent && depth > 0) {{
                            const parentText = parent.textContent || '';
                            if (parentText.includes('TENNIS CANCHA')) {{
                                const match = parentText.match(/TENNIS CANCHA (\d)/);
                                if (match) {{
                                    courtInfo = {{
                                        courtNumber: parseInt(match[1]),
                                        buttonIndex: idx
                                    }};
                                    break;
                                }}
                            }}
                            parent = parent.parentElement;
                            depth--;
                        }}
                        
                        if (courtInfo && btn.offsetParent !== null) {{
                            tennisCourtButtons.push(courtInfo);
                        }}
                    }}
                }});
                
                // Sort by court number
                tennisCourtButtons.sort((a, b) => a.courtNumber - b.courtNumber);
                
                console.log('Found tennis court buttons:', tennisCourtButtons);
                
                // Find button for requested court
                const targetButton = tennisCourtButtons.find(btn => btn.courtNumber === {browser.court_number});
                if (targetButton) {{
                    const button = buttons[targetButton.buttonIndex];
                    if (button) {{
                        button.click();
                        return true;
                    }}
                }}
                return false;
            }}
            """
            
            success = await booking_frame.evaluate(js_code)
            if success:
                self.logger.info(f"Clicked court {browser.court_number} button")
                await asyncio.sleep(RESERVATION_RETRY_DELAY)  # Wait for calendar to load
                
                # Verify we're on the calendar page
                if 'calendar' in booking_frame.url or 'appointment' in booking_frame.url:
                    self.logger.info(f"Successfully positioned on court {browser.court_number} calendar")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error positioning browser on court {browser.court_number}: {e}")
            return False
    
    
    async def execute_parallel_booking(self, target_court: int, user_info: Dict[str, str], 
                                target_time: str = None, user_preferences: List[int] = None) -> Dict[str, Any]:
        """
        Execute booking attempt using available browsers with smart court assignment
        
        Args:
            target_court: Primary court to book
            user_info: User information for booking
            target_time: Time slot to book (from user_info if not provided)
            user_preferences: User's court preferences for fallback
        
        Returns:
            Dict with success status and details
        """
        # Check if browsers are ready
        if not self.is_ready():
            return {
                'success': False,
                'error': 'Browser pool not ready',
                'message': self.get_initialization_error() or 'Browsers not initialized'
            }
        
        if not target_time:
            target_time = user_info.get('preferred_time', '09:00')
            
        self.logger.info(f"Starting booking for {target_time} with court preference: {target_court}")
        start_time = time.time()
        
        self.stats['total_bookings'] += 1
        
        # Prepare results
        results = {
            'success': False,
            'court': None,
            'time': target_time,
            'execution_time': 0,
            'court_attempts': {},
            'browser_used': None
        }
        
        # Get optimized court order based on browser availability
        court_order = self.court_manager.get_court_assignment_strategy(
            user_preferences or [target_court]
        )
        
        # Try booking on each court in order
        for court_num in court_order:
            browser_id = self.court_manager.get_browser_for_court(court_num)
            
            if not browser_id or browser_id not in self.browsers:
                self.logger.debug(f"No browser available for court {court_num}")
                continue
            
            browser = self.browsers[browser_id]
            
            # Attempt booking on this court
            success, message = await self._attempt_booking_on_court(
                browser, target_time, user_info
            )
            
            results['court_attempts'][court_num] = {
                'success': success,
                'message': message,
                'browser': browser_id
            }
            
            if success:
                results['success'] = True
                results['court'] = court_num
                results['message'] = f"Successfully booked {target_time} on court {court_num}"
                results['browser_used'] = browser_id
                self.stats['successful_bookings'] += 1
                
                # Record success for smart assignment
                self.court_manager.record_booking_result(
                    browser_id, court_num, True, user_info.get('user_id')
                )
                
                # Handle post-booking court reassignment
                await self._handle_post_booking_reassignment(browser_id, court_num)
                
                break
            else:
                # Record failure
                self.court_manager.record_booking_result(
                    browser_id, court_num, False, user_info.get('user_id')
                )
        
        results['execution_time'] = time.time() - start_time
        self.logger.info(f"Booking completed in {results['execution_time']:.2f}s - Success: {results['success']}")
        
        return results
    
    async def _attempt_booking_on_court(self, browser: SpecializedBrowser, 
                                  target_time: str, user_info: Dict[str, str]) -> Tuple[bool, str]:
        """Attempt to book a specific time on a pre-positioned court"""
        try:
            self.logger.info(f"Attempting booking on court {browser.court_number} for {target_time}")
            
            # Mark browser as in use
            browser.last_used = datetime.now()
            browser.use_count += 1
            
            # Get the booking frame
            booking_frame = None
            for frame in browser.page.frames:
                if SCHEDULING_IFRAME_URL_PATTERN in frame.url:
                    booking_frame = frame
                    break
            
            if not booking_frame:
                return False, "Lost iframe reference"
            
            # Look for the time slot
            js_code = f"""
            () => {{
                const buttons = document.querySelectorAll('button, a, div[role="button"]');
                for (const btn of buttons) {{
                    if (btn.textContent.includes('{target_time}') && !btn.disabled) {{
                        btn.click();
                        return true;
                    }}
                }}
                return false;
            }}
            """
            
            if not await booking_frame.evaluate(js_code):
                # Time not available - check what times are available
                available_times = await self._get_available_times(booking_frame)
                return False, f"Time {target_time} not available. Available: {', '.join(available_times[:5])}"
            
            self.logger.info(f"Found and clicked {target_time} on court {browser.court_number}")
            await asyncio.sleep(RESERVATION_RETRY_DELAY)  # Wait for form
            
            # Fill user information using AcuityBookingForm handler
            try:
                # Initialize form handler
                form_handler = AcuityBookingForm()
                
                # Prepare user data in the format expected by Acuity form
                user_data = {
                    'nombre': user_info.get('first_name', ''),
                    'apellidos': user_info.get('last_name', ''),
                    'telefono': user_info.get('phone', ''),
                    'correo': user_info.get('email', '')
                }
                
                # Fill and submit the booking form
                # Note: We pass the page object, not the frame, as the form might be in main page
                success, message = await form_handler.fill_booking_form(
                    browser.page, 
                    user_data,
                    wait_for_navigation=True
                )
                
                if not success:
                    return False, f"Form error: {message}"
                
                self.logger.info(f"Form submitted on court {browser.court_number}: {message}")
                
                # Check booking success
                booking_success, confirmation_message = await form_handler.check_booking_success(browser.page)
                
                if booking_success:
                    return True, f"Successfully booked {target_time} - {confirmation_message}"
                else:
                    return True, f"Booking submitted (pending confirmation) - {confirmation_message}"
                
            except Exception as e:
                return False, f"Form submission error: {str(e)}"
                
        except Exception as e:
            self.logger.error(f"Booking attempt failed on court {browser.court_number}: {e}")
            browser.is_healthy = False
            return False, str(e)
    
    async def _get_available_times(self, frame: Frame) -> List[str]:
        """Extract available time slots from current page"""
        try:
            js_code = """
            () => {
                const times = [];
                const buttons = document.querySelectorAll('button, a, div[role="button"]');
                buttons.forEach(btn => {
                    const text = btn.textContent || '';
                    const match = text.match(/\\d{1,2}:\\d{2}/);
                    if (match && !btn.disabled) {
                        times.push(match[0]);
                    }
                });
                return [...new Set(times)];
            }
            """
            return await frame.evaluate(js_code)
        except Exception as e:
            self.logger.error(f"Error getting available times: {e}")
            return []
    
    async def _handle_post_booking_reassignment(self, browser_id: str, booked_court: int):
        """Handle browser reassignment after successful booking"""
        try:
            # Get next court assignment from manager
            next_court = self.court_manager.get_next_court_assignment(booked_court, browser_id)
            
            if next_court and next_court != booked_court:
                self.logger.info(f"Reassigning browser {browser_id} from court {booked_court} to court {next_court}")
                
                # Get browser
                browser = self.browsers.get(browser_id)
                if not browser:
                    return
                
                # Switch court
                switch_result = await self.court_switcher.switch_court(
                    browser.page, 
                    booked_court, 
                    next_court,
                    browser_id
                )
                
                if switch_result['success']:
                    # Update browser's court assignment
                    browser.court_number = next_court
                    browser.court_index = next_court - 1
                    browser.is_positioned = True
                    
                    # Update manager
                    self.court_manager.assign_browser_to_court(browser_id, next_court)
                    
                    self.logger.info(f"Browser {browser_id} successfully reassigned to court {next_court}")
                else:
                    self.logger.error(f"Failed to reassign browser {browser_id}: {switch_result['error']}")
                    
        except Exception as e:
            self.logger.error(f"Error in post-booking reassignment: {e}")
    
    
    async def _close_browser(self, browser: SpecializedBrowser):
        """Close a browser instance"""
        try:
            if browser.page:
                await browser.page.close()
            if browser.context:
                await browser.context.close()
            if browser.browser:
                await browser.browser.close()
            self.logger.debug(f"Closed browser for court {browser.court_number}")
        except Exception as e:
            self.logger.error(f"Error closing browser: {e}")
    
    async def _maintenance_loop(self):
        """Maintain browser health and positioning"""
        self.logger.info("Maintenance thread started")
        
        while self.running:
            try:
                await asyncio.sleep(BROWSER_HEALTH_CHECK_INTERVAL * 10)  # Check periodically
                
                # Check browser health
                browsers_to_recycle = []
                
                with self.lock: # Lock is for self.browsers, not Playwright operations
                    for browser_id, browser in list(self.browsers.items()):
                        # Check if browser needs recycling
                        age = datetime.now() - browser.created_at
                        
                        if (not browser.is_healthy or 
                            browser.use_count >= self.max_uses or
                            age > self.max_age):
                            
                            browsers_to_recycle.append((browser_id, browser))
                            
                        # Check positioning periodically
                        elif age > timedelta(minutes=15):
                            court = self.court_manager.get_court_for_browser(browser_id)
                            if court:
                                health_check = await self.court_switcher.verify_browser_health(
                                    browser.page, court
                                )
                                if not health_check['positioned']:
                                    self.logger.warning(f"Browser {browser_id} lost positioning on court {court}")
                                    browsers_to_recycle.append((browser_id, browser))
                
                # Recycle unhealthy browsers
                for browser_id, browser in browsers_to_recycle:
                    self.logger.info(f"Recycling browser {browser_id}")
                    await self._recycle_browser(browser_id)
                
                # Ensure we maintain required number of browsers
                await self._ensure_browser_coverage()
                        
            except Exception as e:
                self.logger.error(f"Maintenance error: {e}")
    
    async def _recycle_browser(self, browser_id: str):
        """Recycle a specific browser"""
        try:
            with self.lock:
                browser = self.browsers.get(browser_id)
                if not browser:
                    return
                
                court = self.court_manager.get_court_for_browser(browser_id)
                
                # Close old browser
                await self._close_browser(browser)
                del self.browsers[browser_id]
                self.stats['browsers_recycled'] += 1
            
            # Create replacement if needed
            if court and len(self.browsers) < self.max_browsers:
                new_browser = await self._create_and_position_browser(court)
                if new_browser:
                    with self.lock:
                        self.browsers[new_browser.id] = new_browser
                        self.court_manager.assign_browser_to_court(new_browser.id, court)
                        
        except Exception as e:
            self.logger.error(f"Error recycling browser: {e}")
    
    async def _ensure_browser_coverage(self):
        """Ensure we have browsers on primary courts"""
        try:
            current_browser_count = len(self.browsers)
            
            if current_browser_count < self.max_browsers:
                # Check which courts need browsers
                courts_with_browsers = set(
                    self.court_manager.get_court_for_browser(bid) 
                    for bid in self.browsers.keys()
                )
                
                # Prioritize primary courts
                for court in self.courts_needed[:self.max_browsers]:
                    if court not in courts_with_browsers and current_browser_count < self.max_browsers:
                        self.logger.info(f"Creating browser for uncovered court {court}")
                        browser = await self._create_and_position_browser(court)
                        if browser:
                            with self.lock:
                                self.browsers[browser.id] = browser
                                self.court_manager.assign_browser_to_court(browser.id, court)
                            current_browser_count += 1
                            
        except Exception as e:
            self.logger.error(f"Error ensuring browser coverage: {e}")
    
    async def refresh_browser_pages(self) -> Dict[str, bool]:
        """
        Refresh all browser pages to prevent staleness and memory accumulation.
        Uses async-safe page.reload() method within existing event loop.
        
        Returns:
            Dict[str, bool]: browser_id -> success status
        """
        refresh_results = {}
        
        self.logger.info("🔄 Starting browser page refresh cycle")
        
        with self.lock:
            browsers_to_refresh = list(self.browsers.items())
        
        for browser_id, browser in browsers_to_refresh:
            try:
                court = self.court_manager.get_court_for_browser(browser_id)
                age_minutes = (datetime.now() - browser.created_at).total_seconds() / 60
                
                self.logger.info(f"🔄 Refreshing browser {browser_id} (Court {court}, Age: {age_minutes:.1f}min)")
                
                # Use stateful refresh to maintain court position
                from lvbot.automation.browser.stateful_browser_refresh import StatefulBrowserRefresh
                stateful_refresh = StatefulBrowserRefresh()
                
                success, message = await stateful_refresh.refresh_with_state(browser.page)
                
                if success:
                    self.logger.info(f"✅ Browser {browser_id}: {message}")
                    # Update browser health and reset use count
                    browser.is_healthy = True
                    browser.use_count = 0
                    browser.last_used = datetime.now()
                    refresh_results[browser_id] = True
                else:
                    self.logger.error(f"❌ Browser {browser_id}: {message}")
                    # Mark as unhealthy for recycling
                    browser.is_healthy = False
                    refresh_results[browser_id] = False
                    
            except Exception as e:
                self.logger.error(f"❌ Failed to refresh browser {browser_id}: {e}")
                refresh_results[browser_id] = False
                # Mark browser as unhealthy
                if browser_id in self.browsers:
                    self.browsers[browser_id].is_healthy = False
        
        successful_refreshes = sum(1 for success in refresh_results.values() if success)
        total_browsers = len(refresh_results)
        
        self.logger.info(f"🔄 Browser refresh cycle complete: {successful_refreshes}/{total_browsers} successful")
        
        return refresh_results
    
    def get_stats(self) -> Dict:
        """Get pool statistics"""
        with self.lock:
            # Get court manager status
            court_summary = self.court_manager.get_status_summary()
            
            # Get browser details
            browser_details = {}
            for browser_id, browser in self.browsers.items():
                court = self.court_manager.get_court_for_browser(browser_id)
                browser_details[browser_id] = {
                    'court': court,
                    'healthy': browser.is_healthy,
                    'positioned': browser.is_positioned,
                    'uses': browser.use_count,
                    'age_minutes': (datetime.now() - browser.created_at).total_seconds() / 60
                }
            
            return {
                **self.stats,
                'browser_count': len(self.browsers),
                'max_browsers': self.max_browsers,
                'court_assignments': court_summary['assignments'],
                'browser_details': browser_details,
                'available_courts': court_summary['available_courts']
            }
