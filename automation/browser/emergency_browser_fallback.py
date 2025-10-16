"""
Emergency Browser Fallback System
Independent booking mechanism that operates without browser pool dependencies
Used as last resort when browser pool is completely unavailable
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, date
from dataclasses import dataclass

from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from playwright.async_api import TimeoutError as PlaywrightTimeout


@dataclass
class EmergencyBookingResult:
    """Result of an emergency booking attempt"""
    success: bool
    message: Optional[str] = None
    error_message: Optional[str] = None
    court_reserved: Optional[int] = None
    time_reserved: Optional[str] = None
    confirmation_id: Optional[str] = None
    user_name: Optional[str] = None


class EmergencyBrowserFallback:
    """
    Emergency fallback system for booking reservations
    Operates independently of browser pool infrastructure
    Simple, reliable, single-browser implementation
    """
    
    def __init__(self):
        """Initialize emergency fallback - no pool dependencies"""
        self.logger = logging.getLogger('EmergencyBrowserFallback')
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.playwright = None
        self._initialized = False
        
        # Timeout configuration
        self.TIMEOUTS = {
            'navigation': 20000,  # 20s for page loads
            'element': 10000,     # 10s for element waits
            'booking': 60000,     # 60s total for booking
            'form': 15000         # 15s for form operations
        }
        
        self.logger.info("Emergency Browser Fallback initialized")
    
    async def create_browser(self) -> Browser:
        """Create a single browser instance directly with Playwright"""
        try:
            if not self.playwright:
                self.playwright = await async_playwright().start()
                
            # Create browser with simple configuration
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process'
                ]
            )
            
            # Create context with basic settings
            self.context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                locale='es-MX',
                timezone_id='America/Denver',
                ignore_https_errors=True
            )
            
            # Set default timeout
            self.context.set_default_timeout(self.TIMEOUTS['navigation'])
            
            self._initialized = True
            self.logger.info("Emergency browser created successfully")
            return self.browser
            
        except Exception as e:
            self.logger.error(f"Failed to create emergency browser: {e}")
            await self.cleanup()
            raise
    
    async def book_reservation(
        self,
        user_info: Dict[str, Any],
        target_date: date,
        target_time: str,
        court_preferences: list[int] = None
    ) -> EmergencyBookingResult:
        """
        Execute a booking with single browser - simple and reliable
        
        Args:
            user_info: User details (email, first_name, last_name, phone)
            target_date: Date to book
            target_time: Time slot (e.g., "09:00")
            court_preferences: List of court numbers to try
            
        Returns:
            EmergencyBookingResult with booking outcome
        """
        if not self._initialized:
            await self.create_browser()
            
        page = None
        try:
            # Create new page for booking
            page = await self.context.new_page()
            
            # Build direct booking URL
            base_url = "https://clublavilla.as.me/schedule/7d558012/appointment/16021953/calendar/4291312"
            date_str = target_date.strftime("%Y-%m-%d")
            time_str = f"{target_time}:00"
            booking_url = f"{base_url}/datetime/{date_str}T{time_str}-06:00?appointmentTypeIds[]=16021953"
            
            self.logger.info(f"Emergency booking attempt for {date_str} at {time_str}")
            self.logger.info(f"Direct URL: {booking_url}")
            
            # Navigate directly to booking form
            try:
                await page.goto(booking_url, wait_until='domcontentloaded', timeout=self.TIMEOUTS['navigation'])
                await page.wait_for_timeout(2000)  # Let page stabilize
            except PlaywrightTimeout:
                self.logger.warning("Navigation timeout - continuing anyway")
            
            # Check if we reached the form
            form_visible = await self._check_form_visible(page)
            if not form_visible:
                # Try clicking continue if needed
                await self._try_click_continue(page)
                await page.wait_for_timeout(1000)
                form_visible = await self._check_form_visible(page)
            
            if not form_visible:
                return EmergencyBookingResult(
                    success=False,
                    error_message="Could not reach booking form"
                )
            
            # Fill the form
            form_filled = await self._fill_booking_form(page, user_info)
            if not form_filled:
                return EmergencyBookingResult(
                    success=False,
                    error_message="Failed to fill booking form"
                )
            
            # Submit the booking
            confirmation = await self._submit_booking(page)
            
            if confirmation['success']:
                return EmergencyBookingResult(
                    success=True,
                    message=f"✅ Emergency booking successful!",
                    confirmation_id=confirmation.get('confirmation_id'),
                    user_name=confirmation.get('user_name'),
                    time_reserved=target_time,
                    court_reserved=court_preferences[0] if court_preferences else None
                )
            else:
                return EmergencyBookingResult(
                    success=False,
                    error_message=confirmation.get('error', 'Booking submission failed')
                )
                
        except Exception as e:
            self.logger.error(f"Emergency booking failed: {e}")
            return EmergencyBookingResult(
                success=False,
                error_message=f"Emergency booking error: {str(e)}"
            )
        finally:
            if page:
                try:
                    await page.close()
                except:
                    pass
    
    async def _check_form_visible(self, page: Page) -> bool:
        """Check if booking form is visible"""
        try:
            # Check for form fields
            first_name_field = await page.query_selector('input[name="client.firstName"]')
            return first_name_field is not None
        except:
            return False
    
    async def _try_click_continue(self, page: Page):
        """Try to click continue button if present"""
        try:
            continue_btn = await page.query_selector('button:has-text("Continuar")')
            if continue_btn:
                await continue_btn.click()
                await page.wait_for_timeout(1000)
        except:
            pass
    
    async def _fill_booking_form(self, page: Page, user_info: Dict[str, Any]) -> bool:
        """Fill the booking form with user information"""
        try:
            # Fill form fields with proper field names
            await page.fill('input[name="client.firstName"]', user_info.get('first_name', ''))
            await page.fill('input[name="client.lastName"]', user_info.get('last_name', ''))
            await page.fill('input[name="client.phone"]', user_info.get('phone', ''))
            await page.fill('input[name="client.email"]', user_info.get('email', ''))
            
            # Accept terms if checkbox exists
            try:
                terms_checkbox = await page.query_selector('input[type="checkbox"][name="confirmed"]')
                if terms_checkbox:
                    await terms_checkbox.check()
            except:
                pass
                
            self.logger.info("Emergency form filled successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to fill emergency form: {e}")
            return False
    
    async def _submit_booking(self, page: Page) -> Dict[str, Any]:
        """Submit the booking and check for confirmation"""
        try:
            # Find and click submit button
            submit_btn = await page.query_selector('button[type="submit"]:has-text("Schedule")')
            if not submit_btn:
                submit_btn = await page.query_selector('button[type="submit"]:has-text("Agendar")')
            
            if not submit_btn:
                return {'success': False, 'error': 'Submit button not found'}
            
            # Click submit
            await submit_btn.click()
            
            # Wait for navigation or confirmation
            await page.wait_for_timeout(5000)
            
            # Check for confirmation
            current_url = page.url
            if '/confirmation/' in current_url:
                # Extract confirmation ID
                conf_id = current_url.split('/confirmation/')[-1].split('/')[0].split('?')[0]
                
                # Try to get user name from confirmation
                user_name = None
                try:
                    name_element = await page.query_selector('h1, h2, h3')
                    if name_element:
                        text = await name_element.text_content()
                        if '¡Tu cita está confirmada!' in text:
                            user_name = text.split(',')[0].strip()
                except:
                    pass
                
                self.logger.info(f"Emergency booking confirmed! ID: {conf_id}")
                return {
                    'success': True,
                    'confirmation_id': conf_id,
                    'user_name': user_name
                }
            
            # Check for error messages
            error_msg = await self._check_for_errors(page)
            if error_msg:
                return {'success': False, 'error': error_msg}
                
            return {'success': False, 'error': 'No confirmation received'}
            
        except Exception as e:
            self.logger.error(f"Submit failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _check_for_errors(self, page: Page) -> Optional[str]:
        """Check page for error messages"""
        try:
            # Common error selectors
            error_selectors = [
                '.alert-danger',
                '.error-message',
                'div[role="alert"]',
                'p:has-text("error")',
                'p:has-text("Error")'
            ]
            
            for selector in error_selectors:
                error_elem = await page.query_selector(selector)
                if error_elem:
                    error_text = await error_elem.text_content()
                    return error_text.strip()
                    
            # Check for "no availability" messages
            no_avail = await page.query_selector('text=/no.*disponib/i')
            if no_avail:
                return "No availability for selected time"
                
        except:
            pass
            
        return None
    
    async def cleanup(self):
        """Clean up browser resources"""
        try:
            if self.context:
                await self.context.close()
                self.context = None
                
            if self.browser:
                await self.browser.close()
                self.browser = None
                
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
                
            self._initialized = False
            self.logger.info("Emergency browser cleaned up")
            
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")
    
    async def __aenter__(self):
        """Context manager entry"""
        await self.create_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.cleanup()


# Convenience function for quick emergency bookings
async def emergency_book(
    user_info: Dict[str, Any],
    target_date: date,
    target_time: str,
    court_preferences: list[int] = None
) -> EmergencyBookingResult:
    """
    Quick emergency booking function
    Creates fallback browser, executes booking, and cleans up
    """
    async with EmergencyBrowserFallback() as fallback:
        return await fallback.book_reservation(
            user_info=user_info,
            target_date=target_date,
            target_time=target_time,
            court_preferences=court_preferences
        )