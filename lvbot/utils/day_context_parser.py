"""
Day Context Parser - Extract day labels and group times by day from Acuity DOM
Handles Spanish day labels and DOM traversal to associate times with correct days
"""

from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple
from playwright.async_api import Frame, ElementHandle
import logging
import re

logger = logging.getLogger(__name__)


async def identify_visible_day_labels(frame: Frame) -> List[str]:
    """
    Find Spanish day labels currently visible on the page
    
    Args:
        frame: Playwright frame to search
        
    Returns:
        List of day labels found (e.g., ['HOY', 'MAÑANA', 'ESTA SEMANA'])
    """
    day_labels = []
    
    # Spanish day patterns to look for
    day_patterns = [
        'HOY',
        'MAÑANA', 
        'ESTA SEMANA'
    ]
    
    try:
        # Get all text content from the page
        page_text = await frame.evaluate('() => document.body.innerText')
        page_text_upper = page_text.upper()
        
        # Check which day labels are present
        for pattern in day_patterns:
            if pattern in page_text_upper:
                day_labels.append(pattern)
                logger.debug(f"Found day label: {pattern}")
        
        logger.info(f"Identified visible day labels: {day_labels}")
        return day_labels
        
    except Exception as e:
        logger.error(f"Error identifying day labels: {e}")
        return []


async def extract_day_headers_with_positions(frame: Frame) -> Dict[str, ElementHandle]:
    """
    Find day header elements and their DOM positions
    
    Args:
        frame: Playwright frame to search
        
    Returns:
        Dict mapping day labels to their DOM elements
    """
    day_headers = {}
    
    # Selectors for elements that might contain day headers
    header_selectors = [
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',  # Header tags
        'div', 'span', 'p',                    # Text containers
        '[class*="day"]', '[class*="date"]',   # Day/date related classes
        '[class*="header"]', '[class*="title"]' # Header/title classes
    ]
    
    try:
        for selector in header_selectors:
            elements = await frame.query_selector_all(selector)
            
            for element in elements:
                try:
                    if not await element.is_visible():
                        continue
                        
                    text = await element.inner_text()
                    text_upper = text.strip().upper()
                    
                    # Check if this element contains a day label
                    if 'HOY' in text_upper and 'HOY' not in day_headers:
                        day_headers['HOY'] = element
                        logger.debug(f"Found HOY header: '{text.strip()}'")
                        
                    elif 'MAÑANA' in text_upper and 'MAÑANA' not in day_headers:
                        day_headers['MAÑANA'] = element
                        logger.debug(f"Found MAÑANA header: '{text.strip()}'")
                        
                    elif 'ESTA SEMANA' in text_upper and 'ESTA SEMANA' not in day_headers:
                        day_headers['ESTA SEMANA'] = element
                        logger.debug(f"Found ESTA SEMANA header: '{text.strip()}'")
                        
                except Exception as e:
                    logger.debug(f"Error processing element: {e}")
                    continue
        
        logger.info(f"Found {len(day_headers)} day headers: {list(day_headers.keys())}")
        return day_headers
        
    except Exception as e:
        logger.error(f"Error extracting day headers: {e}")
        return {}


