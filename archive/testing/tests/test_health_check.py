#!/usr/bin/env python3
"""Test script to verify health checker fix"""
from utils.tracking import t

import asyncio
import logging
from lvbot.utils.async_browser_pool import AsyncBrowserPool
from lvbot.utils.browser_health_checker import BrowserHealthChecker

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_health_check():
    """Test the browser health checker"""
    t('archive.testing.tests.test_health_check.test_health_check')
    print("Starting browser pool...")
    browser_pool = AsyncBrowserPool()
    
    try:
        # Start the browser pool
        await browser_pool.start()
        print("Browser pool started successfully!")
        
        # Create health checker
        health_checker = BrowserHealthChecker(browser_pool)
        
        # Run comprehensive health check
        print("\nRunning comprehensive health check...")
        result = await health_checker.perform_pre_booking_health_check()
        
        print("\nHealth Check Results:")
        print(f"Overall Status: {result.status.value}")
        print(f"Message: {result.message}")
        print(f"Timestamp: {result.timestamp}")
        
        if result.court_statuses:
            print("\nCourt Details:")
            for court_status in result.court_statuses:
                print(f"\nCourt {court_status.court_number}:")
                print(f"  Status: {court_status.status.value}")
                print(f"  Page exists: {court_status.page_exists}")
                print(f"  Page responsive: {court_status.page_responsive}")
                print(f"  On booking site: {court_status.on_booking_site}")
                print(f"  Has booking elements: {court_status.has_booking_elements}")
                if court_status.details:
                    print(f"  Details: {court_status.details}")
        
        # Test browser responsiveness directly
        print("\n\nTesting browser responsiveness for each court...")
        for court_num in [1, 2, 3]:
            page = browser_pool.get_page(court_num)
            if page:
                print(f"\nTesting Court {court_num}...")
                responsiveness = await health_checker.test_browser_responsiveness(page, court_num)
                print(f"  URL accessible: {responsiveness.get('url_accessible', False)}")
                print(f"  JavaScript works: {responsiveness.get('javascript_works', False)}")
                print(f"  Network OK: {responsiveness.get('network_ok', False)}")
                print(f"  DOM queryable: {responsiveness.get('dom_queryable', False)}")
                
    except Exception as e:
        print(f"\nError during health check: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        print("\nStopping browser pool...")
        await browser_pool.stop()
        print("Browser pool stopped.")

if __name__ == "__main__":
    asyncio.run(test_health_check())