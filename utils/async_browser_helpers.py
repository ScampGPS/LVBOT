"""
Unified Asynchronous Browser and Navigation Helpers
Handles all common browser operations and page interactions in a single module.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple
from playwright.async_api import Page, Frame, ElementHandle

from utils.constants import (
    SCHEDULING_IFRAME_URL_PATTERN,
    DEFAULT_TIMEOUT_SECONDS,
    FAST_POLL_INTERVAL
)

logger = logging.getLogger(__name__)


class BrowserHelpers:
    """
    Collection of asynchronous browser automation helper functions.
    This class merges the functionality of the previous AsyncBrowserHelpers and BrowserHelpers.
    """

    @staticmethod
    async def get_scheduling_frame(page: Page, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Optional[Frame]:
        """
        Get scheduling iframe by polling frames (fallback method).
        Used only when direct page access fails.
        """
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                for frame in page.frames:
                    if SCHEDULING_IFRAME_URL_PATTERN in frame.url:
                        logger.debug(f"Found scheduling frame: {frame.url}")
                        return frame
            except Exception as e:
                logger.debug(f"Error checking frames: {e}")
            await asyncio.sleep(FAST_POLL_INTERVAL)
        logger.debug(f"Scheduling frame not found after {timeout}s (this is normal for modern Acuity pages)")
        return None

    @staticmethod
    async def wait_for_iframe(page: Page, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Optional[Frame]:
        """Alias for get_scheduling_frame for compatibility."""
        return await BrowserHelpers.get_scheduling_frame(page, timeout)

    @staticmethod
    async def safe_click(element: ElementHandle, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> bool:
        """Safely click an element with error handling and state checks."""
        try:
            await element.wait_for_element_state('visible', timeout=timeout * 1000)
            await element.wait_for_element_state('enabled', timeout=timeout * 1000)
            await element.click(timeout=timeout * 1000)
            return True
        except Exception as e:
            logger.debug(f"Failed to click element: {e}")
            return False

    @staticmethod
    async def find_and_click_text(frame: Frame, text: str, exact: bool = True) -> bool:
        """Find an element by its text content and click it."""
        try:
            selector = f'*:has-text("{text}")' if exact else f'*:text-matches("{text}", "i")'
            element = await frame.query_selector(selector)
            if element:
                return await BrowserHelpers.safe_click(element)
            return False
        except Exception as e:
            logger.debug(f"Could not find and click text '{text}': {e}")
            return False

    @staticmethod
    async def find_and_click_button(frame: Frame, button_text: str) -> bool:
        """Find a button by its text and click it using multiple robust selectors."""
        selectors = [
            f'button:has-text("{button_text}")',
            f'[role="button"]:has-text("{button_text}")',
            f'a:has-text("{button_text}")',
            f'*[onclick]:has-text("{button_text}")'
        ]
        for selector in selectors:
            try:
                element = await frame.query_selector(selector)
                if element and await element.is_visible():
                    if await BrowserHelpers.safe_click(element):
                        return True
            except Exception:
                continue
        return False

    @staticmethod
    async def get_visible_text_elements(frame: Frame, pattern: Optional[str] = None) -> List[str]:
        """Get all visible text from elements, optionally matching a pattern."""
        visible_texts = []
        try:
            selector = f'*:has-text("{pattern}")' if pattern else '*'
            elements = await frame.query_selector_all(selector)
            for elem in elements:
                try:
                    if await elem.is_visible():
                        text = await elem.text_content()
                        if text and text.strip():
                            visible_texts.append(text.strip())
                except Exception:
                    continue
            return list(set(visible_texts))
        except Exception as e:
            logger.debug(f"Could not get visible text elements: {e}")
            return []

    @staticmethod
    async def fill_form_field(frame: Frame, field_selector: str, value: str, clear_first: bool = True) -> bool:
        """Fill a form field with a value, trying multiple selectors."""
        try:
            selectors = [
                field_selector,
                f'input[name="{field_selector}"]',
                f'input[id="{field_selector}"]',
                f'input[placeholder*="{field_selector}"]',
                f'textarea[name="{field_selector}"]'
            ]
            field = None
            for selector in selectors:
                field = await frame.query_selector(selector)
                if field:
                    break
            
            if field:
                if clear_first:
                    await field.fill('')
                await field.fill(value)
                return True
            return False
        except Exception as e:
            logger.debug(f"Could not fill form field '{field_selector}': {e}")
            return False

    @staticmethod
    async def select_dropdown_option(frame: Frame, dropdown_selector: str, option_text: str) -> bool:
        """Select an option from a dropdown by its visible text."""
        try:
            dropdown = await frame.query_selector(dropdown_selector)
            if dropdown:
                await dropdown.select_option(label=option_text)
                return True
            return False
        except Exception as e:
            logger.debug(f"Could not select dropdown option '{option_text}': {e}")
            return False

    @staticmethod
    async def wait_for_navigation(page: Page, trigger_action, timeout: int = 30000) -> bool:
        """Wait for a navigation to complete after performing an action."""
        try:
            async with page.expect_navigation(timeout=timeout):
                await trigger_action()
            return True
        except Exception as e:
            logger.debug(f"Navigation did not complete in time: {e}")
            return False

    @staticmethod
    async def check_element_exists(frame: Frame, selector: str) -> bool:
        """Check if an element exists on the page."""
        return await frame.query_selector(selector) is not None

    @staticmethod
    async def get_element_text(frame: Frame, selector: str) -> Optional[str]:
        """Get the text content of a single element."""
        try:
            element = await frame.query_selector(selector)
            if element:
                return await element.text_content()
        except Exception as e:
            logger.debug(f"Could not get text for selector '{selector}': {e}")
        return None

    @staticmethod
    async def wait_for_text(frame: Frame, text: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> bool:
        """Wait for a specific text to appear on the page."""
        try:
            await frame.wait_for_selector(f'*:has-text("{text}")', timeout=timeout * 1000)
            return True
        except Exception:
            return False

    @staticmethod
    async def take_screenshot(page: Page, filename: str = "screenshot.png") -> bool:
        """Take a screenshot of the current page."""
        try:
            await page.screenshot(path=filename)
            logger.info(f"Screenshot saved to {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return False

    @staticmethod
    async def scroll_to_element(frame: Frame, selector: str) -> bool:
        """Scroll an element into view if needed."""
        try:
            element = await frame.query_selector(selector)
            if element:
                await element.scroll_into_view_if_needed()
                return True
            return False
        except Exception as e:
            logger.debug(f"Could not scroll to element '{selector}': {e}")
            return False

    @staticmethod
    async def get_all_buttons(frame: Frame) -> List[Dict[str, Any]]:
        """Get all visible and enabled buttons with their text."""
        buttons = []
        try:
            elements = await frame.query_selector_all('button, [role="button"], a[href="#"]')
            for elem in elements:
                try:
                    if await elem.is_visible() and await elem.is_enabled():
                        text = await elem.text_content()
                        if text:
                            buttons.append({'text': text.strip(), 'element': elem})
                except Exception:
                    continue
            return buttons
        except Exception as e:
            logger.debug(f"Could not get all buttons: {e}")
            return []

    @staticmethod
    async def handle_dialog(page: Page, accept: bool = True, prompt_text: Optional[str] = None) -> None:
        """Sets up a one-time handler for the next dialog that appears."""
        def on_dialog(dialog):
            if prompt_text and dialog.type == 'prompt':
                asyncio.create_task(dialog.accept(prompt_text))
            elif accept:
                asyncio.create_task(dialog.accept())
            else:
                asyncio.create_task(dialog.dismiss())
            page.remove_listener("dialog", on_dialog)
        page.on("dialog", on_dialog)

    @staticmethod
    async def wait_for_element_state(element: ElementHandle, state: str, timeout: int = 5000) -> bool:
        """Wait for an element to reach a specific state (e.g., 'visible', 'enabled')."""
        try:
            await element.wait_for_element_state(state, timeout=timeout)
            return True
        except Exception:
            return False

    @staticmethod
    async def wait_for_elements(frame: Frame, selectors: List[str], timeout: float = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, bool]:
        """Wait for multiple elements concurrently and return their visibility status."""
        async def check_selector(selector):
            try:
                await frame.wait_for_selector(selector, timeout=timeout * 1000)
                return selector, True
            except Exception:
                return selector, False
        
        tasks = [check_selector(s) for s in selectors]
        results = await asyncio.gather(*tasks)
        return dict(results)

    @staticmethod
    async def extract_visible_text_by_selectors(frame: Frame, selectors: Dict[str, str]) -> Dict[str, Optional[str]]:
        """Extracts text from elements matching a dictionary of named selectors."""
        results = {}
        for name, selector in selectors.items():
            results[name] = await BrowserHelpers.get_element_text(frame, selector)
        return results

    @staticmethod
    async def wait_for_time_elements(frame: Frame, min_count: int = 1, timeout: int = 10000) -> bool:
        """Intelligently waits for calendar time slots to be loaded."""
        try:
            await frame.wait_for_function(
                f"() => {{ const buttons = document.querySelectorAll('button'); const timeButtons = Array.from(buttons).filter(btn => btn.textContent && btn.textContent.includes(':')); return timeButtons.length >= {min_count}; }}",
                timeout=timeout
            )
            return True
        except Exception as e:
            logger.debug(f"Time elements wait failed: {e}")
            return False

    @staticmethod
    async def wait_for_calendar_content(frame: Frame, timeout: int = 10000) -> bool:
        """Waits for multiple indicators that the calendar UI is fully loaded and interactive."""
        try:
            await frame.wait_for_function(
                """() => {
                    const hasTimeButtons = document.querySelectorAll('button:has-text(":")').length > 0;
                    const notLoading = document.querySelectorAll('[class*="loading"], [class*="spinner"]').length === 0;
                    const hasCalendarStructure = document.querySelectorAll('[class*="calendar"], [class*="schedule"]').length > 0;
                    return hasTimeButtons && notLoading && hasCalendarStructure;
                }""",
                timeout=timeout
            )
            return True
        except Exception as e:
            logger.debug(f"Calendar content wait failed: {e}")
            return await BrowserHelpers.wait_for_time_elements(frame, min_count=1, timeout=2000)

    @staticmethod
    async def navigate_to_court_safe(page: Page, court_number: int) -> bool:
        """Navigates to a specific court's calendar by finding the correct 'Reservar' button."""
        logger.info(f"Navigating to court {court_number} calendar...")
        try:
            frame = await BrowserHelpers.get_scheduling_frame(page)
            if not frame:
                logger.error("Could not find the scheduling iframe for court navigation.")
                return False

            reservar_buttons = await frame.query_selector_all('button:has-text("Reservar")')
            for button in reservar_buttons:
                parent_container = await button.query_selector('xpath=ancestor::div[contains(., "TENNIS CANCHA")]')
                if parent_container:
                    container_text = await parent_container.inner_text()
                    if f"TENNIS CANCHA {court_number}" in container_text:
                        if await BrowserHelpers.safe_click(button):
                            await frame.wait_for_selector('.calendar-day, .time-grid, .time-slots', timeout=5000)
                            logger.info(f"Successfully navigated to court {court_number} calendar.")
                            return True
                        else:
                            logger.error(f"Failed to click the 'Reservar' button for court {court_number}.")
                            return False
            
            logger.error(f"Could not find the 'Reservar' button for court {court_number}.")
            return False
        except Exception as e:
            logger.error(f"An error occurred while navigating to court {court_number}: {e}")
            return False
