"""
Court availability detection utilities - modular functions for finding available times
"""

from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple, Any
from playwright.async_api import Frame
import logging
import re
import time

from .async_browser_helpers import BrowserHelpers

logger = logging.getLogger(__name__)

class CourtAvailability:
    """Modular functions for detecting court availability across different days"""
    
    @staticmethod
    def get_earliest_booking_hour() -> int:
        """Get the earliest hour courts open for booking"""
        return 7  # 7:00 AM
    
    @staticmethod
    def get_latest_booking_hour() -> int:
        """Get the latest hour courts are available for booking"""
        return 21  # 9:00 PM
    
    @staticmethod
    def get_booking_window_hours() -> int:
        """Get the booking window in hours"""
        return 48  # 48 hours in advance
    
    @staticmethod
    def is_time_text(text: str) -> bool:
        """Check if text represents a time"""
        time_pattern = re.compile(r'^\d{1,2}:\d{2}(\s*(AM|PM))?$', re.IGNORECASE)
        return bool(time_pattern.match(text.strip()))
    
    @staticmethod
    async def is_acuity_scheduling_page(frame: Frame) -> bool:
        """
        Detect if current page is an Acuity Scheduling page
        
        Checks for specific Acuity Scheduling indicators:
        - Button elements with 'time-selection' class
        - Timezone text containing 'Guatemala (GMT'
        - Specific CSS class patterns (css-65sav3 for time text)
        
        Args:
            frame: The page frame to check
            
        Returns:
            bool: True if Acuity Scheduling page detected
        """
        try:
            # Check for Acuity-specific elements
            has_time_selection = await frame.evaluate('''
                () => {
                    // Check for time-selection buttons
                    const timeButtons = document.querySelectorAll('button.time-selection');
                    // Check for timezone button with Guatemala GMT
                    const timezoneText = document.body.textContent.includes('Guatemala (GMT-06:00)');
                    // Check for specific CSS classes used by Acuity
                    const hasAcuityClasses = document.querySelector('p.css-65sav3') !== null;
                    
                    return timeButtons.length > 0 || (timezoneText && hasAcuityClasses);
                }
            ''')
            
            if has_time_selection:
                logger.info("Detected Acuity Scheduling page structure")
            
            return has_time_selection
            
        except Exception as e:
            logger.debug(f"Error detecting Acuity page: {e}")
            return False
    
    @staticmethod
    async def extract_acuity_times_by_day(frame: Frame) -> Dict[str, List[str]]:
        """
        Extract time slots from Acuity Scheduling pages organized by day
        
        UPDATED: Now uses day-aware extraction to properly separate times by day context
        and applies time feasibility filtering based on club constraints.
        
        Args:
            frame: The page frame containing time slots
            
        Returns:
            Dict[str, List[str]]: Dictionary mapping dates to time lists
            Example: {"2025-07-21": ["11:00", "12:00"], "2025-07-22": ["08:00", "09:00"]}
        """
        from datetime import datetime, date
        from .time_feasibility_validator import filter_future_times_for_today
        
        times_by_date = {}
        current_time = datetime.now()
        
        try:
            # Step 1: Use new time-order extraction
            from .time_order_extraction import AcuityTimeParser
            parser = AcuityTimeParser()
            times_by_date = await parser.extract_times_by_day(frame)
            logger.info(f"New extraction found times by date: {times_by_date}")
            
            if not times_by_date:
                logger.warning("No times extracted by new parser, falling back to legacy extraction")
                # Fallback to legacy extraction
                current_day_times = await CourtAvailability._extract_current_day_times(frame)
                if current_day_times:
                    today = date.today().strftime('%Y-%m-%d')
                    times_by_date[today] = current_day_times
                return times_by_date
            
            # Step 3: Apply time feasibility filtering
            filtered_times_by_date = {}
            for date_str, times in times_by_date.items():
                # Check if this is today - if so, filter out past times
                today_str = date.today().strftime('%Y-%m-%d')
                if date_str == today_str:
                    # Filter out times that have already passed
                    future_times = filter_future_times_for_today(times, current_time)
                    if future_times:
                        filtered_times_by_date[date_str] = future_times
                        logger.info(f"Today ({date_str}): {len(future_times)} future times: {future_times}")
                else:
                    # For future days, include all times
                    filtered_times_by_date[date_str] = times
                    logger.info(f"Future day ({date_str}): {len(times)} times: {times}")
            
            return filtered_times_by_date
            
        except Exception as e:
            logger.error(f"Error in day-aware extraction: {e}")
            # Fallback to legacy extraction
            try:
                current_day_times = await CourtAvailability._extract_current_day_times(frame)
                if current_day_times:
                    today = date.today().strftime('%Y-%m-%d')
                    times_by_date[today] = current_day_times
                    logger.info(f"Fallback extraction: {len(current_day_times)} times for today")
            except Exception as fallback_error:
                logger.error(f"Fallback extraction also failed: {fallback_error}")
            
            return times_by_date
    
    @staticmethod
    async def _extract_current_day_times(frame: Frame) -> List[str]:
        """Extract times for the current/primary day shown on the page"""
        available_times = []
        
        try:
            # Query for all time selection buttons
            time_buttons = await frame.query_selector_all('button.time-selection')
            logger.debug(f"Found {len(time_buttons)} time selection buttons")
            
            for button in time_buttons:
                try:
                    # Check if button is visible
                    if not await button.is_visible():
                        continue
                    
                    # Get the child <p> element that contains the time
                    time_element = await button.query_selector('p')
                    if time_element:
                        time_text = await time_element.inner_text()
                        time_text = time_text.strip()
                        
                        # Validate it's a proper time format
                        if CourtAvailability.is_time_text(time_text):
                            available_times.append(time_text)
                            logger.debug(f"Extracted time: {time_text}")
                        else:
                            logger.debug(f"Skipped non-time text: {time_text}")
                            
                except Exception as e:
                    logger.debug(f"Error extracting from button: {e}")
                    continue
            
            # Remove duplicates and sort
            unique_times = sorted(list(set(available_times)))
            return unique_times
            
        except Exception as e:
            logger.error(f"Error extracting current day times: {e}")
            return []

    @staticmethod
    async def extract_acuity_times(frame: Frame) -> List[str]:
        """
        Extract time slots specifically from Acuity Scheduling pages
        
        UPDATED: Now focuses on current day times to avoid mixing multiple days
        
        Args:
            frame: The page frame containing time slots
            
        Returns:
            List[str]: Sorted list of available time strings for current day
        """
        try:
            # Use the new day-based extraction but return just current day times
            times_by_day = await CourtAvailability.extract_acuity_times_by_day(frame)
            
            # Get current day times (should be the primary day shown)
            from datetime import date
            today = date.today().strftime('%Y-%m-%d')
            
            if today in times_by_day:
                current_day_times = times_by_day[today]
                logger.info(f"Acuity extraction found {len(current_day_times)} times for current day: {current_day_times}")
                return current_day_times
            else:
                # FIXED: Don't return all times from all days - return empty list if no times for today
                logger.warning(f"No times found for current day ({today}), returning empty list instead of mixing days")
                return []
                
        except Exception as e:
            logger.error(f"Error in extract_acuity_times: {e}")
            return []
    
    @staticmethod
    def get_time_selectors() -> List[str]:
        """Get list of selectors to find time slots - Updated with better patterns
        
        DEPRECATED: These selectors are outdated. The website now uses:
        - button.time-selection for time buttons
        - 24-hour format (06:00) instead of AM/PM
        Use AvailabilityCheckerV2 which has the correct selectors.
        """
        return [
            # Specific time patterns
            'button[data-time]',
            'button:has-text("AM"), button:has-text("PM")',  # DEPRECATED: Site uses 24-hour format now
            'button:has-text(":")',
            '*:has-text(":")',  # Colon pattern for time
            
            # Common time slot classes
            '.time-slot:not(.disabled)',
            '.time-button:not(.disabled)',
            '[class*="time"]:not(.disabled)',
            '[class*="hora"]:not(.disabled)',
            '[class*="slot"]:not(.disabled)',
            
            # Table-based time slots
            'td button:has-text(":")',
            'td:has-text(":")',
            
            # Generic clickable elements with time pattern
            'button:has-text(":")',
            'a:has-text(":")',
            '[onclick]:has-text(":")',
            
            # Fallback to all buttons
            'button'
        ]
    
    @staticmethod
    async def extract_times_from_page(frame: Frame, take_screenshot: bool = False) -> List[str]:
        """
        Extract available time slots from the current page
        
        Detects page type and routes to appropriate extraction method:
        - Acuity Scheduling: Uses button.time-selection targeting
        - Other systems: Uses generic JavaScript/selector approach
        
        Args:
            frame: The page frame to extract times from
            take_screenshot: Whether to take a debug screenshot (default: False)
            
        Returns:
            List[str]: Sorted list of available time strings
        """
        # Check if this is an Acuity Scheduling page
        if await CourtAvailability.is_acuity_scheduling_page(frame):
            logger.info("Using Acuity-specific time extraction")
            return await CourtAvailability.extract_acuity_times(frame)
        
        # Otherwise, use the generic extraction logic
        logger.info("Using generic time extraction")
        available_times = []
        
        try:
            # Take screenshot for debugging if requested
            if take_screenshot:
                try:
                    screenshot_path = f"/tmp/court_availability_debug_{int(time.time())}.png"
                    await frame.page.screenshot(path=screenshot_path)
                    logger.info(f"Screenshot saved: {screenshot_path}")
                except Exception as e:
                    logger.debug(f"Screenshot failed: {e}")
            
            # Wait for calendar content to load before JavaScript evaluation
            calendar_loaded = await BrowserHelpers.wait_for_calendar_content(frame, timeout=10000)
            if not calendar_loaded:
                logger.debug("Calendar content not loaded within timeout, proceeding anyway")
            
            # Use JavaScript evaluation for more robust time detection
            js_times = await frame.evaluate('''() => {
                const times = [];
                const timeRegex = /\\b\\d{1,2}:\\d{2}\\b/g;
                const processedElements = new Set();
                
                // Debug: log what we're working with
                console.log('DOM elements found:', document.querySelectorAll('*').length);
                console.log('Document title:', document.title);
                console.log('Document body text preview:', document.body.textContent.substring(0, 200));
                
                // Find all elements that might contain times
                const allElements = document.querySelectorAll('*');
                const allMatches = [];
                
                allElements.forEach(element => {
                    // Skip if already processed
                    if (processedElements.has(element)) return;
                    
                    const text = element.textContent || '';
                    const matches = text.match(timeRegex);
                    
                    // Log all time-like text we find
                    if (matches) {
                        allMatches.push({
                            text: matches[0],
                            tagName: element.tagName,
                            className: element.className,
                            isLeaf: element.children.length === 0,
                            style: window.getComputedStyle(element),
                            element: element
                        });
                    }
                    
                    // Check if this is a leaf element (no children) with time
                    if (matches && element.children.length === 0) {
                        const time = matches[0];
                        
                        // Check if element is visible
                        const style = window.getComputedStyle(element);
                        const isVisible = style.display !== 'none' && 
                                         style.visibility !== 'hidden' && 
                                         style.opacity !== '0';
                        
                        // Check if clickable
                        const isClickable = element.tagName === 'BUTTON' || 
                                           element.tagName === 'A' ||
                                           element.onclick !== null ||
                                           element.style.cursor === 'pointer' ||
                                           element.getAttribute('role') === 'button';
                        
                        // Check if disabled
                        const isDisabled = element.disabled || 
                                          element.classList.contains('disabled') ||
                                          element.classList.contains('unavailable') ||
                                          element.style.opacity === '0.5';
                        
                        if (isVisible && !isDisabled && (isClickable || element.tagName === 'TD')) {
                            times.push(time);
                            processedElements.add(element);
                        }
                    }
                });
                
                console.log('All time matches found:', allMatches);
                console.log('Final times extracted:', times);
                
                // Remove duplicates and sort
                const uniqueTimes = [...new Set(times)];
                return uniqueTimes.sort();
            }''')
            
            logger.info(f"JavaScript extracted {len(js_times)} times: {js_times}")
            
            # Add JS-detected times to result
            for time in js_times:
                if CourtAvailability.is_time_text(time) and time not in available_times:
                    available_times.append(time)
                    
        except Exception as e:
            logger.debug(f"JavaScript time extraction failed: {e}")
        
        # Fallback to selector-based approach if JS failed
        if not available_times:
            logger.info("Using fallback selector-based time detection")
            
            # Wait for time elements before trying selectors
            time_elements_ready = await BrowserHelpers.wait_for_time_elements(frame, min_count=1, timeout=5000)
            if time_elements_ready:
                logger.debug("Time elements detected, proceeding with selector extraction")
            else:
                logger.debug("No time elements detected, attempting extraction anyway")
            
            time_selectors = CourtAvailability.get_time_selectors()
            
            for selector in time_selectors:
                try:
                    buttons = await frame.query_selector_all(selector)
                    for button in buttons:
                        if await button.is_visible():
                            text = await button.inner_text()
                            text = text.strip()
                            if CourtAvailability.is_time_text(text) and text not in available_times:
                                available_times.append(text)
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
        
        logger.info(f"Extracted {len(available_times)} time slots: {available_times}")
        return sorted(available_times)
    
    @staticmethod
    def get_day_indicator_selectors() -> List[str]:
        """Get list of selectors to find day indicators - Enhanced patterns"""
        return [
            # Header elements
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            
            # Common day/date classes
            '.date-header', '.day-header', '.date-title', '.day-title',
            '[class*="date"]', '[class*="day"]', '[class*="fecha"]',
            '[class*="calendario"]', '[class*="calendar"]',
            
            # Specific text patterns (Spanish)
            'span:has-text("HOY")', 'span:has-text("MAÑANA")',
            'div:has-text("HOY")', 'div:has-text("MAÑANA")',
            'p:has-text("HOY")', 'p:has-text("MAÑANA")',
            '*:has-text("HOY")', '*:has-text("MAÑANA")',
            
            # English patterns
            'span:has-text("Today")', 'span:has-text("Tomorrow")',
            'div:has-text("Today")', 'div:has-text("Tomorrow")',
            'p:has-text("Today")', 'p:has-text("Tomorrow")',
            '*:has-text("Today")', '*:has-text("Tomorrow")',
            
            # Date format patterns
            r'*:has-text(/\d{1,2}\s*(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)/)',
            r'*:has-text(/\d{1,2}\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)/)',
            r'*:has-text(/\d{1,2}\/\d{1,2}\/\d{2,4}/)',
            
            # Day names (Spanish)
            '*:has-text("lunes")', '*:has-text("martes")', '*:has-text("miércoles")',
            '*:has-text("jueves")', '*:has-text("viernes")', '*:has-text("sábado")', '*:has-text("domingo")',
            
            # Day names (English)
            '*:has-text("monday")', '*:has-text("tuesday")', '*:has-text("wednesday")',
            '*:has-text("thursday")', '*:has-text("friday")', '*:has-text("saturday")', '*:has-text("sunday")',
            
            # Generic text containers
            'p', 'div', 'span', 'td', 'th'
        ]
    
    @staticmethod
    def get_day_names() -> Dict[str, List[str]]:
        """Get mapping of day types to their text representations"""
        return {
            'today': ['HOY', 'TODAY'],
            'tomorrow': ['MAÑANA', 'TOMORROW'], 
            'weekdays': ['LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES', 'SÁBADO', 'DOMINGO'],
            'weekdays_en': ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']
        }
    
    @staticmethod
    async def get_current_day_indicator(frame: Frame) -> Optional[str]:
        """Get the current day indicator from the page"""
        # Use modular selectors and day names
        day_indicators = CourtAvailability.get_day_indicator_selectors()
        
        day_name_map = CourtAvailability.get_day_names()
        day_names = day_name_map['today'] + day_name_map['tomorrow'] + day_name_map['weekdays']
        
        for selector in day_indicators:
            try:
                elements = await frame.query_selector_all(selector)
                for elem in elements:
                    if await elem.is_visible():
                        text = await elem.inner_text()
                        text = text.strip().upper()
                        for day in day_names:
                            if day in text:
                                logger.info(f"Found day indicator: {text}")
                                return text
            except:
                continue
        
        return None
    
    @staticmethod
    async def look_for_today(frame: Frame) -> Tuple[bool, List[str]]:
        """
        Look for today's available time slots
        Returns: (found_today, list_of_times)
        """
        logger.info("Looking for today's availability...")
        
        # Check if we're on today's page
        day_indicator = await CourtAvailability.get_current_day_indicator(frame)
        
        if day_indicator and ('HOY' in day_indicator or 'TODAY' in day_indicator):
            logger.info("Found today's page")
            times = await CourtAvailability.extract_times_from_page(frame)
            return True, times
        
        # If no clear indicator, check if the date matches today
        today = date.today()
        today_patterns = [
            today.strftime("%d"),  # Day number
            today.strftime("%A").upper(),  # Day name in English
            # Spanish day names
            ['LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES', 'SÁBADO', 'DOMINGO'][today.weekday()]
        ]
        
        page_text = await frame.evaluate('() => document.body.innerText')
        for pattern in today_patterns:
            if pattern in page_text.upper():
                logger.info(f"Detected today by pattern: {pattern}")
                times = await CourtAvailability.extract_times_from_page(frame)
                return True, times
        
        return False, []
    
    @staticmethod
    async def look_for_tomorrow(frame: Frame) -> Tuple[bool, List[str]]:
        """
        Look for tomorrow's available time slots
        Returns: (found_tomorrow, list_of_times)
        """
        logger.info("Looking for tomorrow's availability...")
        
        # Check if we're on tomorrow's page
        day_indicator = await CourtAvailability.get_current_day_indicator(frame)
        
        if day_indicator and ('MAÑANA' in day_indicator or 'TOMORROW' in day_indicator):
            logger.info("Found tomorrow's page")
            times = await CourtAvailability.extract_times_from_page(frame)
            return True, times
        
        # Check for tomorrow's date patterns
        tomorrow = date.today() + timedelta(days=1)
        tomorrow_patterns = [
            tomorrow.strftime("%d"),  # Day number
            tomorrow.strftime("%A").upper(),  # Day name in English
            # Spanish day names
            ['LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES', 'SÁBADO', 'DOMINGO'][tomorrow.weekday()]
        ]
        
        page_text = await frame.evaluate('() => document.body.innerText')
        for pattern in tomorrow_patterns:
            if pattern in page_text.upper():
                logger.info(f"Detected tomorrow by pattern: {pattern}")
                times = await CourtAvailability.extract_times_from_page(frame)
                return True, times
        
        return False, []
    
    @staticmethod
    async def look_for_day_after(frame: Frame) -> Tuple[bool, List[str]]:
        """
        Look for day after tomorrow's available time slots
        Returns: (found_day_after, list_of_times)
        """
        logger.info("Looking for day after tomorrow's availability...")
        
        # Check for day after tomorrow's date patterns
        day_after = date.today() + timedelta(days=2)
        day_after_patterns = [
            day_after.strftime("%d"),  # Day number
            day_after.strftime("%A").upper(),  # Day name in English
            # Spanish day names
            ['LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES', 'SÁBADO', 'DOMINGO'][day_after.weekday()]
        ]
        
        page_text = await frame.evaluate('() => document.body.innerText')
        for pattern in day_after_patterns:
            if pattern in page_text.upper():
                logger.info(f"Detected day after tomorrow by pattern: {pattern}")
                times = await CourtAvailability.extract_times_from_page(frame)
                return True, times
        
        return False, []
    
    @staticmethod
    def get_next_navigation_selectors() -> List[str]:
        """Get list of selectors for next day navigation"""
        return [
            # Arrow symbols
            'button:has-text(">")',
            'button:has-text("→")',
            'button:has-text("▶")',
            'button:has-text("›")',
            'button:has-text("»")',
            # Spanish text
            'button:has-text("siguiente")',
            'button:has-text("Siguiente")',
            'button[aria-label*="siguiente"]',
            'button[aria-label*="Siguiente"]',
            # English text
            'button:has-text("next")',
            'button:has-text("Next")',
            'button[aria-label*="next"]',
            'button[aria-label*="Next"]',
            # Generic patterns
            'button[class*="next"]',
            'button[data-action="next"]',
            'button[data-direction="next"]',
            '.next-day', '.next-arrow',
            'a[href*="next"]'
        ]
    
    @staticmethod
    def get_previous_navigation_selectors() -> List[str]:
        """Get list of selectors for previous day navigation"""
        return [
            # Arrow symbols
            'button:has-text("<")',
            'button:has-text("←")',
            'button:has-text("◀")',
            'button:has-text("‹")',
            'button:has-text("«")',
            # Spanish text
            'button:has-text("anterior")',
            'button:has-text("Anterior")',
            'button[aria-label*="anterior"]',
            'button[aria-label*="Anterior"]',
            # English text  
            'button:has-text("prev")',
            'button:has-text("Previous")',
            'button[aria-label*="prev"]',
            'button[aria-label*="Previous"]',
            # Generic patterns
            'button[class*="prev"]',
            'button[data-action="prev"]',
            'button[data-direction="prev"]',
            '.prev-day', '.prev-arrow',
            'a[href*="prev"]'
        ]
    
    @staticmethod
    async def try_navigate_next(frame: Frame) -> bool:
        """
        Try to navigate to the next day using various navigation elements
        Returns: True if navigation was successful
        """
        logger.info("Trying to navigate to next day...")
        
        # Use modular navigation selectors
        navigation_strategies = [
            # Strategy 1: Look for any element with navigation text
            {
                'name': 'Arrow text search',
                'action': lambda: CourtAvailability._click_element_with_text(frame, '>')
            },
            # Strategy 2: Use modular next navigation selectors
            {
                'name': 'Next navigation selectors',
                'selectors': CourtAvailability.get_next_navigation_selectors()
            },
            # Strategy 3: Look near day indicators
            {
                'name': 'Day sibling navigation',
                'action': lambda: CourtAvailability._click_day_navigation(frame)
            }
        ]
        
        for strategy in navigation_strategies:
            try:
                if 'action' in strategy:
                    # Custom action
                    logger.debug(f"Trying strategy: {strategy['name']}")
                    if await strategy['action']():
                        logger.info(f"Navigation successful with strategy: {strategy['name']}")
                        await frame.wait_for_load_state('networkidle')
                        return True
                else:
                    # Selector-based strategy
                    for selector in strategy.get('selectors', []):
                        try:
                            elem = frame.locator(selector).first
                            if elem and await elem.is_visible():
                                logger.debug(f"Found navigation with selector: {selector}")
                                await elem.click()
                                await frame.wait_for_load_state('networkidle')
                                return True
                        except:
                            continue
            except Exception as e:
                logger.debug(f"Strategy {strategy.get('name', 'unknown')} failed: {e}")
        
        logger.warning("Could not find navigation element")
        return False
    
    @staticmethod
    async def _click_element_with_text(frame: Frame, text: str) -> bool:
        """Click any visible element with exact text match"""
        try:
            elements = await frame.query_selector_all('*')
            for elem in elements:
                try:
                    elem_text = await elem.inner_text()
                    elem_text = elem_text.strip() if elem_text else ''
                except:
                    elem_text = ''
                if elem_text == text and await elem.is_visible():
                    # Check if it's clickable (button, link, or has onclick)
                    tag_name = await elem.evaluate('el => el.tagName')
                    has_onclick = await elem.evaluate('el => el.onclick !== null')
                    role = await elem.get_attribute('role')
                    
                    if tag_name in ['BUTTON', 'A'] or has_onclick or role == 'button':
                        logger.info(f"Found clickable {tag_name} with text '{text}'")
                        await elem.click()
                        return True
            return False
        except Exception as e:
            logger.debug(f"Error clicking element with text '{text}': {e}")
            return False
    
    @staticmethod
    async def _click_day_navigation(frame: Frame) -> bool:
        """Look for navigation elements near day indicators"""
        try:
            # Find day elements and check their siblings
            result = await frame.evaluate('''
                () => {
                    const dayNames = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo'];
                    
                    for (const el of document.querySelectorAll('*')) {
                        const text = (el.innerText || '').toLowerCase();
                        for (const day of dayNames) {
                            if (text.includes(day) && el.children.length === 0) {
                                // Check siblings for navigation
                                const parent = el.parentElement;
                                if (parent) {
                                    const siblings = Array.from(parent.children);
                                    const myIndex = siblings.indexOf(el);
                                    
                                    // Check next siblings for arrows
                                    for (let i = myIndex + 1; i < siblings.length; i++) {
                                        const sibling = siblings[i];
                                        const sibText = sibling.innerText || '';
                                        if (sibText.includes('>') || sibText.includes('→')) {
                                            sibling.click();
                                            return true;
                                        }
                                    }
                                }
                            }
                        }
                    }
                    return false;
                }
            ''')
            return result
        except Exception as e:
            logger.debug(f"Error in day navigation: {e}")
            return False
    
    @staticmethod
    def is_day_after_feasible() -> bool:
        """
        Check if day after tomorrow is within the 48-hour booking window
        Returns: True if we should look for day after tomorrow's availability
        """
        now = datetime.now()
        today = date.today()
        day_after = today + timedelta(days=2)
        
        # Use modular function to get earliest booking time
        earliest_hour = CourtAvailability.get_earliest_booking_hour()
        earliest_booking_time = datetime.combine(day_after, datetime.min.time()).replace(hour=earliest_hour, minute=0, second=0, microsecond=0)
        
        # Calculate hours until earliest booking time
        hours_until_booking = (earliest_booking_time - now).total_seconds() / 3600
        
        # Use modular function to get booking window
        booking_window = CourtAvailability.get_booking_window_hours()
        is_feasible = hours_until_booking <= booking_window
        
        logger.info(f"Hours until day after tomorrow's earliest slot: {hours_until_booking:.1f}h")
        logger.info(f"Day after tomorrow feasible: {is_feasible} (within {booking_window}h window)")
        
        return is_feasible
    
    @staticmethod
    def is_today_feasible() -> bool:
        """
        Check if today has any remaining bookable slots
        Returns: True if we should look for today's availability
        """
        now = datetime.now()
        current_hour = now.hour
        
        # Use modular function to get latest booking hour
        latest_hour = CourtAvailability.get_latest_booking_hour()
        
        if current_hour >= latest_hour:
            logger.info(f"Today not feasible: Past {latest_hour}:00")
            return False
        
        logger.info(f"Today feasible: Current time {now.strftime('%H:%M')} (before {latest_hour}:00)")
        return True
    
    @staticmethod
    def is_tomorrow_feasible() -> bool:
        """
        Check if tomorrow is within the booking window
        Returns: True if we should look for tomorrow's availability
        """
        # Tomorrow is always feasible if we're within 48h window
        logger.info("Tomorrow feasible: Always within 48h window")
        return True
    
    @staticmethod
    async def check_all_days_modular(frame: Frame) -> Dict[str, List[str]]:
        """
        Orchestrate checking all feasible days in a modular way
        Returns: Dictionary mapping day names to available time slots
        """
        available_by_date = {}
        logger.info("Starting modular day-by-day availability check")
        
        # Step 1: Check today if feasible
        if CourtAvailability.is_today_feasible():
            found_today, today_times = await CourtAvailability.look_for_today(frame)
            if found_today and today_times:
                available_by_date["Today"] = today_times
                logger.info(f"Today: {len(today_times)} slots found")
        else:
            logger.info("Today: Skipped (not feasible)")
        
        # Step 2: Check tomorrow (always feasible)
        if CourtAvailability.is_tomorrow_feasible():
            found_tomorrow, tomorrow_times = await CourtAvailability.look_for_tomorrow(frame)
            if not found_tomorrow:
                # Try navigation if not found
                logger.info("Tomorrow not visible, attempting navigation")
                if await CourtAvailability.try_navigate_next(frame):
                    found_tomorrow, tomorrow_times = await CourtAvailability.look_for_tomorrow(frame)
            
            if found_tomorrow and tomorrow_times:
                available_by_date["Tomorrow"] = tomorrow_times
                logger.info(f"Tomorrow: {len(tomorrow_times)} slots found")
        
        # Step 3: Check day after tomorrow if feasible
        if CourtAvailability.is_day_after_feasible():
            found_day_after, day_after_times = await CourtAvailability.look_for_day_after(frame)
            if not found_day_after:
                # Try navigation if not found
                logger.info("Day after tomorrow not visible, attempting navigation")
                if await CourtAvailability.try_navigate_next(frame):
                    found_day_after, day_after_times = await CourtAvailability.look_for_day_after(frame)
            
            if found_day_after and day_after_times:
                available_by_date["Day After Tomorrow"] = day_after_times
                logger.info(f"Day After Tomorrow: {len(day_after_times)} slots found")
        else:
            logger.info("Day After Tomorrow: Skipped (not feasible)")
        
        # Summary
        total_slots = sum(len(times) for times in available_by_date.values())
        logger.info(f"Modular check complete: {len(available_by_date)} days, {total_slots} total slots")
        
        return available_by_date