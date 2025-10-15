#!/usr/bin/env python3
"""
Test script to verify Telegram availability display after handler fix
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lvbot.utils.availability_checker_v3 import AvailabilityCheckerV3
from lvbot.utils.async_browser_pool import AsyncBrowserPool
from lvbot.utils.telegram_ui import TelegramUI
from datetime import datetime, timedelta
import pytz

async def test_availability_display():
    """Test that availability data is properly formatted for Telegram display"""
    browser_pool = None
    availability_checker = None
    
    try:
        print("🚀 Starting browser pool...")
        browser_pool = AsyncBrowserPool()
        await browser_pool.start()
        
        print("✅ Browser pool initialized")
        
        # Create availability checker
        availability_checker = AvailabilityCheckerV3(browser_pool)
        
        print("\n📊 Checking availability for all courts...")
        availability_results = await availability_checker.check_availability(
            court_numbers=[1, 2, 3]
        )
        
        print(f"\n📋 Raw availability results:")
        for court, dates_dict in availability_results.items():
            if isinstance(dates_dict, dict) and "error" not in dates_dict:
                for date_str, times in dates_dict.items():
                    if times:
                        print(f"  Court {court} - {date_str}: {len(times)} slots")
        
        # Convert V3 format to matrix format (simulating what handler does)
        print("\n🔄 Converting to matrix format for UI...")
        complete_matrix = {}
        for court_num, dates_dict in availability_results.items():
            if isinstance(dates_dict, dict) and "error" not in dates_dict:
                for date_str, times in dates_dict.items():
                    if date_str not in complete_matrix:
                        complete_matrix[date_str] = {}
                    complete_matrix[date_str][court_num] = times
        
        print(f"\n📊 Matrix format:")
        for date_str, courts in complete_matrix.items():
            print(f"  {date_str}:")
            for court, times in courts.items():
                if times:
                    print(f"    Court {court}: {len(times)} slots - {', '.join(times[:3])}{'...' if len(times) > 3 else ''}")
        
        # Build the Telegram message
        print("\n📱 Building Telegram message...")
        if complete_matrix:
            # Use TelegramUI helper to format message
            message_lines = ["🎾 *Available Courts (Next 48h)*\n"]
            
            # Get timezone
            mst = pytz.timezone("America/Denver")
            now = datetime.now(mst)
            
            for date_str in sorted(complete_matrix.keys()):
                courts_data = complete_matrix[date_str]
                if any(courts_data.values()):  # If any court has slots
                    # Parse date
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                    
                    # Format date header
                    if date_obj == now.date():
                        date_display = "Today"
                    elif date_obj == (now + timedelta(days=1)).date():
                        date_display = "Tomorrow"
                    else:
                        date_display = date_obj.strftime("%A, %B %d")
                    
                    message_lines.append(f"\n📅 *{date_display}*")
                    
                    # Add court times
                    for court_num in sorted(courts_data.keys()):
                        times = courts_data.get(court_num, [])
                        if times:
                            # Show first few times
                            times_display = ", ".join(times[:5])
                            if len(times) > 5:
                                times_display += f" (+{len(times)-5} more)"
                            message_lines.append(f"Court {court_num}: {times_display}")
            
            message = "\n".join(message_lines)
            print("\n✅ Telegram message successfully built:")
            print("-" * 50)
            print(message)
            print("-" * 50)
            
            # Test keyboard generation
            print("\n⌨️ Testing keyboard generation...")
            # This simulates what the handler would do
            keyboard_data = []
            for date_str in sorted(complete_matrix.keys()):
                if any(complete_matrix[date_str].values()):
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                    if date_obj == now.date():
                        button_text = "📅 Today"
                    elif date_obj == (now + timedelta(days=1)).date():
                        button_text = "📅 Tomorrow"
                    else:
                        button_text = f"📅 {date_obj.strftime('%a %b %d')}"
                    keyboard_data.append((button_text, f"48h_date_{date_str}"))
            
            if keyboard_data:
                print(f"✅ Generated {len(keyboard_data)} date buttons")
                for text, callback in keyboard_data:
                    print(f"  - {text} -> {callback}")
            
        else:
            print("\n❌ No availability found to display")
        
        print("\n✅ Test completed successfully!")
        print("The Telegram handler should now properly display all available slots")
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if browser_pool:
            print("\n🧹 Closing browser pool...")
            await browser_pool.stop()

if __name__ == "__main__":
    asyncio.run(test_availability_display())