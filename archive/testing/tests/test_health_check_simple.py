#!/usr/bin/env python3
"""Simple test to verify health checker is working"""
from utils.tracking import t

import asyncio
import logging
from lvbot.utils.async_browser_pool import AsyncBrowserPool
from lvbot.utils.browser_health_checker import BrowserHealthChecker

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_health_check():
    """Test the browser health checker"""
    t('archive.testing.tests.test_health_check_simple.test_health_check')
    browser_pool = AsyncBrowserPool()
    
    try:
        # Start the browser pool
        print("Starting browser pool...")
        await browser_pool.start()
        print("Browser pool started successfully!")
        
        # Create health checker
        health_checker = BrowserHealthChecker(browser_pool)
        
        # Run health check
        print("\nRunning health check...")
        result = await health_checker.perform_pre_booking_health_check()
        
        print(f"\n✅ Health Check Results: {result.status.value.upper()}")
        print(f"   Message: {result.message}")
        
        # Get court health summary
        summary = health_checker.get_court_health_summary()
        print("\nCourt Health Summary:")
        for court, status in summary.items():
            print(f"   Court {court}: {status}")
        
        # Check if pool needs restart
        needs_restart = health_checker.requires_pool_restart()
        print(f"\nPool needs restart: {needs_restart}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await browser_pool.stop()

if __name__ == "__main__":
    asyncio.run(test_health_check())