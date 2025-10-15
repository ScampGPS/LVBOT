"""
Test the time grouping fix to ensure times are properly associated with their days
"""

import asyncio
import sys
import logging
from datetime import datetime
sys.path.append('/mnt/c/Documents/code/python/lvbot')

# Set up detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_time_grouping():
    """Test that times are properly grouped by day using time-order logic"""
    from lvbot.utils.async_browser_pool import AsyncBrowserPool
    from lvbot.utils.availability_checker_v3 import AvailabilityCheckerV3
    
    browser_pool = None
    
    try:
        print("=== TESTING TIME GROUPING FIX ===")
        
        # Initialize browser pool
        print("\n1. Initializing browser pool...")
        browser_pool = AsyncBrowserPool()
        await browser_pool.start()
        print("✅ Browser pool initialized")
        
        # Create availability checker
        print("\n2. Creating V3 availability checker...")
        checker = AvailabilityCheckerV3(browser_pool)
        print("✅ Checker created with AcuityTimeParser")
        
        # Check availability
        print("\n3. Checking availability for all courts...")
        results = await checker.check_availability()
        
        print("\n4. Results by court:")
        for court_num in sorted(results.keys()):
            court_data = results[court_num]
            print(f"\n🎾 Court {court_num}:")
            
            if isinstance(court_data, dict) and "error" in court_data:
                print(f"   ❌ Error: {court_data['error']}")
                continue
                
            # Show times grouped by date
            for date_str in sorted(court_data.keys()):
                times = court_data[date_str]
                print(f"   📅 {date_str}: {len(times)} slots")
                
                # Check if times are in proper order
                if times:
                    # Convert to hours for checking order
                    hours = []
                    for time_str in times:
                        try:
                            hour = int(time_str.split(':')[0])
                            hours.append(hour)
                        except:
                            pass
                    
                    # Check if times are sequential (no backward jumps within a day)
                    is_ordered = all(hours[i] <= hours[i+1] for i in range(len(hours)-1))
                    order_status = "✅ Properly ordered" if is_ordered else "❌ Time order issue!"
                    
                    print(f"      Times: {times}")
                    print(f"      Order: {order_status}")
        
        print("\n5. Summary:")
        # Check if we have the issue where weekday hours appear on weekend
        saturday = "2025-08-02"
        if any(saturday in results.get(court, {}) for court in results):
            print(f"\n🔍 Checking Saturday ({saturday}) for weekday hours...")
            for court_num, court_data in results.items():
                if isinstance(court_data, dict) and saturday in court_data:
                    saturday_times = court_data[saturday]
                    
                    # Check for business hours (08:00-15:00)
                    business_hours = []
                    for time in saturday_times:
                        try:
                            hour = int(time.split(':')[0])
                            if 8 <= hour <= 15:
                                business_hours.append(time)
                        except:
                            pass
                    
                    if business_hours:
                        print(f"   ⚠️ Court {court_num} has business hours on Saturday: {business_hours}")
                    else:
                        print(f"   ✅ Court {court_num} has appropriate weekend hours")
        
        print("\n✅ Test complete!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if browser_pool and hasattr(browser_pool, 'browser') and browser_pool.browser:
            print("\nClosing browser pool...")
            await browser_pool.browser.close()

if __name__ == "__main__":
    asyncio.run(test_time_grouping())