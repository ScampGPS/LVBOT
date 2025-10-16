"""
Stateful Browser Refresh Manager - Maintains page state during refresh
======================================================================

PURPOSE: Refresh browsers while preserving user's current state (selected time slots, etc.)
PATTERN: State capture and restoration pattern for seamless browser refresh
DEPENDENCIES: playwright, async_browser_helpers, logging

This module ensures that when a browser is refreshed, it returns to the exact
state it was in before the refresh, including any selected time slots or
partially filled forms.
"""
from utils.tracking import t

import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from playwright.async_api import Page, Frame, ElementHandle

from lvbot.automation.browser.async_browser_helpers import BrowserHelpers
from lvbot.infrastructure.constants import ACUITY_EMBED_URL, BrowserTimeouts

logger = logging.getLogger(__name__)


class PageState:
    """Represents the captured state of a page before refresh"""
    
    def __init__(self):
        """Initialize page state container"""
        t('archive.legacy_modules.browser_cleanup.stateful_browser_refresh.PageState.__init__')
        self.url: str = ""
        self.court_number: Optional[int] = None
        self.selected_date: Optional[str] = None
        self.selected_time: Optional[str] = None
        self.form_visible: bool = False
        self.form_data: Dict[str, str] = {}
        self.timestamp: datetime = datetime.now()
        
    def __str__(self) -> str:
        """String representation of page state"""
        t('archive.legacy_modules.browser_cleanup.stateful_browser_refresh.PageState.__str__')
        parts = [f"URL: {self.url}"]
        if self.court_number:
            parts.append(f"Court: {self.court_number}")
        if self.selected_time:
            parts.append(f"Time: {self.selected_time}")
        if self.form_visible:
            parts.append("Form: Visible")
        return " | ".join(parts)