async def find_time_buttons_for_day_container(frame: Frame, day_label: str) -> List[str]:
    """
    Find time buttons within the same container as a day label using DOM container search
    
    Based on actual Acuity DOM analysis:
    - Day labels (MAÑANA, HOY) are in P.css-17hpwq8 or P.css-w7uz5c 
    - Time buttons are in BUTTON.time-selection within DIV.css-y8spei
    - Both share grandparent container DIV.css-i8hhkw
    
    Args:
        frame: Playwright frame
        day_label: Day label to search for (e.g., 'HOY', 'MAÑANA')
        
    Returns:
        List of time strings found in the same container context as the day label
    """
    times = []
    
    try:
        # Use DOM traversal strategy based on actual Acuity structure
        times_found = await frame.evaluate(f'''
            (dayLabel) => {{
                const times = [];
                console.log('=== DOM Search for day label:', dayLabel, '===');
                
                // Strategy: Find day label, go up to shared container, find time buttons
                const allElements = document.querySelectorAll('*');
                let dayElement = null;
                
                // Find the specific day label element
                for (const element of allElements) {{
                    const text = element.textContent?.trim() || '';
                    const upperText = text.toUpperCase();
                    
                    // Look for exact or contained day label in leaf elements
                    if ((upperText === dayLabel || upperText.includes(dayLabel)) && 
                        element.children.length === 0) {{
                        console.log('Found day element:', element.tagName + '.' + (element.className || 'no-class'), 
                                  '"' + text + '"');
                        dayElement = element;
                        break;
                    }}
                }}
                
                if (!dayElement) {{
                    console.log('ERROR: No day element found for label:', dayLabel);
                    return times;
                }}
                
                // Walk up the DOM tree to find the shared container
                let container = dayElement;
                let level = 0;
                
                while (container && level < 5) {{
                    const timeButtons = container.querySelectorAll('button.time-selection');
                    console.log(`Level ${{level}}: ${{container.tagName}}.${{container.className || 'no-class'}} - ${{timeButtons.length}} time buttons`);
                    
                    if (timeButtons.length > 0) {{
                        console.log(`SUCCESS: Found ${{timeButtons.length}} time buttons at level ${{level}}`);
                        
                        // Extract time text from buttons
                        timeButtons.forEach((btn, index) => {{
                            const timeText = btn.textContent?.trim();
                            if (timeText && /^\\d{{1,2}}:\\d{{2}}$/.test(timeText)) {{
                                times.push(timeText);
                                console.log(`  Time button ${{index}}: "${{timeText}}"`);
                            }} else {{
                                console.log(`  Invalid time button ${{index}}: "${{timeText}}"`);
                            }}
                        }});
                        
                        break; // Found our times, stop searching
                    }}
                    
                    container = container.parentElement;
                    level++;
                }}
                
                if (times.length === 0) {{
                    console.log('WARNING: No time buttons found in any parent container');
                    
                    // Fallback: Search in document for all time buttons and check context
                    const allTimeButtons = document.querySelectorAll('button.time-selection');
                    console.log(`Fallback: Found ${{allTimeButtons.length}} total time buttons on page`);
                    
                    if (allTimeButtons.length > 0) {{
                        console.log('Using fallback: all available times');
                        allTimeButtons.forEach((btn, index) => {{
                            const timeText = btn.textContent?.trim();
                            if (timeText && /^\\d{{1,2}}:\\d{{2}}$/.test(timeText)) {{
                                times.push(timeText);
                                console.log(`  Fallback time ${{index}}: "${{timeText}}"`);
                            }}
                        }});
                    }}
                }}
                
                console.log('=== Final result for', dayLabel, ':', times.length, 'times ===');
                return times;
            }}
        ''', day_label)
        
        if times_found:
            times.extend(times_found)
        
        # Remove duplicates and sort
        unique_times = sorted(list(set(times)))
        
        logger.info(f"Found {len(unique_times)} times for day '{day_label}': {unique_times}")
        return unique_times
        
    except Exception as e:
        logger.error(f"Error finding times for day '{day_label}': {e}")
        return []


async def extract_times_grouped_by_day(frame: Frame) -> Dict[str, List[str]]:
    """
    Extract time slots grouped by their day context
    
    Main function that orchestrates day-aware time extraction by:
    1. Finding day headers in the DOM
    2. Extracting times associated with each day
    3. Grouping results by day label
    
    Args:
        frame: Playwright frame containing the schedule
        
    Returns:
        Dict mapping day labels to time lists
        Example: {"HOY": ["11:00", "12:00"], "MAÑANA": ["08:00", "09:00"]}
    """
    times_by_day = {}
    
    try:
        # Step 1: Find day headers
        day_headers = await extract_day_headers_with_positions(frame)
        
        if not day_headers:
            # Fallback: If no day headers found, extract all times as single day
            logger.warning("No day headers found, falling back to single day extraction")
            all_times = await _extract_all_time_buttons(frame)
            if all_times:
                times_by_day['UNKNOWN'] = all_times
            return times_by_day
        
        # Step 2: Extract times for each day using container-based search
        for day_label in day_headers.keys():
            times = await find_time_buttons_for_day_container(frame, day_label)
            if times:
                times_by_day[day_label] = times
                logger.info(f"Day '{day_label}': {len(times)} times found: {times}")
            else:
                logger.warning(f"No times found for day '{day_label}' using container search")
        
        # Step 3: If no times found with headers, try alternative extraction
        if not any(times_by_day.values()):
            logger.warning("No times found with header-based extraction, trying alternative method")
            all_times = await _extract_all_time_buttons(frame)
            if all_times:
                # If we have day labels but no times per day, assign all to first day
                first_day = list(day_headers.keys())[0] if day_headers else 'UNKNOWN'
                times_by_day[first_day] = all_times
        
        return times_by_day
        
    except Exception as e:
        logger.error(f"Error in extract_times_grouped_by_day: {e}")
        return {}


