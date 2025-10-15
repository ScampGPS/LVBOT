"""
Availability Checker V2 - Clean implementation with correct selectors
Replaces the old availability checking that uses outdated AM/PM selectors
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date, timedelta
from playwright.async_api import Page, Frame

logger = logging.getLogger(__name__)

class AvailabilityCheckerV2:
    """
    New availability checker with correct selectors for the current website.
    This replaces the old implementation that looks for AM/PM buttons.
    """
    
    # Correct selectors for the current Acuity site
    TIME_BUTTON_SELECTOR = 'button.time-selection'
    DAY_CONTAINER_SELECTOR = '.css-yl3rn6'  # Container with day buttons
    
    def __init__(self, browser_pool):
        self.pool = browser_pool
        self.logger = logger
        
    async def check_all_courts_parallel(self) -> Dict[int, List]:
        """
        Legacy interface for compatibility with existing code.
        Returns data in the old format expected by callback handlers.
        """
        # Get data in new format
        new_format_data = await self.check_all_courts()
        
        # Convert to old format: Dict[court_num, List[TimeSlot objects]]
        old_format_data = {}
        
        # Import TimeSlot if available, otherwise use a simple dict
        try:
            from lvbot.domain.models.time_slot import TimeSlot
            use_timeslot = True
        except ImportError:
            use_timeslot = False
        
        for court_num, dates_dict in new_format_data.items():
            slots = []
            for date_str, times in dates_dict.items():
                for time_str in times:
                    if use_timeslot:
                        try:
                            # Create TimeSlot object
                            slot = TimeSlot(
                                start_time=time_str,
                                end_time=self._add_hour(time_str),
                                court=court_num,
                                available=True
                            )
                            slots.append(slot)
                        except:
                            # Fallback to dict if TimeSlot creation fails
                            slots.append({
                                'time': time_str,
                                'date': date_str,
                                'court': court_num
                            })
                    else:
                        slots.append({
                            'time': time_str,
                            'date': date_str,
                            'court': court_num
                        })
            old_format_data[court_num] = slots
        
        return old_format_data
    
    def _add_hour(self, time_str: str) -> str:
        """Add one hour to a time string"""
        try:
            hour = int(time_str.split(':')[0])
            minute = time_str.split(':')[1] if ':' in time_str else '00'
            hour = (hour + 1) % 24
            return f"{hour:02d}:{minute}"
        except:
            return time_str
    
    async def check_all_courts(self) -> Dict[int, Dict[str, List[str]]]:
        """
        Check availability for all courts and return times by date.
        
        Returns:
            Dict mapping court number to dict of date -> list of times
            Example: {1: {"2025-07-30": ["06:00", "10:00", "11:00"]}}
        """
        results = {}
        
        # Check each court in parallel
        tasks = []
        for court_num in [1, 2, 3]:
            tasks.append(self.check_single_court(court_num))
        
        court_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for court_num, result in zip([1, 2, 3], court_results):
            if isinstance(result, Exception):
                self.logger.error(f"Court {court_num}: Error - {result}")
                results[court_num] = {}
            else:
                results[court_num] = result
                total_slots = sum(len(times) for times in result.values())
                self.logger.info(f"Court {court_num}: Found {total_slots} total time slots across {len(result)} days")
        
        return results
    
    async def check_single_court(self, court_num: int) -> Dict[str, List[str]]:
        """
        Check availability for a single court.
        
        Args:
            court_num: Court number (1, 2, or 3)
            
        Returns:
            Dict mapping date to list of available times
        """
        try:
            page = await self.pool.get_page(court_num)
            if not page:
                self.logger.error(f"Court {court_num}: No page available")
                return {}
            
            # Refresh page to ensure latest data
            await page.reload(wait_until='networkidle')
            await asyncio.sleep(1)  # Let dynamic content load
                
            # Wait for time buttons to be visible
            try:
                await page.wait_for_selector(self.TIME_BUTTON_SELECTOR, timeout=10000)
            except:
                self.logger.warning(f"Court {court_num}: No time buttons found after wait")
                # Try one more time with direct navigation
                court_url = f"https://clublavilla.as.me/schedule/7d558012/appointment/{self._get_appointment_id(court_num)}/calendar/{self._get_calendar_id(court_num)}?appointmentTypeIds[]={self._get_appointment_id(court_num)}"
                await page.goto(court_url, wait_until='networkidle')
                await asyncio.sleep(2)
                
            # Extract all time buttons
            time_buttons = await page.query_selector_all(self.TIME_BUTTON_SELECTOR)
            self.logger.info(f"Court {court_num}: Found {len(time_buttons)} time buttons")
            
            if not time_buttons:
                return {}
            
            # Extract times and their associated days
            times_by_day = await self._extract_times_by_day(page, time_buttons)
            
            return times_by_day
            
        except Exception as e:
            self.logger.error(f"Court {court_num}: Error checking availability: {e}")
            return {}
    
    def _get_appointment_id(self, court_num: int) -> str:
        """Get appointment ID for court"""
        mapping = {1: "15970897", 2: "16021953", 3: "16120442"}
        return mapping.get(court_num, "")
    
    def _get_calendar_id(self, court_num: int) -> str:
        """Get calendar ID for court"""
        mapping = {1: "4282490", 2: "4291312", 3: "4307254"}
        return mapping.get(court_num, "")
    
    async def _extract_times_by_day(self, page: Page, time_buttons: list) -> Dict[str, List[str]]:
        """
        Extract times and group them by day.
        The page shows multiple days, we need to figure out which times belong to which day.
        """
        times_by_day = {}
        
        # Get day labels (hoy, mañana, esta semana)
        day_elements = await page.query_selector_all('.css-gy5kwb, .css-42ma5j')
        day_info = []
        
        for elem in day_elements:
            day_text = await elem.text_content()
            if day_text:
                day_info.append(day_text.strip())
        
        self.logger.info(f"Found day markers: {day_info}")
        
        # Map Spanish day names to dates
        today = date.today()
        tomorrow = today + timedelta(days=1)
        day_after = today + timedelta(days=2)
        
        # Extract all times
        all_times = []
        for button in time_buttons:
            time_text = await button.text_content()
            if time_text:
                all_times.append(time_text.strip())
        
        self.logger.info(f"All times found: {all_times}")
        
        # Simple heuristic: distribute times across days
        # The page typically shows times for multiple days in order
        if 'hoy' in ' '.join(day_info).lower():
            # Today's times are usually first few
            today_count = min(2, len(all_times))  # Usually fewer slots for today
            times_by_day[today.strftime('%Y-%m-%d')] = all_times[:today_count]
            all_times = all_times[today_count:]
        
        if 'mañana' in ' '.join(day_info).lower() and all_times:
            # Tomorrow usually has more slots
            tomorrow_count = min(4, len(all_times))
            times_by_day[tomorrow.strftime('%Y-%m-%d')] = all_times[:tomorrow_count]
            all_times = all_times[tomorrow_count:]
        
        if all_times:  # Remaining times are for day after tomorrow
            times_by_day[day_after.strftime('%Y-%m-%d')] = all_times
        
        return times_by_day
    
    async def find_time_button(self, page: Page, time_slot: str) -> Optional[object]:
        """
        Find a specific time button on the page.
        
        Args:
            page: Playwright page object
            time_slot: Time to find (e.g., "06:00", "10:00")
            
        Returns:
            Button element if found, None otherwise
        """
        # Try multiple selector strategies
        selectors = [
            f'button.time-selection:has(p:text("{time_slot}"))',
            f'button[aria-label*="{time_slot}"]',
            f'button:has-text("{time_slot}")'
        ]
        
        for selector in selectors:
            try:
                button = await page.query_selector(selector)
                if button and await button.is_visible():
                    self.logger.info(f"Found time button for {time_slot} using selector: {selector}")
                    return button
            except:
                continue
                
        self.logger.warning(f"Could not find time button for {time_slot}")
        return None


# Deprecated function that redirects to new implementation
async def check_availability_deprecated(browser_pool):
    """
    DEPRECATED: Use AvailabilityCheckerV2 instead.
    This function is kept for backward compatibility.
    """
    logger.warning("Using deprecated check_availability function. Please update to AvailabilityCheckerV2")
    checker = AvailabilityCheckerV2(browser_pool)
    return await checker.check_all_courts()