"""
Time Order Extraction - New modular approach for extracting day-specific times

This module replaces the broken DOM traversal methods with a simple time-order algorithm:
- Extract all time buttons in DOM order
- When time goes backward, assume it's the next day
- Group times by detected days from page text

Classes:
    DayDetector: Detects available days from page text content
    TimeOrderExtractor: Extracts and groups times using order logic
    AcuityTimeParser: Main orchestrator class
"""

from datetime import datetime, date
from typing import List, Dict, Optional
from playwright.async_api import Frame
import logging

logger = logging.getLogger(__name__)


class DayDetector:
    """
    Single responsibility: Detect available days from page text content
    Follows DRY principle by centralizing all day detection logic
    """
    
    DAY_PATTERNS = {
        'hoy': ['hoy'],
        'mañana': ['mañana', 'manana'],  # Account for accent variations
        'esta semana': ['esta semana', 'estasemana'],
        'la próxima semana': ['la próxima semana', 'próxima semana']
    }
    
    @staticmethod
    def hasday(text_content: str, day_label: str) -> bool:
        """
        Modular day detection function
        
        Args:
            text_content: Raw text from DOM
            day_label: Day to check for ("hoy", "mañana", "esta semana")
            
        Returns:
            True if day is found in text
        """
        if not text_content or not day_label:
            return False
            
        text_lower = text_content.lower()
        patterns = DayDetector.DAY_PATTERNS.get(day_label.lower(), [day_label.lower()])
        
        return any(pattern in text_lower for pattern in patterns)
    
    @staticmethod
    def get_available_days(text_content: str) -> List[str]:
        """
        Get ordered list of available days from text content
        
        Args:
            text_content: Raw text from DOM
            
        Returns:
            Ordered list of day labels found in text
        """
        available_days = []
        
        # Check in logical order (today -> tomorrow -> day after)
        for day_key in ['hoy', 'mañana', 'esta semana', 'la próxima semana']:
            if DayDetector.hasday(text_content, day_key):
                available_days.append(day_key)
        
        logger.info(f"DayDetector found {len(available_days)} days: {available_days}")
        return available_days
    
    @staticmethod
    async def extract_page_text_content(frame: Frame) -> str:
        """
        Extract text content for day detection
        
        Args:
            frame: The page frame to extract text from
            
        Returns:
            Raw text content from page
        """
        try:
            # Get text from the main calendar container
            text_content = await frame.evaluate('() => document.body.textContent || ""')
            logger.debug(f"Extracted text content length: {len(text_content)} chars")
            return text_content.strip()
        except Exception as e:
            logger.warning(f"Failed to extract page text content: {e}")
            return ""