async def _extract_all_time_buttons(frame: Frame) -> List[str]:
    """
    Fallback extraction of all time buttons when day grouping fails
    
    Args:
        frame: Playwright frame
        
    Returns:
        List of all time strings found
    """
    times = []
    
    try:
        # Extract all time selection buttons
        time_buttons = await frame.query_selector_all('button.time-selection')
        
        for button in time_buttons:
            try:
                if await button.is_visible():
                    # Get the time text from the button
                    time_element = await button.query_selector('p')
                    if time_element:
                        time_text = await time_element.inner_text()
                        time_text = time_text.strip()
                        
                        # Validate it's a proper time format
                        if re.match(r'^\d{1,2}:\d{2}$', time_text):
                            times.append(time_text)
                            
            except Exception as e:
                logger.debug(f"Error extracting from button: {e}")
                continue
        
        # Remove duplicates and sort
        unique_times = sorted(list(set(times)))
        logger.debug(f"Fallback extraction found {len(unique_times)} times: {unique_times}")
        
        return unique_times
        
    except Exception as e:
        logger.error(f"Error in fallback time extraction: {e}")
        return []


def convert_day_labels_to_dates(times_by_day: Dict[str, List[str]], reference_date: Optional[date] = None) -> Dict[str, List[str]]:
    """
    Convert Spanish day labels to actual dates
    
    Args:
        times_by_day: Dict with day labels as keys
        reference_date: Reference date (defaults to today)
        
    Returns:
        Dict with actual dates as keys (YYYY-MM-DD format)
    """
    if reference_date is None:
        reference_date = date.today()
    
    times_by_date = {}
    
    for day_label, times in times_by_day.items():
        if day_label == 'HOY':
            date_key = reference_date.strftime('%Y-%m-%d')
        elif day_label == 'MAÑANA':
            tomorrow = reference_date + timedelta(days=1)
            date_key = tomorrow.strftime('%Y-%m-%d')
        elif day_label == 'ESTA SEMANA':
            day_after_tomorrow = reference_date + timedelta(days=2)
            date_key = day_after_tomorrow.strftime('%Y-%m-%d')
        elif day_label == 'LA PRÓXIMA SEMANA':
            # LA PRÓXIMA SEMANA = day after tomorrow (+2 days)
            day_after_tomorrow = reference_date + timedelta(days=2)
            date_key = day_after_tomorrow.strftime('%Y-%m-%d')
        else:
            # Unknown day label, use as-is
            date_key = day_label
        
        times_by_date[date_key] = times
        logger.debug(f"Converted '{day_label}' → '{date_key}': {len(times)} times")
    
    return times_by_date


async def has_navigation_arrow(frame: Frame) -> bool:
    """
    Check if there's a navigation arrow ('>') visible on the page
    
    Args:
        frame: Playwright frame to search
        
    Returns:
        True if navigation arrow is found and visible
    """
    try:
        # Look for common navigation arrow patterns
        arrow_selectors = [
            'button:has-text(">")',
            'button:has-text("→")', 
            'button:has-text("▶")',
            'button[aria-label*="next"]',
            'button[aria-label*="siguiente"]',
            '[class*="next"]',
            '[class*="arrow"]'
        ]
        
        for selector in arrow_selectors:
            try:
                elements = await frame.query_selector_all(selector)
                for element in elements:
                    if await element.is_visible():
                        text = await element.inner_text()
                        logger.debug(f"Found potential navigation arrow: '{text.strip()}'")
                        return True
            except:
                continue
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking navigation arrow: {e}")
        return False