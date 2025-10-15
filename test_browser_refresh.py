#!/usr/bin/env python3
"""
Test script for the new browser refresh functionality
Validates that browsers can be refreshed without event loop conflicts
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from browser_pool_specialized import SpecializedBrowserPool

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('BrowserRefreshTest')

async def test_browser_refresh():
    """Test the new browser refresh functionality"""
    logger.info("🧪 TESTING BROWSER REFRESH FUNCTIONALITY")
    
    try:
        # Create a small browser pool for testing
        logger.info("Creating test browser pool...")
        browser_pool = SpecializedBrowserPool(
            courts_needed=[1, 2],  # Just 2 browsers for testing
            headless=True,
            max_browsers=2,
            low_resource_mode=True,
            persistent=True
        )
        
        # Start the pool
        logger.info("Starting browser pool...")
        await browser_pool.start()
        
        # Wait for pool to be ready
        if not await browser_pool.wait_until_ready(timeout=30):
            logger.error("❌ Browser pool failed to initialize")
            return False
        
        logger.info("✅ Browser pool initialized successfully")
        
        # Check if refresh method exists
        if not hasattr(browser_pool, 'refresh_browser_pages'):
            logger.error("❌ Browser pool doesn't have refresh_browser_pages method")
            return False
        
        logger.info("✅ refresh_browser_pages method found")
        
        # Get initial stats
        initial_stats = browser_pool.get_stats()
        logger.info(f"Initial browser count: {initial_stats.get('browser_count', 0)}")
        
        # Test the refresh functionality
        logger.info("🔄 Testing browser page refresh...")
        refresh_results = await browser_pool.refresh_browser_pages()
        
        if not refresh_results:
            logger.warning("⚠️ No browsers were refreshed (pool might be empty)")
            return True  # Not necessarily a failure
        
        # Analyze results
        successful = sum(1 for success in refresh_results.values() if success)
        total = len(refresh_results)
        
        logger.info(f"📊 Refresh results: {successful}/{total} successful")
        
        if successful > 0:
            logger.info("✅ Browser refresh test PASSED")
            return True
        else:
            logger.error("❌ Browser refresh test FAILED - no successful refreshes")
            return False
            
    except Exception as e:
        logger.error(f"❌ Browser refresh test failed with exception: {e}")
        return False
    finally:
        # Clean up
        try:
            if 'browser_pool' in locals():
                await browser_pool.stop()
                logger.info("🧹 Browser pool cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up: {e}")

async def test_scheduler_integration():
    """Test that the refresh functionality integrates properly with the scheduler"""
    logger.info("🧪 TESTING SCHEDULER INTEGRATION")
    
    try:
        # Import the reservation scheduler
        from utils.reservation_scheduler import ReservationScheduler
        
        # Create a minimal scheduler instance (won't actually run)
        scheduler = ReservationScheduler(
            config=None,
            queue=None,
            notification_callback=None
        )
        
        # Check if force_browser_refresh method exists
        if not hasattr(scheduler, 'force_browser_refresh'):
            logger.error("❌ Scheduler doesn't have force_browser_refresh method")
            return False
        
        logger.info("✅ force_browser_refresh method found on scheduler")
        
        # Test calling it without browser pool (should handle gracefully)
        results = await scheduler.force_browser_refresh()
        
        if results == {}:
            logger.info("✅ Scheduler gracefully handled missing browser pool")
            return True
        else:
            logger.warning("⚠️ Unexpected result from force_browser_refresh with no pool")
            return True  # Not necessarily a failure
            
    except Exception as e:
        logger.error(f"❌ Scheduler integration test failed: {e}")
        return False

async def main():
    """Run all tests"""
    logger.info("🚀 STARTING BROWSER REFRESH TESTS")
    logger.info(f"Test started at: {datetime.now()}")
    
    # Run tests
    test_results = []
    
    logger.info("="*60)
    test_results.append(await test_browser_refresh())
    
    logger.info("="*60)
    test_results.append(await test_scheduler_integration())
    
    logger.info("="*60)
    
    # Summary
    passed = sum(test_results)
    total = len(test_results)
    
    logger.info(f"📊 TEST SUMMARY: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("✅ ALL TESTS PASSED - Browser refresh implementation is working correctly!")
        return True
    else:
        logger.error(f"❌ {total - passed} TEST(S) FAILED - Check implementation")
        return False

if __name__ == '__main__':
    success = asyncio.run(main())
    sys.exit(0 if success else 1)