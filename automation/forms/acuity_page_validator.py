"""
Acuity Page Validator - Validates Acuity scheduling pages for extraction
Implements modular page readiness validation following DRY principles
"""

import logging
from typing import Optional
from playwright.async_api import Page, Frame

logger = logging.getLogger(__name__)


class AcuityPageValidator:
    """
    Validates Acuity scheduling pages are ready for time extraction
    
    Handles Acuity's natural redirect patterns and focuses on content availability
    rather than exact URL matching.
    """
    
    @classmethod
    async def is_page_ready_for_extraction(cls, page: Page, court_num: int) -> bool:
        """
        Check if page is ready for time extraction (allows natural redirects)
        
        This method accepts Acuity's redirect behavior where entry URLs like
        /?appointmentType=15970897 redirect to full calendar URLs. Focus is on
        content readiness rather than URL exactness.
        
        Args:
            page: The browser page to validate
            court_num: Court number for logging context
            
        Returns:
            True if page has extractable scheduling content, False otherwise
        """
        try:
            current_url = page.url
            logger.debug(f"Court {court_num}: Validating page readiness on URL: {current_url}")
            
            # Check if we're on a valid Acuity domain
            if not await cls._is_acuity_domain(page):
                logger.warning(f"Court {court_num}: Not on Acuity domain: {current_url}")
                return False
            
            # Check if page has schedulable content structure
            has_structure = await cls.has_acuity_scheduling_structure(page)
            if has_structure:
                logger.info(f"Court {court_num}: Page ready for extraction")
                return True
            else:
                logger.warning(f"Court {court_num}: Page lacks scheduling structure")
                return False
                
        except Exception as e:
            logger.error(f"Court {court_num}: Error validating page readiness: {e}")
            return False
    
    @classmethod
    async def _is_acuity_domain(cls, page: Page) -> bool:
        """
        Check if page is on a valid Acuity domain
        
        Accepts various Acuity URL patterns including redirected calendar views.
        
        Args:
            page: The browser page to check
            
        Returns:
            True if on Acuity domain, False otherwise
        """
        try:
            current_url = page.url.lower()
            
            # Valid Acuity domains and patterns
            acuity_patterns = [
                'clublavilla.as.me',
                'acuityscheduling.com',
                'squarespacescheduling.com'
            ]
            
            for pattern in acuity_patterns:
                if pattern in current_url:
                    return True
                    
            return False
            
        except Exception as e:
            logger.debug(f"Error checking Acuity domain: {e}")
            return False
    
    @classmethod
    async def has_acuity_scheduling_structure(cls, page: Page) -> bool:
        """
        Detect if page has Acuity scheduling elements for time extraction
        
        Checks for the presence of scheduling interface elements that indicate
        the page can be used for time extraction.
        
        Args:
            page: The browser page to analyze
            
        Returns:
            True if scheduling structure is present, False otherwise
        """
        try:
            # Get the appropriate frame (iframe or page itself)
            extraction_frame = await cls._get_extraction_frame(page)
            if not extraction_frame:
                logger.debug("No suitable frame found for extraction")
                return False
            
            # Check for Acuity scheduling indicators
            scheduling_indicators = [
                'button.time-selection',           # Time selection buttons
                '.calendar-day',                   # Calendar day elements
                '.appointment-time',               # Appointment time slots
                '[data-testid="time-slot"]',       # Test ID for time slots
                '.acuity-calendar',                # Acuity calendar container
                '.time-picker',                    # Time picker interface
                '[class*="time"]',                 # Any element with "time" in class
                'button[onclick*="time"]'          # Buttons with time-related onclick
            ]
            
            for indicator in scheduling_indicators:
                elements = await extraction_frame.query_selector_all(indicator)
                if elements:
                    logger.debug(f"Found scheduling indicator: {indicator} ({len(elements)} elements)")
                    return True
            
            # If no specific indicators, check for general booking interface
            general_indicators = [
                'button',                          # Any buttons (could be time slots)
                '.calendar',                       # Calendar elements
                '[class*="schedule"]',             # Schedule-related classes
                '[class*="booking"]'               # Booking-related classes
            ]
            
            button_count = 0
            for indicator in general_indicators:
                elements = await extraction_frame.query_selector_all(indicator)
                if indicator == 'button':
                    button_count = len(elements)
                if elements:
                    logger.debug(f"Found general indicator: {indicator} ({len(elements)} elements)")
            
            # If we have multiple buttons, likely a scheduling interface
            if button_count >= 5:
                logger.debug(f"Found {button_count} buttons, likely scheduling interface")
                return True
            
            logger.debug("No scheduling structure indicators found")
            return False
            
        except Exception as e:
            logger.debug(f"Error checking scheduling structure: {e}")
            return False
    
    @staticmethod
    async def _get_extraction_frame(page: Page) -> Optional[Frame]:
        """
        Get the appropriate frame for time extraction
        
        Tries page directly first, falls back to scheduling iframe if needed.
        This supports both direct and embedded Acuity pages with better performance.
        
        Args:
            page: The browser page
            
        Returns:
            Frame for extraction or None if page is unusable
        """
        try:
            # First try the page directly (most common case for modern Acuity)
            logger.debug("Using page directly for extraction")
            return page
                
        except Exception as e:
            logger.debug(f"Error getting extraction frame: {e}")
            # Fallback to iframe if page fails
            try:
                from .async_browser_helpers import BrowserHelpers
                iframe = await BrowserHelpers.get_scheduling_frame(page, timeout=1.0)
                if iframe:
                    logger.debug("Fallback: Using scheduling iframe for extraction")
                    return iframe
                else:
                    logger.debug("No iframe fallback available")
                    return page
            except Exception:
                return page  # Final fallback to page itself
    
    @classmethod
    async def log_page_analysis(cls, page: Page, court_num: int) -> None:
        """
        Log detailed page analysis for debugging
        
        Provides comprehensive information about page state for troubleshooting.
        
        Args:
            page: The browser page to analyze
            court_num: Court number for context
        """
        try:
            current_url = page.url
            title = await page.title()
            
            logger.info(f"Court {court_num}: Page Analysis")
            logger.info(f"  URL: {current_url}")
            logger.info(f"  Title: {title}")
            
            # Check domain
            is_acuity = await cls._is_acuity_domain(page)
            logger.info(f"  Acuity Domain: {is_acuity}")
            
            # Check structure
            has_structure = await cls.has_acuity_scheduling_structure(page)
            logger.info(f"  Has Scheduling Structure: {has_structure}")
            
            # Frame information
            frame = await cls._get_extraction_frame(page)
            frame_type = "iframe" if frame != page else "page"
            logger.info(f"  Extraction Frame: {frame_type}")
            
        except Exception as e:
            logger.error(f"Court {court_num}: Error in page analysis: {e}")