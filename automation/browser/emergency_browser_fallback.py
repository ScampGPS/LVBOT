"""
Emergency Browser Fallback System
Independent booking mechanism that operates without browser pool dependencies
Used as last resort when browser pool is completely unavailable
"""

from tracking import t

import logging
from typing import Dict, Any, Optional
from datetime import date
from dataclasses import dataclass

from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from playwright.async_api import TimeoutError as PlaywrightTimeout


class EmergencyLoggerMixin:
    """Provides a shared logger for emergency browser components."""

    def __init__(self, *, logger: Optional[logging.Logger] = None) -> None:
        self.logger = logger or logging.getLogger("EmergencyBrowserFallback")


class EmergencyBrowserFactory(EmergencyLoggerMixin):
    """Creates and manages the single emergency Playwright browser/context."""

    def __init__(self, *, logger: Optional[logging.Logger] = None) -> None:
        super().__init__(logger=logger)
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.playwright = None

    async def create(self, timeouts: Dict[str, int]) -> Browser:
        if not self.playwright:
            self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-gpu",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        )

        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            locale="es-MX",
            timezone_id="America/Denver",
            ignore_https_errors=True,
        )
        self.context.set_default_timeout(timeouts["navigation"])
        self.logger.info("Emergency browser created successfully")
        return self.browser

    async def cleanup(self) -> None:
        try:
            if self.context:
                await self.context.close()
        finally:
            self.context = None

        try:
            if self.browser:
                await self.browser.close()
        finally:
            self.browser = None

        if self.playwright:
            await self.playwright.stop()
            self.playwright = None


class EmergencyFormInteractor(EmergencyLoggerMixin):
    """Handles form navigation, visibility checks, and filling."""

    def __init__(self, *, logger: Optional[logging.Logger] = None) -> None:
        super().__init__(logger=logger)

    async def ensure_form_visible(self, page: Page) -> bool:
        if await self._check_form_visible(page):
            return True
        await self._try_click_continue(page)
        await page.wait_for_timeout(1000)
        return await self._check_form_visible(page)

    async def check_form_visible(self, page: Page) -> bool:
        return await self._check_form_visible(page)

    async def try_click_continue(self, page: Page) -> None:
        await self._try_click_continue(page)

    async def fill_form(self, page: Page, user_info: Dict[str, Any]) -> bool:
        try:
            await page.fill(
                'input[name="client.firstName"]', user_info.get("first_name", "")
            )
            await page.fill(
                'input[name="client.lastName"]', user_info.get("last_name", "")
            )
            await page.fill('input[name="client.phone"]', user_info.get("phone", ""))
            await page.fill('input[name="client.email"]', user_info.get("email", ""))

            terms_checkbox = await page.query_selector(
                'input[type="checkbox"][name="confirmed"]'
            )
            if terms_checkbox:
                await terms_checkbox.check()

            self.logger.info("Emergency form filled successfully")
            return True
        except Exception as exc:
            self.logger.error("Failed to fill emergency form: %s", exc)
            return False

    async def _check_form_visible(self, page: Page) -> bool:
        try:
            field = await page.query_selector('input[name="client.firstName"]')
            return field is not None
        except Exception:
            return False

    async def _try_click_continue(self, page: Page) -> None:
        try:
            continue_btn = await page.query_selector('button:has-text("Continuar")')
            if continue_btn:
                await continue_btn.click()
                await page.wait_for_timeout(1000)
        except Exception:
            pass


