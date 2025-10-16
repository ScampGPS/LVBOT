"""
Debug version of experienced_booking_executor with detailed logging
"""
from tracking import t

import asyncio
import random
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from playwright.async_api import Page

# Set up very detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

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
    t('archive.testing.tests.test_investigations.debug_experienced_executor.apply_speed')
    return max(0.05, delay_seconds / SPEED_MULTIPLIER)

async def fast_fill(element, text):
    """Fast fill for experienced users - like autofill"""
    t('archive.testing.tests.test_investigations.debug_experienced_executor.fast_fill')
    await element.click()
    await asyncio.sleep(0.05)
    await element.fill('')
    await asyncio.sleep(0.05)
    await element.fill(text)
    await asyncio.sleep(0.1)

async def minimal_mouse_movement(page: Page):
    """Minimal mouse movement for experienced users"""
    t('archive.testing.tests.test_investigations.debug_experienced_executor.minimal_mouse_movement')
    logger = logging.getLogger('MouseMovement')
    logger.debug("Starting minimal_mouse_movement")
    x = random.randint(400, 800)
    y = random.randint(300, 600)
    logger.debug(f"Moving mouse to ({x}, {y})")
    await page.mouse.move(x, y)
    logger.debug("Mouse movement sleep 0.1s")
    await asyncio.sleep(0.1)
    logger.debug("minimal_mouse_movement complete")

async def find_time_slot_with_refresh(
    page: Page,
    time_slot: str,
    court_number: int,
    max_attempts: int = 5,
    refresh_delay: float = 1.5,
    logger: logging.Logger = None
) -> Optional[object]:
    """
    Find time slot button, refreshing page if needed
    """
    t('archive.testing.tests.test_investigations.debug_experienced_executor.find_time_slot_with_refresh')
    if not logger:
        logger = logging.getLogger('TimeSlotRefresher')
    
    logger.debug(f"Starting find_time_slot_with_refresh for {time_slot}")
    attempt = 0
    
    # Time slot formats to try
    time_formats = [
        time_slot,                    # "10:00" - exact match for 24-hour format
        time_slot.replace(':00', ''), # "10" - sometimes displayed without minutes
    ]
    
    # Try the new selector first
    try:
        logger.debug(f"Trying new selector: button.time-selection:has(p:text(\"{time_slot}\"))")
        time_button = await page.query_selector(
            f'button.time-selection:has(p:text("{time_slot}"))'
        )
        if time_button:
            logger.debug("Found button with new selector, checking visibility...")
            is_visible = await time_button.is_visible()
            is_enabled = await time_button.is_enabled()
            logger.debug(f"Button visible: {is_visible}, enabled: {is_enabled}")
            if is_visible and is_enabled:
                logger.info(f"Court {court_number}: Found {time_slot} using new selector")
                return time_button
    except Exception as e:
        logger.debug(f"New selector error: {e}")
    
    while attempt < max_attempts:
        attempt += 1
        logger.info(f"Court {court_number}: Attempt {attempt}/{max_attempts} to find {time_slot}")
        
        # Try each format
        for time_format in time_formats:
            try:
                logger.debug(f"Trying selector: button:has-text(\"{time_format}\")")
                # Look for time button
                time_button = await page.query_selector(
                    f'button:has-text("{time_format}")'
                )
                
                if time_button:
                    logger.debug(f"Found button for format {time_format}, checking state...")
                    # Verify button is visible and enabled
                    is_visible = await time_button.is_visible()
                    is_enabled = await time_button.is_enabled()
                    logger.debug(f"Button visible: {is_visible}, enabled: {is_enabled}")
                    
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
                logger.debug("Calling page.reload...")
                # Refresh the page
                await page.reload(wait_until='domcontentloaded')
                logger.debug("Page reload complete")
                
                # Wait for time buttons to potentially load
                try:
                    logger.debug("Waiting for selector button.time-selection...")
                    await page.wait_for_selector(
                        'button.time-selection',
                        timeout=5000,
                        state='visible'
                    )
                    logger.debug("Found time buttons, sleeping 0.5s")
                    # Give a moment for all buttons to load
                    await asyncio.sleep(0.5)
                except Exception as e:
                    logger.debug(f"No time buttons found after wait: {e}")
                
                # Additional delay between refreshes
                logger.debug(f"Refresh delay sleep {refresh_delay}s")
                await asyncio.sleep(refresh_delay)
                
            except Exception as e:
                logger.error(f"Court {court_number}: Refresh error: {e}")
                # Continue trying even if refresh fails
        
    logger.error(f"Court {court_number}: Could not find {time_slot} after {attempt} attempts")
    return None

