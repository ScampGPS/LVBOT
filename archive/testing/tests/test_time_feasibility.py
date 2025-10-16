#!/usr/bin/env python3
"""
Test the time feasibility validator functions
"""
from utils.tracking import t

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from lvbot.utils.time_feasibility_validator import (
    is_within_booking_window,
    filter_future_times_for_today,
    get_earliest_booking_time_for_day,
    should_navigate_to_next_day,
    get_day_offset_from_label,
    is_day_label_feasible
)

def test_time_parsing_and_filtering():
    """Test filtering future times for today"""
    t('archive.testing.tests.test_time_feasibility.test_time_parsing_and_filtering')
    print("=== Testing Time Filtering ===")
    
    # Test scenario: Current time is 2:00 PM
    test_time = datetime(2025, 7, 21, 14, 0)  # 2:00 PM
    
    available_times = ['11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00']
    
    future_times = filter_future_times_for_today(available_times, test_time)
    
    print(f"Current time: {test_time.strftime('%H:%M')}")
    print(f"Available times: {available_times}")
    print(f"Future times: {future_times}")
    
    expected = ['15:00', '16:00', '17:00', '18:00']
    assert future_times == expected, f"Expected {expected}, got {future_times}"
    print("✅ Time filtering works correctly")

def test_booking_window():
    """Test 48h booking window validation"""
    t('archive.testing.tests.test_time_feasibility.test_booking_window')
    print("\n=== Testing Booking Window ===")
    
    current_time = datetime(2025, 7, 21, 14, 0)  # Monday 2:00 PM
    
    # Test times within and outside 48h window
    test_cases = [
        (datetime(2025, 7, 21, 15, 0), True),   # 1h later - within window
        (datetime(2025, 7, 22, 7, 0), True),    # Tomorrow 7AM - within window
        (datetime(2025, 7, 23, 7, 0), True),    # Day after tomorrow 7AM - within window (41h)
        (datetime(2025, 7, 24, 7, 0), False),   # 3 days later - outside window (65h)
    ]
    
    for target_time, expected in test_cases:
        result = is_within_booking_window(target_time, current_time)
        hours_diff = (target_time - current_time).total_seconds() / 3600
        print(f"Target: {target_time} ({hours_diff:.1f}h from now) → Within window: {result}")
        assert result == expected, f"Expected {expected} for {target_time}"
    
    print("✅ Booking window validation works correctly")

def test_day_labels():
    """Test Spanish day label parsing"""
    t('archive.testing.tests.test_time_feasibility.test_day_labels')
    print("\n=== Testing Day Labels ===")
    
    test_cases = [
        ('HOY', 0),
        ('MAÑANA', 1), 
        ('ESTA SEMANA', 2)
    ]
    
    for day_label, expected_offset in test_cases:
        offset = get_day_offset_from_label(day_label)
        print(f"Day label '{day_label}' → offset: {offset}")
        assert offset == expected_offset, f"Expected {expected_offset}, got {offset}"
    
    print("✅ Day label parsing works correctly")

def test_navigation_logic():
    """Test navigation decision logic"""
    t('archive.testing.tests.test_time_feasibility.test_navigation_logic')
    print("\n=== Testing Navigation Logic ===")
    
    # Monday 2:00 PM - well within 48h window
    current_time = datetime(2025, 7, 21, 14, 0)
    
    test_cases = [
        (['HOY'], True),  # Only today visible, should navigate to see tomorrow
        (['HOY', 'MAÑANA'], True),  # Today+tomorrow visible, should navigate to see day after
        (['HOY', 'MAÑANA', 'ESTA SEMANA'], False),  # All days visible, no navigation needed
    ]
    
    for visible_days, expected in test_cases:
        result = should_navigate_to_next_day(visible_days, current_time)
        print(f"Visible days: {visible_days} → Should navigate: {result}")
        assert result == expected, f"Expected {expected} for {visible_days}"
    
    print("✅ Navigation logic works correctly")

def test_edge_cases():
    """Test edge cases near 48h boundary"""
    t('archive.testing.tests.test_time_feasibility.test_edge_cases')
    print("\n=== Testing Edge Cases ===")
    
    # Wednesday 8:00 PM - close to 48h boundary
    current_time = datetime(2025, 7, 23, 20, 0)  # Wednesday 8PM
    
    # Friday 7:00 AM = Wednesday 8PM + 35 hours = within 48h window
    friday_7am = datetime(2025, 7, 25, 7, 0)  
    result = is_within_booking_window(friday_7am, current_time)
    hours_diff = (friday_7am - current_time).total_seconds() / 3600
    print(f"Friday 7AM from Wednesday 8PM: {hours_diff:.1f}h → Within window: {result}")
    assert result == True, "Friday should be within 48h window (35h away)"
    
    # Saturday 7:00 AM = Wednesday 8PM + 59 hours = outside 48h window
    saturday_7am = datetime(2025, 7, 26, 7, 0)
    result = is_within_booking_window(saturday_7am, current_time)
    hours_diff = (saturday_7am - current_time).total_seconds() / 3600
    print(f"Saturday 7AM from Wednesday 8PM: {hours_diff:.1f}h → Within window: {result}")
    assert result == False, "Saturday should be outside 48h window (59h away)"
    
    print("✅ Edge cases work correctly")

if __name__ == "__main__":
    print("Testing Time Feasibility Validator...")
    
    try:
        test_time_parsing_and_filtering()
        test_booking_window()
        test_day_labels()
        test_navigation_logic()
        test_edge_cases()
        
        print("\n🎉 ALL TESTS PASSED!")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)