class TimeOrderExtractor:
    """
    Single responsibility: Extract time buttons and apply time-order grouping logic
    Replaces all broken DOM traversal methods
    """
    
    async def extract_raw_time_buttons(self, frame: Frame) -> List[Dict[str, str]]:
        """
        Extract flat list of time buttons in DOM order
        
        Args:
            frame: The page frame to extract time buttons from
            
        Returns:
            List of {time: "09:00", order: 0} dictionaries in DOM order
        """
        try:
            time_buttons = await frame.evaluate('''() => {
                const buttons = document.querySelectorAll('button.time-selection');
                const results = [];
                
                buttons.forEach((button, index) => {
                    const timeText = button.textContent?.trim();
                    if (timeText && /^\\d{1,2}:\\d{2}$/.test(timeText)) {
                        results.push({
                            time: timeText,
                            order: index
                        });
                    }
                });
                
                return results;
            }''')
            
            logger.info(f"TimeOrderExtractor found {len(time_buttons or [])} time buttons")
            return time_buttons or []
            
        except Exception as e:
            logger.error(f"Failed to extract time buttons: {e}")
            return []
    
    def group_times_by_order_logic(self, time_buttons: List[Dict], available_days: List[str]) -> Dict[str, List[str]]:
        """
        Apply time-order algorithm to group times by day
        
        Logic: When time goes backward or stays same, move to next day
        
        Args:
            time_buttons: List of time button data from extract_raw_time_buttons()
            available_days: List of day labels from DayDetector
            
        Returns:
            Dictionary mapping day labels to time lists
        """
        if not time_buttons or not available_days:
            logger.warning("No time buttons or available days provided")
            return {}
        
        # Initialize matrix for available days
        matrix = {day: [] for day in available_days}
        day_keys = list(matrix.keys())
        
        current_day_index = 0
        previous_hour = -1
        
        logger.info(f"Starting time order grouping with {len(time_buttons)} buttons and {len(day_keys)} days")
        
        for button in time_buttons:
            time_str = button['time']
            current_hour = self._time_to_hour(time_str)
            
            # Time order logic: backward/same time = next day
            if current_hour <= previous_hour and current_day_index < len(day_keys) - 1:
                current_day_index += 1
                logger.debug(f"Time went backward ({current_hour} <= {previous_hour}), moving to day: {day_keys[current_day_index]}")
            
            current_day = day_keys[current_day_index]
            matrix[current_day].append(time_str)
            logger.debug(f"Added {time_str} to {current_day}")
            previous_hour = current_hour
        
        # Log final results
        for day, times in matrix.items():
            logger.info(f"Day '{day}': {len(times)} times: {times}")
        
        return matrix
    
    def _time_to_hour(self, time_str: str) -> int:
        """
        Convert time string to hour integer for comparison
        
        Args:
            time_str: Time in format "HH:MM"
            
        Returns:
            Hour as integer (0-23)
        """
        try:
            return int(time_str.split(':')[0])
        except (ValueError, IndexError):
            logger.warning(f"Failed to parse hour from time string: {time_str}")
            return 0


class AcuityTimeParser:
    """
    Main orchestrator class that coordinates all time extraction
    Replaces the broken court_availability extraction methods
    """
    
    def __init__(self):
        self.day_detector = DayDetector()
        self.time_extractor = TimeOrderExtractor()
    
    async def extract_times_by_day(self, frame: Frame) -> Dict[str, List[str]]:
        """
        Main extraction method using new time-order approach
        
        Args:
            frame: The page frame to extract times from
            
        Returns:
            Dictionary mapping date strings to time lists
            Example: {"2025-07-22": ["09:00", "10:00"], "2025-07-23": ["09:00", "11:00"]}
        """
        try:
            logger.info("Starting new time-order extraction")
            
            # Step 1: Get page text content
            text_content = await self.day_detector.extract_page_text_content(frame)
            logger.info(f"Extracted page text preview: {text_content[:100]}...")
            
            # Step 2: Detect available days
            available_days = self.day_detector.get_available_days(text_content)
            logger.info(f"Detected available days: {available_days}")
            
            if not available_days:
                logger.warning("No days detected in page content")
                return {}
            
            # Step 3: Extract time buttons in order
            time_buttons = await self.time_extractor.extract_raw_time_buttons(frame)
            logger.info(f"Extracted {len(time_buttons)} time buttons")
            
            if not time_buttons:
                logger.warning("No time buttons found")
                return {}
            
            # Step 4: Apply time order logic
            day_time_matrix = self.time_extractor.group_times_by_order_logic(time_buttons, available_days)
            logger.info(f"Grouped times by day: {day_time_matrix}")
            
            # Step 5: Convert day labels to actual dates
            # Convert to uppercase for compatibility with existing function
            uppercase_matrix = {}
            for day_label, times in day_time_matrix.items():
                if day_label == 'hoy':
                    uppercase_matrix['HOY'] = times
                elif day_label == 'mañana':
                    uppercase_matrix['MAÑANA'] = times
                elif day_label == 'esta semana':
                    uppercase_matrix['ESTA SEMANA'] = times
                elif day_label == 'la próxima semana':
                    uppercase_matrix['LA PRÓXIMA SEMANA'] = times
                else:
                    uppercase_matrix[day_label.upper()] = times
            
            from .day_context_parser import convert_day_labels_to_dates
            date_time_matrix = convert_day_labels_to_dates(uppercase_matrix)
            logger.info(f"Converted to dates: {date_time_matrix}")
            
            return date_time_matrix
            
        except Exception as e:
            logger.error(f"Error in new time extraction: {e}")
            return {}