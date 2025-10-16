"""
Browser Refresh Manager - Modular browser refresh to prevent memory leaks
=========================================================================

PURPOSE: Periodically refresh browsers in the pool to prevent memory leaks
PATTERN: DRY principle - reusable refresh logic for any browser pool
SCOPE: Works with SimpleBrowserPool and other pool implementations

This module provides automatic browser refresh functionality that can be
attached to any browser pool implementation.
"""

import logging
import threading
import time
from typing import Optional, Callable, Dict, Any
from datetime import datetime, timedelta


class BrowserRefreshManager:
    """
    Manages periodic browser refresh for memory leak prevention
    
    This is a modular component that can work with any browser pool
    that implements the required interface.
    """
    
    def __init__(self, 
                 browser_pool,
                 refresh_interval: int = 900,  # 15 minutes default
                 logger: Optional[logging.Logger] = None):
        """
        Initialize browser refresh manager
        
        Args:
            browser_pool: Browser pool instance with refresh_browser method
            refresh_interval: Seconds between refreshes (default 15 minutes)
            logger: Optional logger instance
        """
        self.browser_pool = browser_pool
        self.refresh_interval = refresh_interval
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        
        # Refresh state
        self._running = False
        self._refresh_thread = None
        self._last_refresh_times = {}  # Track per-browser refresh times
        
        # Statistics
        self.stats = {
            'total_refreshes': 0,
            'successful_refreshes': 0,
            'failed_refreshes': 0,
            'last_refresh_cycle': None
        }
    
    def start(self):
        """Start the refresh manager"""
        if self._running:
            self.logger.warning("Refresh manager already running")
            return
        
        self.logger.info("="*60)
        self.logger.info("BROWSER REFRESH MANAGER: Starting")
        self.logger.info(f"Refresh interval: {self.refresh_interval} seconds ({self.refresh_interval/60:.1f} minutes)")
        self.logger.info("="*60)
        
        self._running = True
        self._refresh_thread = threading.Thread(
            target=self._refresh_loop,
            daemon=True,
            name="BrowserRefreshManager"
        )
        self._refresh_thread.start()
    
    def stop(self):
        """Stop the refresh manager"""
        self.logger.info("Stopping browser refresh manager")
        self._running = False
        
        if self._refresh_thread:
            self._refresh_thread.join(timeout=5)
    
    def _refresh_loop(self):
        """Main refresh loop"""
        while self._running:
            try:
                # Wait for refresh interval
                time.sleep(self.refresh_interval)
                
                if not self._running:
                    break
                
                # Perform refresh cycle
                self._perform_refresh_cycle()
                
            except Exception as e:
                self.logger.error(f"Error in refresh loop: {e}")
                time.sleep(30)  # Wait before retrying
    
    def _perform_refresh_cycle(self):
        """Perform a complete refresh cycle on all browsers"""
        self.logger.info("="*40)
        self.logger.info("BROWSER REFRESH CYCLE: Starting")
        self.logger.info(f"Time: {datetime.now()}")
        
        start_time = time.time()
        refreshed_count = 0
        failed_count = 0
        
        try:
            # Get browser pool stats if available
            if hasattr(self.browser_pool, 'get_stats'):
                stats = self.browser_pool.get_stats()
                self.logger.info(f"Pool stats before refresh: {stats}")
            
            # Check if pool has browsers to refresh
            if hasattr(self.browser_pool, 'browsers'):
                browsers = self.browser_pool.browsers
                self.logger.info(f"Found {len(browsers)} browsers to refresh")
                
                # Refresh each browser
                for browser_info in browsers:
                    browser_id = browser_info.get('id', 'unknown')
                    
                    # Check if browser needs refresh
                    if self._should_refresh_browser(browser_info):
                        if self._refresh_single_browser(browser_info):
                            refreshed_count += 1
                            self._last_refresh_times[browser_id] = datetime.now()
                        else:
                            failed_count += 1
                    else:
                        self.logger.debug(f"Browser {browser_id} doesn't need refresh yet")
            
            # Update statistics
            self.stats['total_refreshes'] += refreshed_count
            self.stats['successful_refreshes'] += refreshed_count
            self.stats['failed_refreshes'] += failed_count
            self.stats['last_refresh_cycle'] = datetime.now()
            
            elapsed = time.time() - start_time
            self.logger.info(f"BROWSER REFRESH CYCLE: Completed")
            self.logger.info(f"Refreshed: {refreshed_count}, Failed: {failed_count}, Time: {elapsed:.2f}s")
            self.logger.info("="*40)
            
        except Exception as e:
            self.logger.error(f"Error in refresh cycle: {e}")
    
    def _should_refresh_browser(self, browser_info: Dict[str, Any]) -> bool:
        """
        Determine if a browser should be refreshed
        
        Args:
            browser_info: Browser information dictionary
            
        Returns:
            bool: True if browser should be refreshed
        """
        browser_id = browser_info.get('id', 'unknown')
        
        # Check if browser is available (not in use)
        if not browser_info.get('available', True):
            self.logger.debug(f"Browser {browser_id} is in use, skipping refresh")
            return False
        
        # Check if critical operation is in progress (for browser pools)
        if hasattr(self.browser_pool, 'is_critical_operation_in_progress'):
            if self.browser_pool.is_critical_operation_in_progress():
                self.logger.debug(f"Critical operation in progress, skipping all browser refreshes")
                return False
        
        # Check if browser is healthy
        if not browser_info.get('healthy', True):
            self.logger.info(f"Browser {browser_id} is unhealthy, needs refresh")
            return True
        
        # Check last refresh time
        last_refresh = self._last_refresh_times.get(browser_id)
        if last_refresh:
            time_since_refresh = (datetime.now() - last_refresh).total_seconds()
            if time_since_refresh < self.refresh_interval:
                return False
        
        # Check browser age
        created_at = browser_info.get('created_at')
        if created_at and isinstance(created_at, datetime):
            age = (datetime.now() - created_at).total_seconds()
            if age > self.refresh_interval:
                self.logger.info(f"Browser {browser_id} is {age/60:.1f} minutes old, needs refresh")
                return True
        
        return True
    
    def _refresh_single_browser(self, browser_info: Dict[str, Any]) -> bool:
        """
        Refresh a single browser while maintaining state
        
        Args:
            browser_info: Browser information dictionary
            
        Returns:
            bool: True if successful
        """
        browser_id = browser_info.get('id', 'unknown')
        
        try:
            self.logger.info(f"Refreshing browser {browser_id}...")
            
            # Use stateful refresh for Playwright pages
            if 'page' in browser_info and browser_info['page']:
                from lvbot.automation.browser.stateful_browser_refresh import StatefulBrowserRefresh
                stateful_refresh = StatefulBrowserRefresh()
                
                # Check if this is an async page (for AsyncBrowserPool)
                page = browser_info['page']
                if hasattr(page, 'reload'):  # It's a real page object
                    # For sync Playwright, we need to run in a new event loop
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        success, message = loop.run_until_complete(
                            stateful_refresh.refresh_with_state(page)
                        )
                        if success:
                            self.logger.info(f"✓ Browser {browser_id}: {message}")
                        else:
                            self.logger.error(f"✗ Browser {browser_id}: {message}")
                        return success
                    finally:
                        loop.close()
            
            # Fallback to pool's refresh method if available
            if hasattr(self.browser_pool, 'refresh_browser'):
                success = self.browser_pool.refresh_browser(browser_id)
                if success:
                    self.logger.info(f"✓ Browser {browser_id} refreshed successfully")
                else:
                    self.logger.error(f"✗ Failed to refresh browser {browser_id}")
                return success
            else:
                # Fallback: close and recreate
                return self._recreate_browser(browser_info)
            
        except Exception as e:
            self.logger.error(f"Error refreshing browser {browser_id}: {e}")
            return False
    
    def _recreate_browser(self, browser_info: Dict[str, Any]) -> bool:
        """
        Recreate a browser by closing and creating a new one
        
        Args:
            browser_info: Browser information dictionary
            
        Returns:
            bool: True if successful
        """
        browser_id = browser_info.get('id', 'unknown')
        index = browser_info.get('index', 0)
        
        try:
            # Close existing browser resources
            if 'page' in browser_info and browser_info['page']:
                browser_info['page'].close()
            if 'context' in browser_info and browser_info['context']:
                browser_info['context'].close()
            
            # Call pool's create method if available
            if hasattr(self.browser_pool, '_create_browser'):
                return self.browser_pool._create_browser(index)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error recreating browser {browser_id}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get refresh manager statistics"""
        return {
            'running': self._running,
            'refresh_interval': self.refresh_interval,
            'total_refreshes': self.stats['total_refreshes'],
            'successful_refreshes': self.stats['successful_refreshes'],
            'failed_refreshes': self.stats['failed_refreshes'],
            'last_refresh_cycle': self.stats['last_refresh_cycle'],
            'success_rate': (
                self.stats['successful_refreshes'] / self.stats['total_refreshes']
                if self.stats['total_refreshes'] > 0 else 0
            )
        }
    
    def force_refresh_all(self):
        """Force immediate refresh of all browsers"""
        self.logger.info("Force refresh requested for all browsers")
        self._perform_refresh_cycle()