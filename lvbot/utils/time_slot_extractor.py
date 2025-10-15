"""
Time Slot Extractor Module
=========================

PURPOSE: Extract time slot data from Acuity Scheduling pages
PATTERN: Single responsibility - DOM extraction only
SCOPE: Time button finding and text extraction

Separates DOM extraction logic from availability checking logic.
"""

import logging
from typing import List, Optional
from playwright.async_api import Page
from .constants import TIME_BUTTON_SELECTOR, TIME_SLOT_SELECTORS

logger = logging.getLogger(__name__)


class TimeSlotExtractor:
    """
    Handles extraction of time slots from Acuity pages.
    Single responsibility: Find and extract time data from DOM.
    """
    
    @staticmethod
    async def extract_all_time_buttons(page: Page) -> List[object]:
        """
        Extract all time buttons from the page.
        
        Args:
            page: Playwright page object
            
        Returns:
            List of button elements
        """
        try:
            # Try primary selector first
            buttons = await page.query_selector_all(TIME_BUTTON_SELECTOR)
            if buttons:
                logger.debug(f"Found {len(buttons)} buttons using primary selector")
                return buttons
                
            # Fallback to other selectors
            for selector in TIME_SLOT_SELECTORS[1:]:  # Skip first as we already tried it
                try:
                    buttons = await page.query_selector_all(selector)
                    if buttons:
                        logger.debug(f"Found {len(buttons)} buttons using selector: {selector}")
                        return buttons
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    
            logger.warning("No time buttons found with any selector")
            return []
            
        except Exception as e:
            logger.error(f"Error extracting time buttons: {e}")
            return []
    
    @staticmethod
    async def extract_time_text(button) -> Optional[str]:
        """
        Extract time text from a button element.
        
        Args:
            button: Button element
            
        Returns:
            Time text or None
        """
        try:
            text = await button.text_content()
            if text:
                # Clean and normalize the time text
                cleaned = text.strip()
                # Ensure consistent format (e.g., "6:00" -> "06:00")
                if cleaned and len(cleaned) == 4 and cleaned[0].isdigit():
                    cleaned = f"0{cleaned}"
                return cleaned
            return None
        except Exception as e:
            logger.debug(f"Error extracting text from button: {e}")
            return None
    
    @staticmethod
    async def find_specific_time_button(page: Page, time_slot: str) -> Optional[object]:
        """
        Find a specific time slot button on the page.
        
        Args:
            page: Playwright page object
            time_slot: Time to find (e.g., "06:00", "10:00")
            
        Returns:
            Button element if found, None otherwise
        """
        # Normalize time format
        if len(time_slot) == 4 and time_slot[0].isdigit():
            time_slot = f"0{time_slot}"
            
        # Try multiple selector strategies
        selectors = [
            f'{TIME_BUTTON_SELECTOR}:has(p:text("{time_slot}"))',
            f'button[aria-label*="{time_slot}"]',
            f'button:has-text("{time_slot}")',
            f'{TIME_BUTTON_SELECTOR}:has-text("{time_slot}")'
        ]
        
        for selector in selectors:
            try:
                button = await page.query_selector(selector)
                if button and await button.is_visible():
                    logger.info(f"Found time button for {time_slot}")
                    return button
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                
        logger.warning(f"Could not find time button for {time_slot}")
        return None