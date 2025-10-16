#!/usr/bin/env python3
"""
Test script for AvailabilityCheckerV3
"""
from utils.tracking import t

import asyncio
import logging
from lvbot.utils.async_browser_pool import AsyncBrowserPool
from lvbot.utils.availability_checker_v3 import AvailabilityCheckerV3

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_availability():
    """Test the availability checker with all features"""
    t('archive.testing.tests.test_availability_v3.test_availability')
    browser_pool = AsyncBrowserPool()
    
    try:
        print("Starting browser pool...")
        await browser_pool.start()
        print("✅ Browser pool started")
        
        # Create availability checker
        checker = AvailabilityCheckerV3(browser_pool)
        
        # Test 1: Check all courts using backward compatibility method
        print("\n=== Test 1: check_all_courts_parallel() ===")
        results = await checker.check_all_courts_parallel()
        for court, times in results.items():
            print(f"Court {court}: {len(times)} slots - {times[:3]}...")
            
        # Test 2: Check specific courts with date info
        print("\n=== Test 2: check_availability() with dates ===")
        detailed_results = await checker.check_availability([1, 3])
        for court, dates in detailed_results.items():
            print(f"\nCourt {court}:")
            if isinstance(dates, dict) and "error" not in dates:
                for date, times in dates.items():
                    print(f"  {date}: {times}")
                    
        # Test 3: Find next available slot
        print("\n=== Test 3: get_next_available_slot() ===")
        next_slot = await checker.get_next_available_slot()
        if next_slot:
            court, date, time = next_slot
            print(f"Next available: Court {court} on {date} at {time}")
        else:
            print("No available slots found")
            
        # Test 4: Format availability message
        print("\n=== Test 4: format_availability_message() ===")
        message = checker.format_availability_message(detailed_results)
        print(message)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nClosing browser pool...")
        await browser_pool.stop()
        print("✅ Test completed")

if __name__ == "__main__":
    asyncio.run(test_availability())