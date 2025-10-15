import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, date, timedelta
from playwright.async_api import Page, Frame
from .async_browser_pool import AsyncBrowserPool
from .async_browser_helpers import BrowserHelpers
from .court_availability import CourtAvailability
from .acuity_page_validator import AcuityPageValidator
from .constants import BOOKING_URL, BOOKING_WINDOW_HOURS
from lvbot.domain.models.time_slot import TimeSlot

logger = logging.getLogger(__name__)

class AsyncAvailabilityChecker:
    """Parallel availability checking using asyncio.gather()
    REPLACES existing availability checker
    
    DEPRECATED: This class uses outdated selectors that look for AM/PM buttons.
    The website now uses 24-hour format (06:00, not 6:00 AM) and different selectors.
    Use AvailabilityCheckerV2 from availability_checker_v2.py instead.
    """
    
    def __init__(self, browser_pool: AsyncBrowserPool):
        self.pool = browser_pool
        
    async def check_court(self, court_num: int) -> List[TimeSlot]:
        """
        Check single court availability using modular validation approach
        
        Trusts browser pool navigation and focuses on content readiness rather than
        strict URL matching. Allows Acuity's natural redirect patterns.
        
        Args:
            court_num: The court number to check
            
        Returns:
            List of available TimeSlot objects for the court
        """
        try:
            page = await self.pool.get_page(court_num)
            
            # Use modular validation to check if page is ready
            if not await AcuityPageValidator.is_page_ready_for_extraction(page, court_num):
                logger.warning(f"Court {court_num}: Page not ready for extraction, trying fallback")
                return await self._fallback_check_court(court_num)
            
            # Extract times from the ready page
            return await self._extract_court_times(page, court_num)
            
        except Exception as e:
            logger.error(f"Court {court_num}: Error checking availability: {e}")
            return await self._fallback_check_court(court_num)
    
    async def _extract_court_times(self, page: Page, court_num: int) -> List[TimeSlot]:
        """
        Extract available times from a validated page
        
        Single responsibility: extract times from page that's already validated
        as ready for extraction.
        
        Args:
            page: The browser page (already validated)
            court_num: The court number for context
            
        Returns:
            List of available TimeSlot objects
        """
        try:
            # Get the appropriate frame for extraction
            frame = await AcuityPageValidator._get_extraction_frame(page)
            if not frame:
                logger.warning(f"Court {court_num}: No extraction frame available")
                return []
            
            # Extract available times from the frame
            available_times = await CourtAvailability.extract_times_from_page(frame)
            
            # Convert to TimeSlot objects
            time_slots = []
            for time_str in available_times:
                try:
                    time_slots.append(TimeSlot(
                        start_time=time_str,
                        end_time=self._add_hour(time_str),
                        court=court_num,
                        available=True
                    ))
                except Exception as e:
                    logger.debug(f"Court {court_num}: Error parsing time {time_str}: {e}")
            
            logger.info(f"Court {court_num}: Found {len(time_slots)} available slots")
            return time_slots
            
        except Exception as e:
            logger.error(f"Court {court_num}: Error extracting times: {e}")
            return []
        
    async def check_all_courts_parallel(self) -> Dict[int, List[TimeSlot]]:
        """
        Refresh all pages then check availability in parallel
        Court pages show all available days, so no target date needed.
            
        Returns:
            Dictionary mapping court numbers to lists of available TimeSlots
        """
        # First refresh all pages to get latest data - use calendar mode to ensure we're on the right page
        logger.info("Refreshing all court pages to calendar view before availability check")
        await self.pool.refresh_all_pages(refresh_type="calendar")
        
        # Then check all courts in parallel (pages already at correct URLs)
        logger.info("Checking availability on all courts in parallel")
        tasks = [self.check_court(court) for court in self.pool.courts]
        results = await asyncio.gather(*tasks)
        return dict(zip(self.pool.courts, results))
    
    async def _fallback_check_court(self, court_num: int) -> List[TimeSlot]:
        """
        Fallback method when normal extraction fails - try direct navigation
        
        Args:
            court_num: The court number to check
            
        Returns:
            List of available TimeSlot objects for the court
        """
        try:
            logger.warning(f"Court {court_num}: Using fallback direct navigation")
            page = await self.pool.get_page(court_num)
            
            # Try direct navigation as fallback
            if await self._try_direct_navigation(page, court_num):
                logger.info(f"Court {court_num}: Fallback navigation successful")
                
                # Use modular approach for fallback extraction too
                logger.info(f"Court {court_num}: Fallback - validating page after navigation")
                
                if await AcuityPageValidator.is_page_ready_for_extraction(page, court_num):
                    return await self._extract_court_times(page, court_num)
                else:
                    logger.warning(f"Court {court_num}: Fallback page still not ready for extraction")
                    return []
            else:
                logger.error(f"Court {court_num}: Fallback navigation also failed")
                return []
                
        except Exception as e:
            logger.error(f"Court {court_num}: Fallback method failed: {e}")
            return []
    
    async def _try_direct_navigation(self, page: Page, court_num: int) -> bool:
        """
        Try to navigate directly to court-specific URL
        
        Args:
            page: The browser page
            court_num: The court number
            
        Returns:
            True if direct navigation succeeded, False otherwise
        """
        try:
            if court_num not in self.pool.DIRECT_COURT_URLS:
                logger.debug(f"Court {court_num}: No direct URL available")
                return False
                
            court_url = self.pool.DIRECT_COURT_URLS[court_num]
            logger.info(f"Court {court_num}: Navigating directly to {court_url}")
            
            await page.goto(court_url, wait_until='domcontentloaded', timeout=15000)
            logger.info(f"Court {court_num}: Direct navigation completed successfully")
            return True
            
        except Exception as e:
            logger.warning(f"Court {court_num}: Direct navigation failed: {e}")
            return False
    
    async def _try_fallback_navigation(self, page: Page, court_num: int) -> bool:
        """
        Fallback to original navigation method via main booking page
        
        Args:
            page: The browser page
            court_num: The court number
            
        Returns:
            True if fallback navigation succeeded, False otherwise
        """
        try:
            logger.info(f"Court {court_num}: Using fallback navigation to main booking page")
            await page.goto(BOOKING_URL, wait_until='domcontentloaded', timeout=15000)
            
            # Get the scheduling frame
            frame = await AsyncBrowserHelpers.get_scheduling_frame(page)
            if not frame:
                logger.error(f"Court {court_num}: Could not find scheduling iframe in fallback")
                return False
            
            # Try to navigate to specific court if available
            try:
                # Look for court selection buttons
                court_buttons = await frame.query_selector_all(f'button:has-text("Court {court_num}"), button:has-text("Cancha {court_num}"), button:has-text("TENNIS CANCHA {court_num}")')
                if court_buttons:
                    for button in court_buttons:
                        if await button.is_visible():
                            logger.info(f"Court {court_num}: Found court button in fallback, clicking...")
                            await button.click()
                            await frame.wait_for_load_state('domcontentloaded', timeout=5000)
                            break
                else:
                    logger.info(f"Court {court_num}: No court-specific button found in fallback")
            except Exception as e:
                logger.debug(f"Court {court_num}: Error during fallback court navigation: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Court {court_num}: Fallback navigation also failed: {e}")
            return False
    
    async def _check_date_availability(self, frame: Frame, target_date: date) -> List[str]:
        """
        Check availability for a specific date
        
        Args:
            frame: The scheduling iframe
            target_date: The date to check
            
        Returns:
            List of available time strings
        """
        try:
            # Calculate days from today
            today = date.today()
            days_diff = (target_date - today).days
            
            if days_diff < 0:
                logger.warning(f"Target date {target_date} is in the past")
                return []
            
            # Wait for calendar elements to be present
            try:
                await frame.wait_for_selector('button, .time-slot, .calendar-day', timeout=5000)
            except:
                logger.warning("Calendar elements not found within timeout")
            
            # Navigate to the correct day if needed
            if days_diff == 0:
                # Today - check if we're on today's page
                found_today, today_times = await CourtAvailability.look_for_today(frame)
                if found_today:
                    return today_times
            elif days_diff == 1:
                # Tomorrow - navigate if needed
                found_tomorrow, tomorrow_times = await CourtAvailability.look_for_tomorrow(frame)
                if not found_tomorrow:
                    # Try to navigate to tomorrow
                    if await CourtAvailability.try_navigate_next(frame):
                        found_tomorrow, tomorrow_times = await CourtAvailability.look_for_tomorrow(frame)
                if found_tomorrow:
                    return tomorrow_times
            elif days_diff == 2:
                # Day after tomorrow
                if CourtAvailability.is_day_after_feasible():
                    # Navigate twice if needed
                    navigation_count = 0
                    for _ in range(2):
                        if await CourtAvailability.try_navigate_next(frame):
                            navigation_count += 1
                        else:
                            break
                    
                    if navigation_count > 0:
                        found_day_after, day_after_times = await CourtAvailability.look_for_day_after(frame)
                        if found_day_after:
                            return day_after_times
            else:
                # For dates beyond 2 days, try generic navigation
                logger.info(f"Target date {target_date} is {days_diff} days away, attempting navigation...")
                
                # Try to find a date picker or calendar widget
                try:
                    # Look for date input or calendar button
                    date_selectors = [
                        f'input[type="date"]',
                        f'button:has-text("{target_date.strftime("%d")}")',
                        f'td:has-text("{target_date.strftime("%d")}")',
                        f'.calendar-day:has-text("{target_date.strftime("%d")}")'
                    ]
                    
                    for selector in date_selectors:
                        elem = await frame.query_selector(selector)
                        if elem and await elem.is_visible():
                            await elem.click()
                            await frame.wait_for_load_state('domcontentloaded', timeout=3000)
                            break
                except Exception as e:
                    logger.debug(f"Error navigating to specific date: {e}")
            
            # After navigation attempts, extract any visible times
            times = await CourtAvailability.extract_times_from_page(frame)
            return times
            
        except Exception as e:
            logger.error(f"Error checking date availability: {e}")
            return []
    
    def _add_hour(self, time_str: str) -> str:
        """
        Add one hour to a time string
        
        Args:
            time_str: Time string (e.g., "10:00 AM" or "10:00")
            
        Returns:
            Time string one hour later
        """
        try:
            # Try parsing with AM/PM
            try:
                time_obj = datetime.strptime(time_str, "%I:%M %p")
            except:
                # Try 24-hour format
                time_obj = datetime.strptime(time_str, "%H:%M")
            
            # Add one hour
            end_time = time_obj + timedelta(hours=1)
            
            # Return in same format as input
            if "AM" in time_str or "PM" in time_str:
                return end_time.strftime("%I:%M %p").lstrip("0")
            else:
                return end_time.strftime("%H:%M")
        except:
            # If parsing fails, just append estimate
            return f"{time_str} + 1h"