class ExperiencedBookingExecutor:
    """Executor for experienced users with minimal delays"""
    
    def __init__(self, browser_pool=None):
        t('archive.testing.tests.test_investigations.debug_experienced_executor.ExperiencedBookingExecutor.__init__')
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
        t('archive.testing.tests.test_investigations.debug_experienced_executor.ExperiencedBookingExecutor.execute_booking')
        
        self.logger.debug(f"execute_booking called with court={court_number}, time={time_slot}")
        
        if not self.browser_pool:
            self.logger.error("Browser pool not initialized")
            return ExecutionResult(
                success=False,
                error_message="Browser pool not initialized"
            )
        
        try:
            self.logger.debug(f"Getting page for court {court_number} from browser pool...")
            page = await self.browser_pool.get_page(court_number)
            self.logger.debug(f"Got page: {page}")
            
            if not page:
                self.logger.error(f"Could not get page for court {court_number}")
                return ExecutionResult(
                    success=False,
                    error_message=f"Could not get page for court {court_number}"
                )
            
            self.logger.info(f"Starting EXPERIENCED booking: Court {court_number} at {time_slot}")
            
            # Minimal initial delay - experienced user knows the page
            delay = random.uniform(0.8, 1.2)
            self.logger.info(f"Minimal initial delay ({delay:.1f}s)")
            await asyncio.sleep(delay)
            self.logger.debug("Initial delay complete")
            
            # Quick mouse movement
            self.logger.debug("Starting mouse movement...")
            await minimal_mouse_movement(page)
            self.logger.debug("Mouse movement complete")
            
            # Find time slot with refresh capability
            self.logger.info(f"Looking for {time_slot} time slot...")
            
            # Find time slot with refresh
            time_button = await find_time_slot_with_refresh(
                page=page,
                time_slot=time_slot,
                court_number=court_number,
                max_attempts=5,
                refresh_delay=1.5,
                logger=self.logger
            )
            
            if not time_button:
                return ExecutionResult(
                    success=False,
                    court_number=court_number,
                    error_message=f"Time slot {time_slot} not found after refreshing"
                )
            
            self.logger.info(f"Found {time_slot} time slot!")
            
            # Rest of the booking process...
            self.logger.debug("Booking process would continue here...")
            
            return ExecutionResult(
                success=False,
                court_number=court_number,
                error_message="Debug version - stopped after finding time slot"
            )
                
        except Exception as e:
            self.logger.error(f"Booking error: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                court_number=court_number,
                error_message=str(e)
            )

# Test the debug version
async def test_debug_executor():
    """Test the debug executor to see where it gets stuck"""
    t('archive.testing.tests.test_investigations.debug_experienced_executor.test_debug_executor')
    import sys
    sys.path.append('/mnt/c/Documents/code/python/lvbot')
    from lvbot.utils.async_browser_pool import AsyncBrowserPool
    
    browser_pool = None
    try:
        print("=== TESTING DEBUG EXECUTOR ===")
        
        # Initialize browser pool
        browser_pool = AsyncBrowserPool()
        await browser_pool.start()
        
        # Create executor
        executor = ExperiencedBookingExecutor(browser_pool)
        
        # Test user info
        user_info = {
            'first_name': 'Saul',
            'last_name': 'Campos',
            'phone': '12345678',
            'email': 'saul@example.com'
        }
        
        # Try booking
        result = await executor.execute_booking(
            court_number=3,
            target_date=datetime(2025, 7, 31),
            time_slot="09:00",
            user_info=user_info
        )
        
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if browser_pool:
            await browser_pool.close()

if __name__ == "__main__":
    asyncio.run(test_debug_executor())