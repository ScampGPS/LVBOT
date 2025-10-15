import asyncio
import logging
import time
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from lvbot.utils.constants import BrowserTimeouts, BrowserPoolConfig, COURT_CONFIG

# Read production mode setting
PRODUCTION_MODE = os.getenv('PRODUCTION_MODE', 'true').lower() == 'true'

logger = logging.getLogger(__name__)

class AsyncBrowserPool:
    """Pure async browser pool using async_playwright
    REPLACES all existing browser pool implementations
    """
    
    # Use centralized court configuration
    @property
    def DIRECT_COURT_URLS(self):
        """Get direct court URLs from centralized config"""
        return {
            court_num: config["direct_url"] 
            for court_num, config in COURT_CONFIG.items()
        }

    def __init__(self, courts: List[int] = [1, 2, 3]):
        self.courts = courts
        self.pages: Dict[int, Page] = {}
        self.contexts: Dict[int, BrowserContext] = {}  # Track contexts for proper cleanup
        self.lock = asyncio.Lock()
        self.browser: Browser = None
        self.playwright = None
        self.critical_operation_in_progress = False  # Flag to prevent refresh during bookings
        self.is_partially_ready = False  # Track if pool is only partially initialized

    async def start(self):
        """Initialize browsers and pre-navigate to direct court URLs in parallel"""
        try:
            logger.info("Starting Playwright...")
            self.playwright = await async_playwright().start()
            
            logger.info("Launching Chromium browser...")
            self.browser = await self.playwright.chromium.launch(
                headless=False,  # Run with UI for debugging
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',  # Disable automation features
                    '--disable-infobars',  # Remove "Chrome is being controlled" bar
                    '--window-size=1920,1080',
                    '--start-maximized'
                ]
            )
            
            # PARALLEL initialization with retry mechanism - critical for speed and resilience
            logger.info("Initializing browser pool with PARALLEL pre-navigation to direct court URLs (with retry)")
            tasks = []
            for i, court in enumerate(self.courts):
                # Add staggered delay to prevent simultaneous hits
                delay = i * 1.5  # 1.5 seconds between each court initialization
                tasks.append(self._create_and_navigate_court_page_with_stagger(court, delay))
            
            # Wait for ALL courts in parallel - use gather with return_exceptions=True
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successful initializations
            successful_courts = 0
            failed_courts = []
            for i, (court, result) in enumerate(zip(self.courts, results)):
                if isinstance(result, Exception):
                    logger.error(f"❌ Court {court} failed to initialize: {result}")
                    failed_courts.append(court)
                else:
                    successful_courts += 1
                    logger.info(f"✅ Court {court} initialized successfully")
            
            # Enable partial success - continue with available courts
            if successful_courts == 0:
                raise Exception(f"All court initializations failed: 0/{len(self.courts)} courts ready")
            
            # Log appropriate message based on success level
            if successful_courts < len(self.courts):
                logger.warning(f"⚠️ PARTIAL Browser pool initialization: {successful_courts}/{len(self.courts)} courts ready")
                logger.warning(f"Failed courts: {failed_courts}")
                logger.info("Continuing with available courts...")
            else:
                logger.info(f"✅ FULL Browser pool initialized with {successful_courts}/{len(self.courts)} courts ready")
            
            # Mark pool as partially ready if at least 1 court is available
            self.is_partially_ready = successful_courts < len(self.courts)
            
        except Exception as e:
            logger.error(f"Failed to start browser pool: {e}")
            await self._cleanup_on_failure()
            raise

    async def _create_and_navigate_court_page_with_stagger(self, court: int, initial_delay: float):
        """
        Wrapper that adds staggered start and retry logic to court page creation
        
        Args:
            court: The court number to create and navigate
            initial_delay: Initial delay in seconds before starting (for staggering)
            
        Returns:
            bool: True if successful after retries, raises exception if all attempts fail
        """
        # Apply stagger delay to prevent simultaneous server hits
        if initial_delay > 0:
            if not PRODUCTION_MODE:
                logger.info(f"Court {court}: Waiting {initial_delay}s before initialization (staggered start)")
            await asyncio.sleep(initial_delay)
        
        return await self._create_and_navigate_court_page_with_retry(court)
    
    async def _create_and_navigate_court_page_with_retry(self, court: int):
        """
        Wrapper that adds retry logic to court page creation with exponential backoff
        
        Args:
            court: The court number to create and navigate
            
        Returns:
            bool: True if successful after retries, raises exception if all attempts fail
        """
        for attempt in range(BrowserPoolConfig.MAX_RETRY_ATTEMPTS):
            try:
                return await self._create_and_navigate_court_page_safe(court)
            except Exception as e:
                if attempt < BrowserPoolConfig.MAX_RETRY_ATTEMPTS - 1:
                    # Calculate exponential backoff delay: 2s, 4s, 8s
                    delay = BrowserTimeouts.RETRY_DELAY_BASE ** (attempt + 1)
                    logger.warning(f"Court {court} attempt {attempt + 1}/{BrowserPoolConfig.MAX_RETRY_ATTEMPTS} failed: {e}")
                    if not PRODUCTION_MODE:
                        logger.info(f"Court {court}: Retrying in {delay}s (exponential backoff)...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Court {court} failed after {BrowserPoolConfig.MAX_RETRY_ATTEMPTS} attempts: {e}")
                    raise

    async def _create_and_navigate_court_page_safe(self, court: int):
        """
        Safe wrapper for parallel court page creation with error handling
        
        Args:
            court: The court number to create and navigate
            
        Returns:
            bool: True if successful, raises exception if failed
        """
        try:
            # Create context with more realistic browser properties
            context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='es-GT',
                timezone_id='America/Guatemala'
            )
            page = await context.new_page()
            
            # Add anti-detection measures
            await page.add_init_script("""
                // Override webdriver detection
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Add chrome object
                window.chrome = {
                    runtime: {},
                };
                
                // Fix permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)
            
            self.pages[court] = page
            self.contexts[court] = context
            
            # Pre-navigate if URL available - with shorter timeout for speed
            if court in self.DIRECT_COURT_URLS:
                court_url = self.DIRECT_COURT_URLS[court]
                if not PRODUCTION_MODE:
                    logger.debug(f"Court {court}: Pre-navigating to {court_url}")
                
                # Use domcontentloaded instead of networkidle for faster initialization
                # The test showed DOM loads at ~7s, networkidle takes 30+s
                await page.goto(court_url, wait_until='domcontentloaded', timeout=BrowserTimeouts.SLOW_NAVIGATION)
                
                # Log where we actually ended up
                final_url = page.url
                if not PRODUCTION_MODE:
                    logger.info(f"Court {court}: After navigation, current URL: {final_url}")
                
                if '/datetime/' in final_url:
                    logger.warning(f"Court {court}: WARNING - Ended up on booking form URL instead of calendar!")
                    logger.warning(f"Court {court}: This may cause issues for executors expecting calendar page")
                
                # Wait for critical calendar elements to appear (they show up around 24-25s)
                try:
                    # Wait for time elements which appear around 24-25s based on test
                    await page.wait_for_selector('[class*="time"]', timeout=30000)
                    if not PRODUCTION_MODE:
                        logger.debug(f"Court {court}: Calendar elements loaded")
                except:
                    # If calendar elements don't load, continue anyway
                    logger.warning(f"Court {court}: Calendar elements not found, continuing anyway")
                
                logger.debug(f"Court {court}: Pre-navigation completed")
                
                # IMPORTANT: Add warm-up delay to appear more human-like
                # This helps avoid anti-bot detection
                warmup_delay = getattr(self, 'WARMUP_DELAY', 10.0)  # Default 10s, can be overridden
                logger.info(f"Court {court}: Warming up browser for {warmup_delay} seconds...")
                await asyncio.sleep(warmup_delay)
                logger.info(f"Court {court}: Browser warm-up completed")
            else:
                logger.warning(f"Court {court}: No direct URL available for pre-navigation")
                
            return True
            
        except Exception as e:
            # Clean up failed page/context
            if court in self.pages:
                try:
                    await self.pages[court].close()
                    del self.pages[court]
                except:
                    pass
            if court in self.contexts:
                try:
                    await self.contexts[court].close()
                    del self.contexts[court]
                except:
                    pass
            raise e

    async def _create_and_navigate_court_page(self, court: int):
        """Legacy method - keeping for compatibility"""
        return await self._create_and_navigate_court_page_safe(court)

    async def _cleanup_on_failure(self):
        """Cleanup resources when startup fails"""
        try:
            # Close all pages
            for page in self.pages.values():
                try:
                    await page.close()
                except:
                    pass
            
            # Close all contexts
            for context in self.contexts.values():
                try:
                    await context.close()
                except:
                    pass
            
            # Close browser
            if self.browser:
                try:
                    await self.browser.close()
                except:
                    pass
            
            # Stop playwright
            if self.playwright:
                try:
                    await self.playwright.stop()
                except:
                    pass
            
            # Clear state
            self.pages.clear()
            self.contexts.clear()
            self.browser = None
            self.playwright = None
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def stop(self):
        """Cleanup all resources - waits for critical operations to complete"""
        import asyncio
        
        logger.info("🔴 STARTING BROWSER POOL SHUTDOWN...")
        
        # Wait for critical operations to complete before shutdown
        if self.critical_operation_in_progress:
            logger.info("⏳ Waiting for critical booking operations to complete before shutdown...")
            max_wait_time = 300  # 5 minutes max wait
            wait_interval = 1    # Check every second
            waited = 0
            
            while self.critical_operation_in_progress and waited < max_wait_time:
                await asyncio.sleep(wait_interval)
                waited += wait_interval
                if waited % 30 == 0:  # Log every 30 seconds
                    logger.info(f"⏳ Still waiting for critical operations... ({waited}s elapsed)")
            
            if self.critical_operation_in_progress:
                logger.warning(f"⚠️ Forcing shutdown after {max_wait_time}s - critical operation still in progress")
            else:
                logger.info("✅ Critical operations completed, proceeding with shutdown")
        
        # Enhanced cleanup with better logging and error handling
        logger.info(f"🔄 Closing {len(self.pages)} pages...")
        page_errors = []
        for court_num, page in self.pages.items():
            try:
                if page and not page.is_closed():
                    await page.close()
                    logger.info(f"✅ Page for court {court_num} closed")
                else:
                    logger.info(f"⚠️ Page for court {court_num} was already closed")
            except Exception as e:
                # Suppress expected shutdown errors
                if "Connection closed" in str(e) or "Target closed" in str(e):
                    logger.debug(f"Page {court_num} already disconnected (normal during shutdown)")
                else:
                    page_errors.append(f"Court {court_num}: {str(e)}")
                    logger.error(f"Error closing page for court {court_num}: {e}")
        
        logger.info(f"🔄 Closing {len(self.contexts)} browser contexts...")
        context_errors = []
        for court_num, context in self.contexts.items():
            try:
                if context:
                    await context.close()
                    logger.info(f"✅ Context for court {court_num} closed")
            except Exception as e:
                # Suppress expected shutdown errors
                if "Connection closed" in str(e) or "Target closed" in str(e):
                    logger.debug(f"Context {court_num} already disconnected (normal during shutdown)")
                else:
                    context_errors.append(f"Court {court_num}: {str(e)}")
                    logger.error(f"Error closing context for court {court_num}: {e}")
        
        # Clear the dictionaries
        self.pages.clear()
        self.contexts.clear()
        logger.info("✅ Page and context dictionaries cleared")
        
        # Close browser with enhanced error handling
        if self.browser:
            try:
                await self.browser.close()
                logger.info("✅ Chromium browser closed")
            except Exception as e:
                # Suppress expected shutdown errors
                if "Connection closed" in str(e) or "Target closed" in str(e):
                    logger.info("ℹ️ Browser already disconnected (normal during shutdown)")
                else:
                    logger.error(f"❌ Error closing browser: {e}")
        else:
            logger.info("⚠️ No browser instance to close")
                
        # Stop playwright with enhanced error handling
        if self.playwright:
            try:
                await self.playwright.stop()
                logger.info("✅ Playwright stopped")
            except Exception as e:
                logger.error(f"❌ Error stopping playwright: {e}")
        else:
            logger.info("⚠️ No playwright instance to stop")
        
        # Final status report
        if page_errors or context_errors:
            logger.warning(f"⚠️ Shutdown completed with {len(page_errors)} page errors and {len(context_errors)} context errors")
        else:
            logger.info("✅ BROWSER POOL SHUTDOWN COMPLETED SUCCESSFULLY")
        
        # Reset internal state
        self.browser = None
        self.playwright = None
        self.critical_operation_in_progress = False
        self.is_partially_ready = False

    async def get_page(self, court_num: int) -> Page:
        """Get page for specific court with connection health check"""
        async with self.lock:
            page = self.pages.get(court_num)
            if not page:
                # If court was never initialized, log it differently
                if court_num not in self.courts:
                    logger.warning(f"Court {court_num} was not requested during initialization")
                else:
                    logger.warning(f"Court {court_num} is not available (initialization may have failed)")
                return None
            
            # Check if page connection is still alive
            try:
                # Quick connection test - accessing URL property should work if connection is alive
                _ = page.url  # This will fail if connection is dead
                return page
            except Exception as e:
                logger.warning(f"Court {court_num} page connection is dead: {e}. Recreating...")
                
                # Clean up dead page/context
                try:
                    await page.close()
                except:
                    pass
                try:
                    if court_num in self.contexts:
                        await self.contexts[court_num].close()
                except:
                    pass
                
                # Remove from tracking
                if court_num in self.pages:
                    del self.pages[court_num]
                if court_num in self.contexts:
                    del self.contexts[court_num]
                
                # Recreate the page
                try:
                    await self._create_and_navigate_court_page_safe(court_num)
                    return self.pages.get(court_num)
                except Exception as recreate_error:
                    logger.error(f"Failed to recreate Court {court_num} page: {recreate_error}")
                    return None
    
    def is_ready(self) -> bool:
        """Check if browser pool is ready for use (at least one court available)"""
        return bool(self.browser and self.pages)
    
    async def wait_until_ready(self, timeout: float = 30) -> bool:
        """
        Wait until browser pool is ready or timeout occurs
        Compatible with SpecializedBrowserPool interface
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if ready, False if timeout or error
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_ready():
                return True
            await asyncio.sleep(0.5)
        return False
    
    def get_initialization_error(self) -> Optional[str]:
        """
        Get initialization error if any
        Compatible with SpecializedBrowserPool interface
        
        Returns:
            Error message if initialization failed, None otherwise
        """
        if not self.is_ready():
            return "Browser pool not initialized or no pages available"
        return None
    
    def get_stats(self) -> Dict:
        """
        Get pool statistics
        Compatible with SpecializedBrowserPool interface
        
        Returns:
            Dictionary with pool statistics
        """
        return {
            'browser_count': len(self.pages),
            'browsers_created': len(self.pages),
            'browsers_recycled': 0,
            'positioning_failures': 0,
            'total_bookings': 0,
            'successful_bookings': 0,
            'max_browsers': len(self.courts),
            'court_assignments': {court: court for court in self.pages.keys()},
            'browser_details': {
                f"court{court}": {
                    'court': court,
                    'healthy': True,
                    'positioned': True,
                    'uses': 0,
                    'age_minutes': 0
                } for court in self.pages.keys()
            },
            'available_courts': list(self.pages.keys())
        }
    
    def get_available_courts(self) -> List[int]:
        """Get list of successfully initialized courts"""
        return list(self.pages.keys())
    
    def is_fully_ready(self) -> bool:
        """Check if all requested courts are initialized"""
        return self.is_ready() and not self.is_partially_ready
    
    async def set_critical_operation(self, in_progress: bool):
        """Set critical operation flag to prevent refresh during important operations"""
        async with self.lock:
            self.critical_operation_in_progress = in_progress
            logger.info(f"Critical operation flag set to: {in_progress}")
    
    def is_critical_operation_in_progress(self) -> bool:
        """Check if a critical operation is in progress"""
        return self.critical_operation_in_progress
    
    async def refresh_browser_pages(self) -> Dict[int, bool]:
        """
        Refresh all browser pages to prevent staleness and memory accumulation.
        Navigates back to the court booking page for each court.
        
        Returns:
            Dict[int, bool]: court_number -> success status
        """
        refresh_results = {}
        
        logger.info("🔄 Starting browser page refresh cycle")
        
        # Check if we have pages to refresh
        if not self.pages:
            logger.warning("No browser pages to refresh")
            return refresh_results
        
        for court in self.courts:
            if court not in self.pages:
                logger.warning(f"Court {court} has no page to refresh")
                refresh_results[court] = False
                continue
                
            page = self.pages[court]
            
            try:
                logger.info(f"🔄 Refreshing Court {court} browser page")
                
                # Navigate back to the court's booking page
                court_url = self.DIRECT_COURT_URLS.get(court)
                if not court_url:
                    logger.error(f"No URL found for court {court}")
                    refresh_results[court] = False
                    continue
                
                # Navigate to the court page with a reasonable timeout
                await page.goto(court_url, wait_until='domcontentloaded', timeout=30000)
                logger.info(f"✅ Court {court} refreshed successfully")
                refresh_results[court] = True
                
            except Exception as e:
                logger.error(f"❌ Failed to refresh Court {court}: {e}")
                refresh_results[court] = False
        
        successful_refreshes = sum(1 for success in refresh_results.values() if success)
        total_courts = len(refresh_results)
        
        logger.info(f"🔄 REFRESH COMPLETE: {successful_refreshes}/{total_courts} courts refreshed successfully")
        
        return refresh_results
    
    async def execute_parallel_booking(self, target_court: int, user_info: Dict[str, Any], 
                                     target_time: str = None, user_preferences: List[int] = None,
                                     target_date: datetime = None) -> Dict[str, Any]:
        """
        Execute parallel booking attempt on specified court
        
        Args:
            target_court: Court index (0-2) to book
            user_info: User information for booking
            target_time: Preferred time slot
            user_preferences: List of court preferences
            target_date: Target date for the booking
            
        Returns:
            Dict with success status and details
        """
        try:
            # target_court is already the court number (1, 2, or 3), not an index
            court_number = target_court
            
            # Get the page for this court
            page = await self.get_page(court_number)
            if not page:
                # Provide more context about why court is not available
                available_courts = self.get_available_courts()
                error_msg = f'Court {court_number} page not available. Available courts: {available_courts}'
                if self.is_partially_ready:
                    error_msg += ' (Browser pool is partially initialized)'
                return {
                    'success': False,
                    'error': error_msg
                }
            
            # Check if experienced mode is enabled in user_info
            experienced_mode = user_info.get('experienced_mode', True)  # Default to True
            
            if experienced_mode:
                # Use ExperiencedBookingExecutor with mouse clicks
                logger.info(f"Using EXPERIENCED mode (mouse clicks) for Court {court_number}")
                from lvbot.utils.experienced_booking_executor import ExperiencedBookingExecutor
                executor = ExperiencedBookingExecutor(self)
                
                # Execute the booking
                result = await executor.execute_booking(
                    court_number=court_number,
                    target_date=target_date or datetime.now(),
                    time_slot=target_time or '10:00',
                    user_info=user_info
                )
            else:
                # Use SmartAsyncBookingExecutor with direct URL navigation
                logger.info(f"Using STANDARD mode (direct URL) for Court {court_number}")
                from lvbot.utils.smart_async_booking_executor import SmartAsyncBookingExecutor
                executor = SmartAsyncBookingExecutor(self)
                
                # Execute the booking with smart timeout and retry
                result = await executor.execute_booking_with_retry(
                    court_number=court_number,
                    time_slot=target_time or '10:00',
                    user_info=user_info,
                    target_date=target_date or datetime.now()
                )
            
            # Map result fields based on executor type
            if experienced_mode:
                # ExperiencedBookingExecutor returns different fields
                return {
                    'success': result.success,
                    'court': result.court_number,
                    'time': target_time or '10:00',  # Time from input since not in result
                    'message': result.confirmation_url if result.success else result.error_message,
                    'error': result.error_message
                }
            else:
                # SmartAsyncBookingExecutor fields
                return {
                    'success': result.success,
                    'court': result.court_reserved,
                    'time': result.time_reserved,
                    'message': result.message or result.error_message,
                    'error': result.error_message
                }
            
        except Exception as e:
            logger.error(f"Error in execute_parallel_booking: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def refresh_all_pages(self, refresh_type: str = "current"):
        """
        Refresh all court pages to get latest availability data
        
        Args:
            refresh_type: Type of refresh to perform
                - "calendar": Navigate back to calendar page (for availability checking)
                - "current": Maintain current page state (default, for booking process)
        
        Refreshes all 3 courts in parallel for speed. If refresh fails,
        proceeds with existing page content (might be slightly stale but functional).
        """
        # Check if critical operation is in progress
        if self.is_critical_operation_in_progress():
            logger.warning("Skipping page refresh - critical booking operation in progress")
            return
            
        logger.info(f"Refreshing all court pages (mode: {refresh_type}) for latest availability data")
        tasks = []
        for court in self.courts:
            if court in self.pages:
                tasks.append(self._refresh_court_page(court, refresh_type))
        
        # Wait for all refreshes to complete (or fail)
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("All court page refreshes completed")

    async def _refresh_court_page(self, court: int, refresh_type: str = "current"):
        """
        Refresh specific court page
        
        Args:
            court: The court number to refresh
            refresh_type: Type of refresh ("calendar" or "current")
        """
        try:
            page = self.pages[court]
            
            if refresh_type == "calendar":
                # Navigate back to the calendar page
                logger.info(f"Court {court}: Refreshing to calendar page")
                court_url = self.DIRECT_COURT_URLS[court]
                await page.goto(court_url, wait_until='domcontentloaded', timeout=BrowserTimeouts.SLOW_NAVIGATION)
                
                # Log where we ended up
                final_url = page.url
                logger.info(f"Court {court}: After refresh, current URL: {final_url}")
                
                # Wait for time elements to appear
                try:
                    await page.wait_for_selector('[class*="time"]', timeout=30000)
                    if not PRODUCTION_MODE:
                        logger.debug(f"Court {court}: Calendar elements loaded")
                except:
                    logger.warning(f"Court {court}: Calendar elements not found after refresh")
                    
            else:
                # Use stateful refresh to maintain current state
                logger.debug(f"Court {court}: Starting stateful refresh")
                from lvbot.utils.stateful_browser_refresh import StatefulBrowserRefresh
                stateful_refresh = StatefulBrowserRefresh()
                
                success, message = await stateful_refresh.refresh_with_state(page)
                
                if success:
                    logger.info(f"Court {court}: {message}")
                else:
                    logger.warning(f"Court {court}: {message}")
            
        except Exception as e:
            logger.warning(f"Court {court}: Page refresh failed: {e} - proceeding with existing content")
            # Don't raise - proceed with existing page content
    
    async def is_slot_available(self, court_number: int, time_slot: str, target_date: datetime) -> Dict[str, Any]:
        """
        Check if a time slot is available without actually booking it
        
        Args:
            court_number: Court number (1, 2, or 3)
            time_slot: Time slot in HH:MM format (e.g., "13:00")
            target_date: Target date for checking availability
            
        Returns:
            Dict with availability status:
            {
                'available': bool,
                'reason': str,  # Explanation if not available
                'checked_at': datetime,
                'court': int
            }
        """
        try:
            # Get the page for this court
            page = await self.get_page(court_number)
            if not page:
                return {
                    'available': False,
                    'reason': f'Court {court_number} page not available',
                    'checked_at': datetime.now(),
                    'court': court_number
                }
            
            # Use the same navigation logic as SmartAsyncBookingExecutor but without booking
            from lvbot.utils.smart_async_booking_executor import SmartAsyncBookingExecutor
            
            # Create executor instance to use its navigation methods
            executor = SmartAsyncBookingExecutor(self)
            
            # Construct direct URL to check availability
            court_urls = {
                1: "https://clublavilla.as.me/schedule/7d558012/appointment/15970897/calendar/4282490",
                2: "https://clublavilla.as.me/schedule/7d558012/appointment/16021953/calendar/4291312", 
                3: "https://clublavilla.as.me/schedule/7d558012/appointment/16120442/calendar/4307254"
            }
            
            date_str = target_date.strftime("%Y-%m-%d")
            appointment_type_id = court_urls[court_number].split('/appointment/')[1].split('/')[0]
            direct_url = f"{court_urls[court_number]}/datetime/{date_str}T{time_slot}:00-06:00?appointmentTypeIds[]={appointment_type_id}"
            
            logger.info(f"Checking availability for Court {court_number} at {time_slot} on {date_str}")
            
            # Navigate to the booking form to check availability
            navigation_result = await executor._navigate_with_smart_timeout(page, direct_url)
            
            if not navigation_result['success']:
                return {
                    'available': False,
                    'reason': f"Navigation failed: {navigation_result.get('error', 'unknown error')}",
                    'checked_at': datetime.now(),
                    'court': court_number
                }
            
            # Check if form was detected (indicates availability)
            if navigation_result.get('form_ready', False):
                return {
                    'available': True,
                    'reason': 'Booking form detected - slot appears available',
                    'checked_at': datetime.now(),
                    'court': court_number
                }
            else:
                reason = navigation_result.get('reason', 'unknown')
                if reason == 'no_form_after_dom_ready':
                    reason_text = 'No booking form found - slot likely unavailable'
                elif reason == 'unavailable_message_found':
                    reason_text = 'Slot explicitly marked as unavailable'
                else:
                    reason_text = f'Form not ready - {reason}'
                
                return {
                    'available': False,
                    'reason': reason_text,
                    'checked_at': datetime.now(),
                    'court': court_number
                }
                
        except Exception as e:
            logger.error(f"Error checking availability for Court {court_number}: {e}")
            return {
                'available': False,
                'reason': f'Error during availability check: {str(e)}',
                'checked_at': datetime.now(),
                'court': court_number
            }
    
    async def stop(self):
        """Clean up all browser resources properly"""
        logger.info("Stopping AsyncBrowserPool...")
        
        try:
            # Close all pages first
            for court, page in self.pages.items():
                try:
                    logger.debug(f"Closing page for court {court}")
                    await page.close()
                except Exception as e:
                    if "Connection closed" not in str(e) and "Target closed" not in str(e):
                        logger.error(f"Error closing page for court {court}: {e}")
            
            # Close all contexts
            for court, context in self.contexts.items():
                try:
                    logger.debug(f"Closing context for court {court}")
                    await context.close()
                except Exception as e:
                    if "Connection closed" not in str(e) and "Target closed" not in str(e):
                        logger.error(f"Error closing context for court {court}: {e}")
            
            # Close the browser
            if self.browser:
                try:
                    logger.info("Closing browser...")
                    await self.browser.close()
                except Exception as e:
                    if "Connection closed" not in str(e) and "Target closed" not in str(e):
                        logger.error(f"Error closing browser: {e}")
            
            # Stop playwright
            if self.playwright:
                try:
                    logger.info("Stopping playwright...")
                    await self.playwright.stop()
                except Exception as e:
                    logger.error(f"Error stopping playwright: {e}")
            
            # Clear references
            self.pages.clear()
            self.contexts.clear()
            self.browser = None
            self.playwright = None
            
            logger.info("✅ AsyncBrowserPool stopped successfully")
            
        except Exception as e:
            logger.error(f"Error during AsyncBrowserPool cleanup: {e}")