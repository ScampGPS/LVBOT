"""
Browser lifecycle management utilities
Centralizes browser pool initialization and shutdown
"""
from tracking import t

import logging
from typing import Optional


class BrowserLifecycle:
    """Manages browser pool lifecycle operations"""
    
    @staticmethod
    async def start_pool(browser_pool, logger: Optional[logging.Logger] = None) -> bool:
        """
        Initialize browser pool with proper error handling
        
        Args:
            browser_pool: The browser pool instance to start
            logger: Optional logger for status messages
            
        Returns:
            bool: True if successful, False otherwise
        """
        t('automation.browser.browser_lifecycle.BrowserLifecycle.start_pool')
        if not logger:
            logger = logging.getLogger('BrowserLifecycle')
            
        try:
            logger.info("Initializing browser pool...")
            await browser_pool.start()
            logger.info("✅ Browser pool started successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to start browser pool: {e}")
            raise
    
    @staticmethod
    async def stop_pool(browser_pool, logger: Optional[logging.Logger] = None) -> bool:
        """
        Shutdown browser pool with proper error handling
        
        Args:
            browser_pool: The browser pool instance to stop
            logger: Optional logger for status messages
            
        Returns:
            bool: True if successful, False otherwise
        """
        t('automation.browser.browser_lifecycle.BrowserLifecycle.stop_pool')
        if not logger:
            logger = logging.getLogger('BrowserLifecycle')
            
        try:
            logger.info("Stopping browser pool...")
            await browser_pool.stop()
            logger.info("✅ Browser pool stopped successfully")
            return True
        except Exception as e:
            logger.error(f"Error stopping browser pool: {e}")
            return False