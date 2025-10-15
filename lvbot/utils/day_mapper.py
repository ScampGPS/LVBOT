"""
Day Mapper Module
================

PURPOSE: Map Spanish day names to dates and organize times by day
PATTERN: Single responsibility - Date/time mapping logic
SCOPE: Spanish to date conversion and time organization

Handles the logic of mapping day labels to actual dates.
"""

import logging
from typing import Dict, List, Tuple
from datetime import date, timedelta
from playwright.async_api import Page

logger = logging.getLogger(__name__)


class DayMapper:
    """
    Maps Spanish day names to dates and organizes times by day.
    Single responsibility: Date mapping and time organization.
    """
    
    # Spanish day name mappings
    SPANISH_DAYS = {
        'hoy': 0,           # Today
        'mañana': 1,        # Tomorrow  
        'pasado mañana': 2,  # Day after tomorrow
        'esta semana': 2     # This week (typically day after tomorrow)
    }
    
    # CSS selectors for day elements
    DAY_SELECTORS = [
        '.css-gy5kwb',      # Regular day container
        '.css-42ma5j',      # Alternative day container
        '[class*="day"]',   # Any class containing "day"
        '.day-label'        # Common day label class
    ]
    
    @classmethod
    async def extract_day_labels(cls, page: Page) -> List[str]:
        """
        Extract day labels from the page.
        
        Args:
            page: Playwright page object
            
        Returns:
            List of day label strings
        """
        day_labels = []
        
        for selector in cls.DAY_SELECTORS:
            try:
                elements = await page.query_selector_all(selector)
                for elem in elements:
                    text = await elem.text_content()
                    if text:
                        day_labels.append(text.strip().lower())
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {e}")
                
        logger.info(f"Extracted day labels: {day_labels}")
        return day_labels
    
    @classmethod
    def map_labels_to_dates(cls, day_labels: List[str]) -> Dict[str, date]:
        """
        Map Spanish day labels to actual dates.
        
        Args:
            day_labels: List of Spanish day labels
            
        Returns:
            Dict mapping label to date
        """
        today = date.today()
        date_mapping = {}
        
        # Process each label
        for label in day_labels:
            # Check for known Spanish day names
            for spanish_day, days_offset in cls.SPANISH_DAYS.items():
                if spanish_day in label:
                    target_date = today + timedelta(days=days_offset)
                    date_mapping[label] = target_date
                    break
                    
        return date_mapping
    
    @classmethod
    def distribute_times_to_days(
        cls, 
        times: List[str], 
        day_labels: List[str]
    ) -> Dict[date, List[str]]:
        """
        Distribute times across identified days.
        
        This is a heuristic approach since Acuity shows times in order
        but doesn't directly associate each time with its day.
        
        Args:
            times: List of all time strings
            day_labels: List of day labels found on page
            
        Returns:
            Dict mapping date to list of times
        """
        today = date.today()
        result = {}
        
        # Map labels to dates
        date_mapping = cls.map_labels_to_dates(day_labels)
        
        if not date_mapping:
            # No day labels found, assume all times are for tomorrow
            logger.warning("No day labels found, assuming all times are for tomorrow")
            tomorrow = today + timedelta(days=1)
            result[tomorrow] = times
            return result
        
        # Simple distribution heuristic
        # Acuity typically shows fewer slots for today, more for future days
        dates = sorted(date_mapping.values())
        
        if len(dates) == 1:
            # All times for one day
            result[dates[0]] = times
        elif len(dates) == 2:
            # Split between two days (typically today has fewer)
            if dates[0] == today:
                # Today gets first 1-2 slots, rest for tomorrow
                today_count = min(2, len(times))
                result[dates[0]] = times[:today_count]
                result[dates[1]] = times[today_count:]
            else:
                # Split evenly
                mid = len(times) // 2
                result[dates[0]] = times[:mid]
                result[dates[1]] = times[mid:]
        else:
            # Multiple days - distribute based on typical patterns
            if dates[0] == today:
                # Today: 1-2 slots
                # Tomorrow: 4-5 slots  
                # Day after: remaining
                today_count = min(2, len(times))
                tomorrow_count = min(5, len(times) - today_count)
                
                result[dates[0]] = times[:today_count]
                if len(dates) > 1:
                    result[dates[1]] = times[today_count:today_count + tomorrow_count]
                if len(dates) > 2:
                    result[dates[2]] = times[today_count + tomorrow_count:]
            else:
                # Distribute more evenly
                slots_per_day = len(times) // len(dates)
                remainder = len(times) % len(dates)
                
                start = 0
                for i, date_obj in enumerate(dates):
                    count = slots_per_day + (1 if i < remainder else 0)
                    result[date_obj] = times[start:start + count]
                    start += count
                    
        return result