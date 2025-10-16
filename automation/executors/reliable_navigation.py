"""
Reliable Navigation Module - Playwright Workaround
==================================================

PURPOSE: Centralized navigation that bypasses Playwright's hanging goto() issue
USED BY: All booking executors (AsyncBookingExecutor, SmartAsyncBookingExecutor, etc.)
APPROACH: Event-driven navigation with manual timeout control
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ReliableNavigation:
    """Centralized navigation utility that works around Playwright goto() hanging"""
    
    @staticmethod
    async def navigate_to_url(
        page,
        url: str,
        timeout_seconds: int = 10,
        enable_network_logging: bool = False
    ) -> Dict[str, Any]:
        """
        Navigate to URL using event-driven approach to bypass Playwright hanging
        
        Args:
            page: Playwright page object
            url: Target URL to navigate to
            timeout_seconds: Maximum time to wait for navigation
            enable_network_logging: Whether to log network requests
            
        Returns:
            Dict with navigation result:
            {
                'success': bool,
                'navigation_time': float,
                'dom_ready_time': float,
                'error': str (if failed),
                'status_code': int (if available)
            }
        """
        start_time = time.time()
        
        # Setup event tracking
        dom_ready = asyncio.Event()
        navigation_response = None
        request_count = 0
        response_count = 0
        
        def on_dom_ready():
            dom_time = time.time() - start_time
            logger.info(f"[RELIABLE NAV] DOM ready at {dom_time:.2f}s")
            dom_ready.set()
        
        def on_request(request):
            nonlocal request_count
            request_count += 1
            if enable_network_logging:
                elapsed = time.time() - start_time
                logger.debug(f"[RELIABLE NAV {elapsed:.1f}s] REQ #{request_count}: {request.url[:80]}...")
        
        def on_response(response):
            nonlocal response_count, navigation_response
            response_count += 1
            if enable_network_logging:
                elapsed = time.time() - start_time
                logger.debug(f"[RELIABLE NAV {elapsed:.1f}s] RES #{response_count}: {response.status} {response.url[:80]}...")
            
            # Capture main document response
            if response.url == url or response.url.startswith(url.split('?')[0]):
                navigation_response = response
        
        # Attach event listeners
        page.on('domcontentloaded', on_dom_ready)
        if enable_network_logging:
            page.on('request', on_request)
            page.on('response', on_response)
        
        try:
            logger.info(f"[RELIABLE NAV] Starting navigation to: {url[:100]}...")
            
            # Start navigation with minimal wait condition (just commit, not domcontentloaded)
            navigation_task = asyncio.create_task(
                page.goto(url, wait_until='commit', timeout=5000)
            )
            
            # Wait for DOM ready event with our timeout
            try:
                await asyncio.wait_for(dom_ready.wait(), timeout=timeout_seconds)
                dom_ready_time = time.time() - start_time
                logger.info(f"[RELIABLE NAV] DOM ready in {dom_ready_time:.2f}s")
                
                # Wait a bit more for navigation task to complete (but don't block on it)
                try:
                    await asyncio.wait_for(navigation_task, timeout=2.0)
                    navigation_time = time.time() - start_time
                    logger.info(f"[RELIABLE NAV] Navigation task completed in {navigation_time:.2f}s")
                except asyncio.TimeoutError:
                    # Navigation task is hanging, but DOM is ready so we can proceed
                    navigation_time = time.time() - start_time
                    logger.warning(f"[RELIABLE NAV] Navigation task hanging after {navigation_time:.2f}s, proceeding anyway")
                    navigation_task.cancel()
                
                return {
                    'success': True,
                    'navigation_time': navigation_time,
                    'dom_ready_time': dom_ready_time,
                    'status_code': navigation_response.status if navigation_response else 200,
                    'requests': request_count,
                    'responses': response_count
                }
                
            except asyncio.TimeoutError:
                # DOM never loaded
                failed_time = time.time() - start_time
                logger.error(f"[RELIABLE NAV] DOM never loaded after {failed_time:.2f}s")
                navigation_task.cancel()
                
                return {
                    'success': False,
                    'navigation_time': failed_time,
                    'error': f'DOM never loaded after {timeout_seconds}s',
                    'requests': request_count,
                    'responses': response_count
                }
                
        except Exception as e:
            error_time = time.time() - start_time
            logger.error(f"[RELIABLE NAV] Navigation error after {error_time:.2f}s: {e}")
            
            return {
                'success': False,
                'navigation_time': error_time,
                'error': str(e),
                'requests': request_count,
                'responses': response_count
            }
            
        finally:
            # Clean up event listeners
            try:
                page.remove_listener('domcontentloaded', on_dom_ready)
                if enable_network_logging:
                    page.remove_listener('request', on_request)
                    page.remove_listener('response', on_response)
            except:
                pass


    @staticmethod
    async def navigate_with_form_check(
        page,
        url: str,
        form_selectors: list = None,
        timeout_seconds: int = 15
    ) -> Dict[str, Any]:
        """
        Navigate and check for form availability (for booking pages)
        
        Args:
            page: Playwright page object
            url: Target URL to navigate to
            form_selectors: List of selectors to check for form readiness
            timeout_seconds: Maximum time to wait
            
        Returns:
            Dict with navigation result including form_ready status
        """
        if form_selectors is None:
            form_selectors = [
                'input[name="client.firstName"]',
                'input[name="client.lastName"]',
                'input[name*="firstName"]',
                'input[name*="lastName"]'
            ]
        
        # First, do reliable navigation
        nav_result = await ReliableNavigation.navigate_to_url(
            page, url, timeout_seconds, enable_network_logging=True
        )
        
        if not nav_result['success']:
            return nav_result
        
        # After DOM is ready, check for form elements
        logger.info("[RELIABLE NAV] Checking for booking form...")
        
        try:
            # Wait for form elements to appear
            for selector in form_selectors:
                try:
                    await page.wait_for_selector(selector, state='visible', timeout=3000)
                    logger.info(f"[RELIABLE NAV] Form ready - found {selector}")
                    nav_result['form_ready'] = True
                    nav_result['form_selector'] = selector
                    return nav_result
                except:
                    continue
            
            # No form found
            logger.warning("[RELIABLE NAV] No booking form detected")
            nav_result['form_ready'] = False
            nav_result['reason'] = 'no_booking_form_found'
            return nav_result
            
        except Exception as e:
            logger.error(f"[RELIABLE NAV] Error checking form: {e}")
            nav_result['form_ready'] = False
            nav_result['form_error'] = str(e)
            return nav_result