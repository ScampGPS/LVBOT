"""
Availability Checker V3 - Refactored Modular Implementation
===========================================================

PURPOSE: Check court availability with modular, DRY architecture
PATTERN: Composition of single-responsibility components
SCOPE: Court availability checking with proper separation of concerns

This is the refactored version that uses:
- constants.py for all configuration
- time_slot_extractor.py for DOM extraction
- day_mapper.py for date mapping
"""

import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import date, datetime, timedelta
from playwright.async_api import Page, Browser

from .constants import (
    COURT_CONFIG, 
    NO_AVAILABILITY_PATTERNS,
    SCHEDULING_IFRAME_URL_PATTERN,
    BrowserTimeouts
)
from .time_slot_extractor import TimeSlotExtractor
from .day_mapper import DayMapper
from .time_order_extraction import AcuityTimeParser

logger = logging.getLogger(__name__)


class AvailabilityCheckerV3:
    """
    Modular availability checker using composition pattern.
    Delegates specific responsibilities to specialized components.
    """
    
    def __init__(self, browser_pool):
        """
        Initialize with browser pool and component instances.
        
        Args:
            browser_pool: AsyncBrowserPool instance
        """
        self.browser_pool = browser_pool
        self.time_extractor = TimeSlotExtractor()
        self.day_mapper = DayMapper()
        self.acuity_parser = AcuityTimeParser()  # Use proper time-order extraction
        
    async def check_all_courts_parallel(self) -> Dict[int, List]:
        """
        Check all courts in parallel (backward compatibility method).
        
        Returns:
            Dict mapping court number to list of available time slots
        """
        # Call the main check_availability method
        results = await self.check_availability()
        
        # Convert to backward-compatible format
        # Old format: {court_num: ["06:00", "07:00"]}
        # New format: {court_num: {"2025-07-30": ["06:00", "07:00"]}}
        compatible_results = {}
        
        for court_num, dates_data in results.items():
            # Handle error cases
            if isinstance(dates_data, dict) and "error" in dates_data:
                compatible_results[court_num] = []
                continue
                
            # Flatten all times from all dates
            all_times = []
            for date_str, times in dates_data.items():
                all_times.extend(times)
                
            compatible_results[court_num] = sorted(list(set(all_times)))
            
        return compatible_results
    
    async def check_availability(
        self, 
        court_numbers: Optional[List[int]] = None,
        max_concurrent: int = 3,
        timeout_per_court: float = 30.0
    ) -> Dict[int, Dict[str, List[str]]]:
        """
        Check availability for specified courts or all courts.
        
        Args:
            court_numbers: List of court numbers to check (None = all)
            max_concurrent: Max concurrent court checks
            timeout_per_court: Timeout per court in seconds
            
        Returns:
            Dict mapping court number to date->times availability
        """
        # Default to all courts if none specified
        if court_numbers is None:
            court_numbers = list(COURT_CONFIG.keys())
        
        # Validate court numbers
        valid_courts = [c for c in court_numbers if c in COURT_CONFIG]
        if len(valid_courts) < len(court_numbers):
            invalid = set(court_numbers) - set(valid_courts)
            logger.warning(f"Invalid court numbers: {invalid}")
            
        # Create tasks for concurrent checking
        tasks = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        for court_num in valid_courts:
            task = self._check_with_semaphore(
                court_num, semaphore, timeout_per_court
            )
            tasks.append(task)
            
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        availability = {}
        for court_num, result in zip(valid_courts, results):
            if isinstance(result, Exception):
                logger.error(f"Court {court_num} check failed: {result}")
                availability[court_num] = {"error": str(result)}
            else:
                availability[court_num] = result
                
        return availability
    
    async def _check_with_semaphore(
        self, 
        court_num: int, 
        semaphore: asyncio.Semaphore,
        timeout: float
    ) -> Dict[str, List[str]]:
        """
        Check single court with semaphore for concurrency control.
        """
        async with semaphore:
            try:
                return await asyncio.wait_for(
                    self.check_single_court(court_num),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"Court {court_num} check timed out after {timeout}s")
                return {"error": f"Timeout after {timeout}s"}
    
    async def check_single_court(self, court_num: int) -> Dict[str, List[str]]:
        """
        Check availability for a single court.
        
        Args:
            court_num: Court number to check
            
        Returns:
            Dict mapping date to list of available times
        """
        court_config = COURT_CONFIG.get(court_num)
        if not court_config:
            raise ValueError(f"Invalid court number: {court_num}")
            
        court_url = court_config["direct_url"]
        logger.info(f"Checking Court {court_num} availability")
        
        # Get the pre-loaded page for this court
        page = self.browser_pool.pages.get(court_num)
        if not page:
            raise RuntimeError(f"No page available for court {court_num}")
            
        try:
            # Reload page to get fresh data
            await page.reload(wait_until='domcontentloaded')
            await asyncio.sleep(1)  # Let dynamic content load
            
            # Since we're using direct court URLs, we're already on the scheduling page
            # No need to look for iframe - we ARE the scheduling page
            context = page
            logger.debug(f"Court {court_num}: Using page directly (URL: {page.url})")
                
            # Check for no availability message
            if await self._has_no_availability_message(context):
                logger.info(f"Court {court_num}: No availability")
                return {}
                
            # Use AcuityTimeParser for proper time-order extraction
            # This will correctly group times by day based on time order
            result = await self.acuity_parser.extract_times_by_day(context)
            
            if not result:
                logger.warning(f"Court {court_num}: No times found by AcuityTimeParser")
                return {}
                
            # Log what we found
            total_times = sum(len(times) for times in result.values())
            logger.info(f"Court {court_num}: Found {total_times} time slots across {len(result)} days")
            for date_str, times in result.items():
                logger.debug(f"  {date_str}: {times}")
                
            return result
            
        except Exception as e:
            logger.error(f"Error checking Court {court_num}: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def _wait_for_scheduling_iframe(
        self, 
        page: Page,
        timeout: float = 15.0
    ) -> Optional[Page]:
        """
        Wait for scheduling iframe to load and return its context.
        
        Args:
            page: Main page object
            timeout: Max wait time in seconds
            
        Returns:
            Iframe page context or None
        """
        try:
            # Wait for iframe to appear
            iframe_element = await page.wait_for_selector(
                f'iframe[src*="{SCHEDULING_IFRAME_URL_PATTERN}"]',
                timeout=timeout * 1000
            )
            
            if not iframe_element:
                logger.error("No scheduling iframe found")
                return None
                
            # Get iframe content
            iframe = await iframe_element.content_frame()
            if not iframe:
                logger.error("Could not access iframe content")
                return None
                
            # Wait for iframe to be ready
            await iframe.wait_for_load_state('domcontentloaded')
            return iframe
            
        except Exception as e:
            logger.error(f"Error waiting for iframe: {e}")
            return None
    
    async def _has_no_availability_message(self, page: Page) -> bool:
        """
        Check if page displays no availability message.
        
        Args:
            page: Page or iframe context
            
        Returns:
            True if no availability message found
        """
        try:
            # Check for any no availability pattern
            for pattern in NO_AVAILABILITY_PATTERNS.get('es', []):
                elements = await page.query_selector_all(f'*:has-text("{pattern}")')
                if elements:
                    return True
                    
            # Also check English patterns
            for pattern in NO_AVAILABILITY_PATTERNS.get('en', []):
                elements = await page.query_selector_all(f'*:has-text("{pattern}")')
                if elements:
                    return True
                    
            return False
            
        except Exception as e:
            logger.debug(f"Error checking no availability: {e}")
            return False
    
    async def get_next_available_slot(
        self,
        court_numbers: Optional[List[int]] = None,
        min_time: Optional[str] = None,
        max_time: Optional[str] = None
    ) -> Optional[Tuple[int, date, str]]:
        """
        Find the next available slot across specified courts.
        
        Args:
            court_numbers: Courts to check (None = all)
            min_time: Minimum time (e.g., "07:00")
            max_time: Maximum time (e.g., "13:00")
            
        Returns:
            Tuple of (court_number, date, time) or None
        """
        availability = await self.check_availability(court_numbers)
        
        # Find earliest slot that meets criteria
        earliest = None
        for court_num, dates in availability.items():
            if isinstance(dates, dict) and "error" in dates:
                continue
                
            for date_str, times in dates.items():
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                
                for time in times:
                    # Apply time filters if provided
                    if min_time and time < min_time:
                        continue
                    if max_time and time > max_time:
                        continue
                        
                    # Check if this is the earliest so far
                    if not earliest or (date_obj, time) < (earliest[1], earliest[2]):
                        earliest = (court_num, date_obj, time)
                        
        return earliest
    
    def format_availability_message(
        self, 
        availability: Dict[int, Dict[str, List[str]]]
    ) -> str:
        """
        Format availability data into user-friendly message.
        
        Args:
            availability: Raw availability data
            
        Returns:
            Formatted message string
        """
        if not availability:
            return "No hay disponibilidad en ninguna cancha"
            
        lines = ["🎾 *Disponibilidad de Canchas*\n"]
        
        for court_num in sorted(availability.keys()):
            court_data = availability[court_num]
            
            # Handle error cases
            if isinstance(court_data, dict) and "error" in court_data:
                lines.append(f"*Cancha {court_num}:* ❌ Error al verificar")
                continue
                
            # Handle no availability
            if not court_data:
                lines.append(f"*Cancha {court_num}:* Sin disponibilidad")
                continue
                
            # Format available times
            lines.append(f"*Cancha {court_num}:*")
            for date_str in sorted(court_data.keys()):
                times = court_data[date_str]
                if times:
                    # Convert date string to readable format
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                    today = date.today()
                    
                    if date_obj == today:
                        day_label = "Hoy"
                    elif date_obj == today + timedelta(days=1):
                        day_label = "Mañana"
                    else:
                        day_label = date_obj.strftime("%d/%m")
                        
                    times_str = ", ".join(sorted(times))
                    lines.append(f"  • {day_label}: {times_str}")
                    
        return "\n".join(lines)