class StatefulBrowserRefresh:
    """
    Handles browser refresh operations while maintaining page state.
    
    This class captures the current state of a page (selected times, forms, etc.)
    before refresh and restores it after the refresh completes.
    """
    
    def __init__(self):
        """Initialize stateful refresh handler"""
        t('archive.legacy_modules.browser_cleanup.stateful_browser_refresh.StatefulBrowserRefresh.__init__')
        self.logger = logger
        self.browser_helpers = BrowserHelpers()
        
    async def refresh_with_state(self, page: Page) -> Tuple[bool, str]:
        """
        Refresh page while maintaining its current state
        
        Args:
            page: Playwright page to refresh
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        t('archive.legacy_modules.browser_cleanup.stateful_browser_refresh.StatefulBrowserRefresh.refresh_with_state')
        try:
            self.logger.info("🔄 Starting stateful page refresh")
            
            # Capture current state
            state = await self._capture_page_state(page)
            self.logger.info(f"📸 Captured state: {state}")
            
            # Perform refresh
            await page.reload(wait_until='domcontentloaded', timeout=BrowserTimeouts.PAGE_LOAD)
            self.logger.info("✅ Page refreshed")
            
            # Restore state
            success = await self._restore_page_state(page, state)
            
            if success:
                return True, "Page refreshed and state restored successfully"
            else:
                return False, "Page refreshed but state restoration failed"
                
        except Exception as e:
            self.logger.error(f"❌ Stateful refresh failed: {e}")
            return False, f"Refresh failed: {str(e)}"
    
    async def _capture_page_state(self, page: Page) -> PageState:
        """
        Capture current page state
        
        Args:
            page: Page to capture state from
            
        Returns:
            PageState object containing captured state
        """
        t('archive.legacy_modules.browser_cleanup.stateful_browser_refresh.StatefulBrowserRefresh._capture_page_state')
        state = PageState()
        state.url = page.url
        
        self.logger.info(f"Capturing page state from URL: {state.url}")
        
        # Log if we're on a booking form
        if '/datetime/' in state.url:
            self.logger.warning("WARNING: Page is on a booking form URL during state capture!")
            self.logger.warning("This will cause issues when refreshing as it will restore to this form.")
        
        try:
            # Check if we're on a court page
            state.court_number = await self._extract_court_number(page)
            
            # Check for selected time slot
            state.selected_time = await self._extract_selected_time(page)
            
            # Check if form is visible
            state.form_visible = await self._is_form_visible(page)
            
            # Capture form data if visible
            if state.form_visible:
                state.form_data = await self._extract_form_data(page)
                
        except Exception as e:
            self.logger.warning(f"Error capturing state: {e}")
            
        return state
    
    async def _restore_page_state(self, page: Page, state: PageState) -> bool:
        """
        Restore page to captured state
        
        Args:
            page: Page to restore state to
            state: Previously captured state
            
        Returns:
            bool: True if restoration successful
        """
        t('archive.legacy_modules.browser_cleanup.stateful_browser_refresh.StatefulBrowserRefresh._restore_page_state')
        try:
            # Log what state we're trying to restore
            self.logger.info(f"Attempting to restore state: {state}")
            
            # If no special state to restore, we're done
            if not state.court_number and not state.selected_time:
                self.logger.info("No special state to restore")
                return True
                
            # Navigate to court if needed
            if state.court_number and ACUITY_EMBED_URL not in page.url:
                court_url = f"{ACUITY_EMBED_URL}?appointmentType=5{6000000 + state.court_number}"
                await page.goto(court_url, wait_until='networkidle')
                await page.wait_for_timeout(2000)
                
            # Re-select time slot if one was selected
            if state.selected_time:
                self.logger.info(f"🕒 Restoring selected time: {state.selected_time}")
                success = await self._click_time_slot(page, state.selected_time)
                
                if not success:
                    self.logger.warning(f"Could not restore time slot: {state.selected_time}")
                    return False
                    
                # Wait for form to appear if it was visible
                if state.form_visible:
                    await page.wait_for_timeout(2000)
                    
                    # Restore form data
                    if state.form_data:
                        await self._restore_form_data(page, state.form_data)
                        
            return True
            
        except Exception as e:
            self.logger.error(f"Error restoring state: {e}")
            return False
    
    async def _extract_court_number(self, page: Page) -> Optional[int]:
        """Extract court number from current page"""
        t('archive.legacy_modules.browser_cleanup.stateful_browser_refresh.StatefulBrowserRefresh._extract_court_number')
        try:
            # Check URL for court number
            url = page.url
            if 'appointmentType=' in url:
                appointment_type = url.split('appointmentType=')[1].split('&')[0]
                if appointment_type.startswith('56'):
                    court_num = int(appointment_type) - 56000000
                    if 1 <= court_num <= 5:
                        return court_num
                        
            # Check page content for court number
            content = await page.content()
            for court in range(1, 6):
                if f"TENNIS CANCHA {court}" in content:
                    return court
                    
        except Exception as e:
            self.logger.debug(f"Could not extract court number: {e}")
            
        return None
    
    async def _extract_selected_time(self, page: Page) -> Optional[str]:
        """Extract currently selected time slot"""
        t('archive.legacy_modules.browser_cleanup.stateful_browser_refresh.StatefulBrowserRefresh._extract_selected_time')
        try:
            # Look for highlighted/selected time button
            selected_buttons = await page.query_selector_all('button[class*="selected"], button[aria-pressed="true"]')
            
            for button in selected_buttons:
                text = await button.text_content()
                if text and ':' in text:  # Time format check
                    return text.strip()
                    
            # Alternative: Check for time in form or confirmation
            time_elements = await page.query_selector_all('[class*="time"], [class*="hora"]')
            for elem in time_elements:
                text = await elem.text_content()
                if text and ':' in text and ('AM' in text or 'PM' in text):
                    return text.strip()
                    
        except Exception as e:
            self.logger.debug(f"Could not extract selected time: {e}")
            
        return None
    
    async def _is_form_visible(self, page: Page) -> bool:
        """Check if booking form is visible"""
        t('archive.legacy_modules.browser_cleanup.stateful_browser_refresh.StatefulBrowserRefresh._is_form_visible')
        try:
            # Check for common form indicators
            form_selectors = [
                'input[name*="firstName"]',
                'input[name*="lastName"]',
                'input[placeholder*="Nombre"]',
                'form#appointmentForm',
                'button:has-text("CONFIRMAR CITA")'
            ]
            
            for selector in form_selectors:
                element = await page.query_selector(selector)
                if element and await element.is_visible():
                    return True
                    
        except Exception as e:
            self.logger.debug(f"Error checking form visibility: {e}")
            
        return False
    
    async def _extract_form_data(self, page: Page) -> Dict[str, str]:
        """Extract data from visible form fields"""
        t('archive.legacy_modules.browser_cleanup.stateful_browser_refresh.StatefulBrowserRefresh._extract_form_data')
        form_data = {}
        
        try:
            # Common form fields to check
            field_mappings = {
                'nombre': ['input[name*="firstName"]', 'input[placeholder*="Nombre"]'],
                'apellidos': ['input[name*="lastName"]', 'input[placeholder*="Apellidos"]'],
                'telefono': ['input[type="tel"]', 'input[name*="phone"]'],
                'correo': ['input[type="email"]', 'input[name*="email"]']
            }
            
            for field_name, selectors in field_mappings.items():
                for selector in selectors:
                    element = await page.query_selector(selector)
                    if element:
                        value = await element.input_value()
                        if value:
                            form_data[field_name] = value
                        break
                        
        except Exception as e:
            self.logger.debug(f"Error extracting form data: {e}")
            
        return form_data
    
    async def _click_time_slot(self, page: Page, time_text: str) -> bool:
        """Click on a specific time slot button"""
        t('archive.legacy_modules.browser_cleanup.stateful_browser_refresh.StatefulBrowserRefresh._click_time_slot')
        try:
            # Wait for time slots to be available
            await page.wait_for_selector('button:has-text(":")', timeout=5000)
            
            # Find and click the specific time
            time_buttons = await page.query_selector_all('button')
            
            for button in time_buttons:
                button_text = await button.text_content()
                if button_text and time_text in button_text:
                    if await button.is_visible() and await button.is_enabled():
                        await button.click()
                        self.logger.info(f"✅ Clicked time slot: {time_text}")
                        return True
                        
        except Exception as e:
            self.logger.error(f"Error clicking time slot: {e}")
            
        return False
    
    async def _restore_form_data(self, page: Page, form_data: Dict[str, str]) -> bool:
        """Restore previously entered form data"""
        t('archive.legacy_modules.browser_cleanup.stateful_browser_refresh.StatefulBrowserRefresh._restore_form_data')
        try:
            from lvbot.automation.forms.acuity_booking_form import AcuityBookingForm
            
            form_handler = AcuityBookingForm()
            
            # Use the form handler's fill methods but don't submit
            for field_name, value in form_data.items():
                if field_name in form_handler.FORM_SELECTORS:
                    selector = form_handler.FORM_SELECTORS[field_name]
                    await form_handler._fill_field(page, selector, value, field_name)
                    
            self.logger.info(f"✅ Restored form data: {list(form_data.keys())}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error restoring form data: {e}")
            return False