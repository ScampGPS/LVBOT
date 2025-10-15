#!/usr/bin/env python3
"""
Test the new AvailabilityCheckerV2 implementation
"""

import asyncio
import logging
from utils.async_browser_pool import AsyncBrowserPool
from utils.availability_checker_v2 import AvailabilityCheckerV2

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_availability_checker():
    """Test the new availability checker"""
    print("=" * 60)
    print("Testing AvailabilityCheckerV2")
    print("=" * 60)
    
    # Initialize browser pool
    browser_pool = AsyncBrowserPool()
    await browser_pool.start()
    
    print("\nBrowser pool initialized with 3 courts")
    
    # Create availability checker
    checker = AvailabilityCheckerV2(browser_pool)
    
    # Test single court
    print("\n" + "-" * 60)
    print("Testing single court (Court 3):")
    print("-" * 60)
    
    court3_times = await checker.check_single_court(3)
    print(f"\nCourt 3 availability:")
    for date_str, times in court3_times.items():
        print(f"  {date_str}: {times}")
        if "06:00" in times:
            print("  ✅ Found 6:00 AM slot!")
    
    # Test all courts
    print("\n" + "-" * 60)
    print("Testing all courts in parallel:")
    print("-" * 60)
    
    all_courts = await checker.check_all_courts()
    
    print("\nResults:")
    for court_num, dates in all_courts.items():
        print(f"\nCourt {court_num}:")
        if dates:
            for date_str, times in dates.items():
                print(f"  {date_str}: {len(times)} slots - {times[:3]}...")
                if court_num == 3 and "06:00" in times:
                    print("  ✅ Court 3 has 6:00 AM slot!")
        else:
            print("  ❌ No availability found")
    
    # Test time button finding
    print("\n" + "-" * 60)
    print("Testing time button finder for 06:00:")
    print("-" * 60)
    
    page = await browser_pool.get_page(3)
    if page:
        button = await checker.find_time_button(page, "06:00")
        if button:
            print("✅ Successfully found 06:00 button!")
            print("   Button is ready to click for booking")
        else:
            print("❌ Could not find 06:00 button")
    
    # Cleanup
    await browser_pool.stop()
    print("\n✅ Test completed")

if __name__ == "__main__":
    asyncio.run(test_availability_checker())