class EmergencyConfirmationChecker(EmergencyLoggerMixin):
    """Submits booking and extracts confirmation/error state."""

    def __init__(self, *, logger: Optional[logging.Logger] = None) -> None:
        super().__init__(logger=logger)

    async def submit(self, page: Page) -> Dict[str, Any]:
        try:
            submit_btn = await page.query_selector(
                'button[type="submit"]:has-text("Schedule")'
            )
            if not submit_btn:
                submit_btn = await page.query_selector(
                    'button[type="submit"]:has-text("Agendar")'
                )

            if not submit_btn:
                return {"success": False, "error": "Submit button not found"}

            await submit_btn.click()
            await page.wait_for_timeout(5000)

            current_url = page.url
            if "/confirmation/" in current_url:
                confirmation_id = (
                    current_url.split("/confirmation/")[-1].split("/")[0].split("?")[0]
                )
                user_name = await self._extract_user_name(page)
                self.logger.info("Emergency booking confirmed! ID: %s", confirmation_id)
                return {
                    "success": True,
                    "confirmation_id": confirmation_id,
                    "user_name": user_name,
                }

            error_msg = await self._check_for_errors(page)
            if error_msg:
                return {"success": False, "error": error_msg}

            return {"success": False, "error": "No confirmation received"}
        except Exception as exc:
            self.logger.error("Submit failed: %s", exc)
            return {"success": False, "error": str(exc)}

    async def check_for_errors(self, page: Page) -> Optional[str]:
        return await self._check_for_errors(page)

    async def _extract_user_name(self, page: Page) -> Optional[str]:
        try:
            name_element = await page.query_selector("h1, h2, h3")
            if not name_element:
                return None
            text = await name_element.text_content()
            if text and "¡Tu cita está confirmada!" in text:
                return text.split(",")[0].strip()
        except Exception:
            return None
        return None

    async def _check_for_errors(self, page: Page) -> Optional[str]:
        selectors = [
            ".alert-danger",
            ".error-message",
            'div[role="alert"]',
            'p:has-text("error")',
            'p:has-text("Error")',
        ]

        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text:
                        return text.strip()
            except Exception:
                continue

        try:
            no_avail = await page.query_selector("text=/no.*disponib/i")
            if no_avail:
                return "No availability for selected time"
        except Exception:
            pass

        return None


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


