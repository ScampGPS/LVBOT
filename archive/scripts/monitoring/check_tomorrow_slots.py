#!/usr/bin/env python3
"""
Check available slots for tomorrow WITHOUT booking
This is safe to run - it only checks availability
"""
from utils.tracking import t
import pathlib
from pathlib import Path
import sys

ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


import asyncio
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

async def check_tomorrow_availability():
    """Check what slots are available tomorrow"""
    t('archive.scripts.monitoring.check_tomorrow_slots.check_tomorrow_availability')
    logger = logging.getLogger('SlotChecker')
    
    print("\n" + "="*80)
    print("CHECKING TOMORROW'S AVAILABLE SLOTS")
    print("="*80)
    print("This will ONLY check availability - NO BOOKINGS WILL BE MADE")
    print("="*80 + "\n")
    
    from lvbot.utils.async_browser_pool import AsyncBrowserPool
    from lvbot.utils.court_availability import CourtAvailability
    
    # Initialize browser pool
    browser_pool = AsyncBrowserPool()
    
    # Use shorter warm-up for just checking
    browser_pool.WARMUP_DELAY = 3.0  # Just 3 seconds for checking
    
    await browser_pool.start()
    
    # Check availability
    availability = CourtAvailability()
    
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow_str = tomorrow.strftime('%Y-%m-%d')
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    print(f"Today: {today_str}")
    print(f"Tomorrow: {tomorrow_str} ({tomorrow.strftime('%A')})")
    print("="*80 + "\n")
    
    all_slots = []
    
    for court_number in [1, 2, 3]:
        try:
            page = await browser_pool.get_page(court_number)
            if page and await availability.is_acuity_scheduling_page(page):
                times_by_day = await availability.extract_acuity_times_by_day(page)
                
                print(f"\nCOURT {court_number}:")
                print("-"*40)
                
                # Show today's slots (but mark as unavailable for booking)
                if today_str in times_by_day:
                    today_times = times_by_day[today_str]
                    print(f"Today ({today_str}): {len(today_times)} slots")
                    print("  ⚠️  SAME-DAY BOOKINGS NOT ALLOWED")
                    for time in today_times[:3]:
                        print(f"     - {time} (TODAY - NOT BOOKABLE)")
                    if len(today_times) > 3:
                        print(f"     ... and {len(today_times) - 3} more")
                
                # Show tomorrow's slots (available for booking)
                if tomorrow_str in times_by_day:
                    tomorrow_times = times_by_day[tomorrow_str]
                    print(f"Tomorrow ({tomorrow_str}): {len(tomorrow_times)} slots")
                    for time in tomorrow_times:
                        print(f"  ✅ {time}")
                        all_slots.append({
                            'court': court_number,
                            'time': time,
                            'date': tomorrow
                        })
                else:
                    print(f"Tomorrow ({tomorrow_str}): No slots available")
                    
        except Exception as e:
            print(f"\nCOURT {court_number}: Error - {e}")
    
    print("\n" + "="*80)
    print(f"TOTAL AVAILABLE SLOTS FOR TOMORROW: {len(all_slots)}")
    print("="*80)
    
    if all_slots:
        print("\nSample booking commands for tomorrow:")
        for i, slot in enumerate(all_slots[:3]):
            print(f"{i+1}. Court {slot['court']} at {slot['time']} on {slot['date'].strftime('%Y-%m-%d')}")
    
    # Cleanup
    if hasattr(browser_pool, 'close'):
        await browser_pool.close()
    
    return all_slots

if __name__ == "__main__":
    asyncio.run(check_tomorrow_availability())
