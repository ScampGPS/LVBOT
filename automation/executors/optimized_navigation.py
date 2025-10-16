"""
Optimized navigation strategies for faster page loading
"""

import asyncio
import logging
from typing import Optional, Tuple
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)

class OptimizedNavigation:
    """Handles optimized navigation strategies for booking URLs"""
    
    @staticmethod
    async def navigate_with_progressive_fallback(
        page: Page, 
        url: str, 
        max_timeout: int = 30000
    ) -> Tuple[bool, float]:
        """
        Navigate to URL with progressive fallback strategies
        
        Args:
            page: Playwright page object
            url: URL to navigate to
            max_timeout: Maximum timeout in milliseconds
            
        Returns:
            Tuple of (success, navigation_time_seconds)
        """
        import time
        start_time = time.time()
        
        # Strategy 1: Try fast commit-only navigation
        try:
            logger.info("Attempting fast navigation (commit only)...")
            await page.goto(url, wait_until='commit', timeout=5000)
            
            # Wait for form to appear
            try:
                await page.wait_for_selector('form', timeout=5000)
                nav_time = time.time() - start_time
                logger.info(f"✅ Fast navigation successful in {nav_time:.2f}s")
                return True, nav_time
            except PlaywrightTimeout:
                logger.warning("Form not found after commit, trying next strategy...")
        except Exception as e:
            logger.debug(f"Fast navigation failed: {e}")
        
        # Strategy 2: Try domcontentloaded
        try:
            logger.info("Attempting standard navigation (domcontentloaded)...")
            await page.goto(url, wait_until='domcontentloaded', timeout=10000)
            
            # Give dynamic content time to load
            await page.wait_for_timeout(2000)
            
            # Check for form
            form_present = await page.locator('form').count() > 0
            if form_present:
                nav_time = time.time() - start_time
                logger.info(f"✅ Standard navigation successful in {nav_time:.2f}s")
                return True, nav_time
            else:
                logger.warning("Form not present after domcontentloaded")
        except Exception as e:
            logger.debug(f"Standard navigation failed: {e}")
        
        # Strategy 3: Full networkidle (fallback)
        try:
            logger.info("Attempting full navigation (networkidle)...")
            await page.goto(url, wait_until='networkidle', timeout=max_timeout)
            nav_time = time.time() - start_time
            logger.info(f"✅ Full navigation completed in {nav_time:.2f}s")
            return True, nav_time
        except PlaywrightTimeout:
            nav_time = time.time() - start_time
            logger.warning(f"Navigation timed out after {nav_time:.2f}s, but page might be usable")
            
            # Check if form is present despite timeout
            try:
                form_present = await page.locator('form').count() > 0
                if form_present:
                    logger.info("Form is present despite timeout, continuing...")
                    return True, nav_time
            except:
                pass
                
            return False, nav_time
        except Exception as e:
            nav_time = time.time() - start_time
            logger.error(f"Navigation failed after {nav_time:.2f}s: {e}")
            return False, nav_time
    
    @staticmethod
    async def ensure_page_ready(page: Page, timeout: int = 10000) -> bool:
        """
        Ensure page is ready for interaction
        
        Args:
            page: Playwright page object
            timeout: Timeout in milliseconds
            
        Returns:
            True if page is ready, False otherwise
        """
        try:
            # Wait for any loading indicators to disappear
            loading_selectors = [
                '.loading',
                '.spinner',
                '[class*="load"]',
                '[class*="spin"]',
                '.loader'
            ]
            
            for selector in loading_selectors:
                try:
                    await page.wait_for_selector(selector, state='hidden', timeout=1000)
                except:
                    pass  # Selector might not exist
            
            # Ensure form is present and visible
            await page.wait_for_selector('form', state='visible', timeout=timeout)
            
            # Ensure key form fields are present (phone field might take longer to render)
            key_fields = [
                'input[name="client.firstName"]', 
                'input[name="client.lastName"]',
                'input[name="client.email"]'
            ]
            for field in key_fields:
                await page.wait_for_selector(field, state='visible', timeout=2000)
            
            # Phone field might be dynamically loaded, check for it separately
            try:
                await page.wait_for_selector('input[name="client.phone"]', state='attached', timeout=3000)
            except:
                logger.debug("Phone field not immediately available, but form is likely ready")
            
            # Check page is responsive
            await page.evaluate('() => document.readyState')
            
            return True
            
        except Exception as e:
            logger.error(f"Page readiness check failed: {e}")
            return False
    
    @staticmethod
    async def navigate_and_validate(
        page: Page,
        url: str,
        expected_form_fields: Optional[list] = None
    ) -> Tuple[bool, str]:
        """
        Navigate to URL and validate the page loaded correctly
        
        Args:
            page: Playwright page object
            url: URL to navigate to
            expected_form_fields: List of expected form field selectors
            
        Returns:
            Tuple of (success, message)
        """
        # Navigate with optimized strategy
        nav_success, nav_time = await OptimizedNavigation.navigate_with_progressive_fallback(
            page, url
        )
        
        if not nav_success:
            return False, f"Navigation failed after {nav_time:.2f}s"
        
        # Ensure page is ready
        page_ready = await OptimizedNavigation.ensure_page_ready(page)
        if not page_ready:
            return False, "Page not ready for interaction"
        
        # Validate expected form fields if provided
        if expected_form_fields:
            for field_selector in expected_form_fields:
                try:
                    field_present = await page.locator(field_selector).count() > 0
                    if not field_present:
                        return False, f"Expected field not found: {field_selector}"
                except Exception as e:
                    return False, f"Error checking field {field_selector}: {e}"
        
        return True, f"Navigation successful in {nav_time:.2f}s"