class EmergencyBrowserFallback(EmergencyLoggerMixin):
    """
    Emergency fallback system for booking reservations
    Operates independently of browser pool infrastructure
    Simple, reliable, single-browser implementation
    """

    def __init__(self, *, logger: Optional[logging.Logger] = None):
        """Initialize emergency fallback - no pool dependencies"""
        t(
            "automation.browser.emergency_browser_fallback.EmergencyBrowserFallback.__init__"
        )
        super().__init__(logger=logger)
        self._initialized = False

        # Timeout configuration
        self.TIMEOUTS = {
            "navigation": 20000,  # 20s for page loads
            "element": 10000,  # 10s for element waits
            "booking": 60000,  # 60s total for booking
            "form": 15000,  # 15s for form operations
        }

        self.logger.info("Emergency Browser Fallback initialized")
        self._factory = EmergencyBrowserFactory(logger=self.logger)
        self._form = EmergencyFormInteractor(logger=self.logger)
        self._confirmation = EmergencyConfirmationChecker(logger=self.logger)

    async def create_browser(self) -> Browser:
        """Create a single browser instance directly with Playwright"""
        t(
            "automation.browser.emergency_browser_fallback.EmergencyBrowserFallback.create_browser"
        )
        try:
            browser = await self._factory.create(self.TIMEOUTS)
            self._initialized = True
            return browser
        except Exception as e:
            self.logger.error(f"Failed to create emergency browser: {e}")
            await self.cleanup()
            raise

    async def book_reservation(
        self,
        user_info: Dict[str, Any],
        target_date: date,
        target_time: str,
        court_preferences: list[int] = None,
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
        t(
            "automation.browser.emergency_browser_fallback.EmergencyBrowserFallback.book_reservation"
        )
        if not self._initialized:
            await self.create_browser()

        if not self._factory.context:
            raise RuntimeError("Emergency browser context not available")

        page: Optional[Page] = None
        try:
            # Create new page for booking
            page = await self._factory.context.new_page()

            # Build direct booking URL
            base_url = "https://clublavilla.as.me/schedule/7d558012/appointment/16021953/calendar/4291312"
            date_str = target_date.strftime("%Y-%m-%d")
            time_str = f"{target_time}:00"
            booking_url = f"{base_url}/datetime/{date_str}T{time_str}-06:00?appointmentTypeIds[]=16021953"

            self.logger.info(f"Emergency booking attempt for {date_str} at {time_str}")
            self.logger.info(f"Direct URL: {booking_url}")

            # Navigate directly to booking form
            try:
                await page.goto(
                    booking_url,
                    wait_until="domcontentloaded",
                    timeout=self.TIMEOUTS["navigation"],
                )
                await page.wait_for_timeout(2000)  # Let page stabilize
            except PlaywrightTimeout:
                self.logger.warning("Navigation timeout - continuing anyway")

            # Check if we reached the form
            if not await self._form.ensure_form_visible(page):
                return EmergencyBookingResult(
                    success=False, error_message="Could not reach booking form"
                )

            # Fill the form
            if not await self._form.fill_form(page, user_info):
                return EmergencyBookingResult(
                    success=False, error_message="Failed to fill booking form"
                )

            # Submit the booking
            confirmation = await self._confirmation.submit(page)

            if confirmation["success"]:
                return EmergencyBookingResult(
                    success=True,
                    message="✅ Emergency booking successful!",
                    confirmation_id=confirmation.get("confirmation_id"),
                    user_name=confirmation.get("user_name"),
                    time_reserved=target_time,
                    court_reserved=court_preferences[0] if court_preferences else None,
                )
            else:
                return EmergencyBookingResult(
                    success=False,
                    error_message=confirmation.get(
                        "error", "Booking submission failed"
                    ),
                )

        except Exception as e:
            self.logger.error(f"Emergency booking failed: {e}")
            return EmergencyBookingResult(
                success=False, error_message=f"Emergency booking error: {str(e)}"
            )
        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass

    async def _delegate_call(
        self,
        target_attr: str,
        method_name: str,
        tracking_id: str,
        *args,
        **kwargs,
    ):
        t(tracking_id)
        target = getattr(self, target_attr)
        method = getattr(target, method_name)
        return await method(*args, **kwargs)

    async def _check_form_visible(self, page: Page) -> bool:
        """Check if booking form is visible"""
        return await self._delegate_call(
            "_form",
            "check_form_visible",
            "automation.browser.emergency_browser_fallback.EmergencyBrowserFallback._check_form_visible",
            page,
        )

    async def _try_click_continue(self, page: Page):
        """Try to click continue button if present"""
        t(
            "automation.browser.emergency_browser_fallback.EmergencyBrowserFallback._try_click_continue"
        )
        await self._form.try_click_continue(page)

    async def _fill_booking_form(self, page: Page, user_info: Dict[str, Any]) -> bool:
        """Fill the booking form with user information"""
        return await self._delegate_call(
            "_form",
            "fill_form",
            "automation.browser.emergency_browser_fallback.EmergencyBrowserFallback._fill_booking_form",
            page,
            user_info,
        )

    async def _submit_booking(self, page: Page) -> Dict[str, Any]:
        """Submit the booking and check for confirmation"""
        return await self._delegate_call(
            "_confirmation",
            "submit",
            "automation.browser.emergency_browser_fallback.EmergencyBrowserFallback._submit_booking",
            page,
        )

    async def _check_for_errors(self, page: Page) -> Optional[str]:
        """Check page for error messages"""
        return await self._delegate_call(
            "_confirmation",
            "check_for_errors",
            "automation.browser.emergency_browser_fallback.EmergencyBrowserFallback._check_for_errors",
            page,
        )

    async def cleanup(self):
        """Clean up browser resources"""
        t(
            "automation.browser.emergency_browser_fallback.EmergencyBrowserFallback.cleanup"
        )
        t(
            "automation.browser.emergency_browser_fallback.EmergencyBrowserFallback.cleanup"
        )
        await self._factory.cleanup()
        self._initialized = False
        self.logger.info("Emergency browser cleaned up")

    async def __aenter__(self):
        """Context manager entry"""
        t(
            "automation.browser.emergency_browser_fallback.EmergencyBrowserFallback.__aenter__"
        )
        await self.create_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        t(
            "automation.browser.emergency_browser_fallback.EmergencyBrowserFallback.__aexit__"
        )
        await self.cleanup()


# Convenience function for quick emergency bookings
async def emergency_book(
    user_info: Dict[str, Any],
    target_date: date,
    target_time: str,
    court_preferences: list[int] = None,
) -> EmergencyBookingResult:
    """
    Quick emergency booking function
    Creates fallback browser, executes booking, and cleans up
    """
    t("automation.browser.emergency_browser_fallback.emergency_book")
    async with EmergencyBrowserFallback() as fallback:
        return await fallback.book_reservation(
            user_info=user_info,
            target_date=target_date,
            target_time=target_time,
            court_preferences=court_preferences,
        )
