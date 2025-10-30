"""Reservation cancellation service using disposable browsers."""

from __future__ import annotations

import logging
from typing import Optional

from playwright.async_api import async_playwright, Browser, Page


class ReservationCancellationService:
    """Service to cancel reservations using temporary, disposable browsers."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    async def cancel_reservation(self, cancel_url: str) -> dict[str, any]:
        """
        Cancel a reservation by navigating to the cancel URL and clicking the CANCELAR button.

        Args:
            cancel_url: The confirmation page URL (e.g., https://clublavilla.as.me/schedule/.../confirmation/...)

        Returns:
            dict with 'success' (bool), 'message' (str), and optionally 'error' (str)
        """
        self.logger.info("Starting reservation cancellation for URL: %s", cancel_url[:80])

        try:
            async with async_playwright() as p:
                # Launch headless browser (temporary, disposable)
                browser: Browser = await p.chromium.launch(headless=True)
                self.logger.debug("Temporary browser launched for cancellation")

                try:
                    # Create a new page
                    page: Page = await browser.new_page()

                    # Navigate to confirmation page
                    self.logger.info("Navigating to confirmation page...")
                    await page.goto(cancel_url, wait_until="networkidle", timeout=15000)

                    # Wait for page to load
                    await page.wait_for_timeout(2000)

                    # Look for CANCELAR button
                    self.logger.info("Looking for CANCELAR button...")
                    cancel_button = await page.query_selector('button:has-text("Cancelar"), button:has-text("CANCELAR")')

                    if not cancel_button:
                        # Try alternative selectors
                        cancel_button = await page.query_selector('button:has-text("Cancel")')

                    if not cancel_button:
                        self.logger.warning("CANCELAR button not found on page")
                        return {
                            "success": False,
                            "message": "Could not find cancel button on confirmation page",
                            "error": "CANCELAR button not found"
                        }

                    # Click the CANCELAR button
                    self.logger.info("Clicking CANCELAR button...")
                    await cancel_button.click()

                    # Wait for cancellation to process
                    await page.wait_for_timeout(2000)

                    # Check for cancellation confirmation
                    page_content = await page.content()
                    page_text = (await page.text_content("body") or "").lower()

                    # Check for cancellation success messages
                    success_indicators = [
                        "cancelada",
                        "cancelled",
                        "canceled",
                        "eliminada",
                        "removed"
                    ]

                    if any(indicator in page_text for indicator in success_indicators):
                        self.logger.info("✅ Reservation cancelled successfully")
                        return {
                            "success": True,
                            "message": "Reservation cancelled successfully"
                        }
                    else:
                        # Check if there was an error message
                        error_indicators = ["error", "problema", "no se pudo"]
                        if any(indicator in page_text for indicator in error_indicators):
                            self.logger.warning("Cancellation may have failed - error message detected")
                            return {
                                "success": False,
                                "message": "Could not cancel reservation - an error occurred",
                                "error": "Error message detected on page"
                            }

                        # Unclear result
                        self.logger.warning("Unclear cancellation result - no success or error message found")
                        return {
                            "success": False,
                            "message": "Could not confirm cancellation - please check manually",
                            "error": "No confirmation message found"
                        }

                finally:
                    # Always close the browser
                    await browser.close()
                    self.logger.debug("Temporary browser closed")

        except Exception as exc:
            self.logger.error("Failed to cancel reservation: %s", exc, exc_info=True)
            return {
                "success": False,
                "message": f"Cancellation failed: {str(exc)}",
                "error": str(exc)
            }


__all__ = ["ReservationCancellationService"]
