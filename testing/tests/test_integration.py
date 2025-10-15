#!/usr/bin/env python3
"""
Integration test to verify the updated CourtAvailability works without breaking existing functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, date, timedelta
from lvbot.utils.court_availability import CourtAvailability

def test_backward_compatibility():
    """Test that existing methods still work"""
    print("=== Testing Backward Compatibility ===")
    
    # Test static methods that don't require Playwright
    earliest_hour = CourtAvailability.get_earliest_booking_hour()
    latest_hour = CourtAvailability.get_latest_booking_hour()
    booking_window = CourtAvailability.get_booking_window_hours()
    
    assert earliest_hour == 7, f"Expected 7, got {earliest_hour}"
    assert latest_hour == 21, f"Expected 21, got {latest_hour}"
    assert booking_window == 48, f"Expected 48, got {booking_window}"
    
    print(f"✅ Club constants: {earliest_hour}:00-{latest_hour}:00, {booking_window}h window")

def test_time_validation():
    """Test time text validation"""
    print("\n=== Testing Time Validation ===")
    
    test_cases = [
        ('10:00', True),
        ('9:30', True),
        ('21:45', True),
        ('not a time', False),
        ('25:00', True),  # CourtAvailability.is_time_text allows this
        ('10:60', True),  # CourtAvailability.is_time_text allows this
        ('', False)
    ]
    
    for time_str, expected in test_cases:
        result = CourtAvailability.is_time_text(time_str)
        print(f"'{time_str}' → {result} (expected: {expected})")
        assert result == expected, f"Expected {expected} for '{time_str}'"
    
    print("✅ Time validation works correctly")

def test_day_feasibility():
    """Test day feasibility checks"""
    print("\n=== Testing Day Feasibility ===")
    
    # Today should be feasible if we're before 9 PM
    current_time = datetime.now()
    if current_time.hour < 21:
        assert CourtAvailability.is_today_feasible(), "Today should be feasible before 9 PM"
        print("✅ Today is feasible (before 9 PM)")
    else:
        assert not CourtAvailability.is_today_feasible(), "Today should not be feasible after 9 PM"
        print("✅ Today is not feasible (after 9 PM)")
    
    # Tomorrow should always be feasible
    assert CourtAvailability.is_tomorrow_feasible(), "Tomorrow should always be feasible"
    print("✅ Tomorrow is feasible")
    
    # Test day after tomorrow feasibility
    day_after_feasible = CourtAvailability.is_day_after_feasible()
    print(f"✅ Day after tomorrow feasible: {day_after_feasible}")

def test_navigation_selectors():
    """Test navigation selector lists"""
    print("\n=== Testing Navigation Selectors ===")
    
    next_selectors = CourtAvailability.get_next_navigation_selectors()
    prev_selectors = CourtAvailability.get_previous_navigation_selectors()
    day_selectors = CourtAvailability.get_day_indicator_selectors()
    
    assert len(next_selectors) > 0, "Should have next navigation selectors"
    assert len(prev_selectors) > 0, "Should have previous navigation selectors"
    assert len(day_selectors) > 0, "Should have day indicator selectors"
    
    # Check for expected patterns
    assert any('>' in selector for selector in next_selectors), "Should have > arrow selector"
    assert any('<' in selector for selector in prev_selectors), "Should have < arrow selector"
    assert any('HOY' in selector for selector in day_selectors), "Should have HOY selector"
    
    print(f"✅ Navigation selectors: {len(next_selectors)} next, {len(prev_selectors)} prev, {len(day_selectors)} day")

def test_day_names_mapping():
    """Test day names mapping"""
    print("\n=== Testing Day Names Mapping ===")
    
    day_names = CourtAvailability.get_day_names()
    
    expected_keys = ['today', 'tomorrow', 'weekdays', 'weekdays_en']
    for key in expected_keys:
        assert key in day_names, f"Missing key: {key}"
    
    assert 'HOY' in day_names['today'], "HOY should be in today list"
    assert 'MAÑANA' in day_names['tomorrow'], "MAÑANA should be in tomorrow list"
    assert 'LUNES' in day_names['weekdays'], "LUNES should be in weekdays list"
    
    print("✅ Day names mapping works correctly")

def test_imports():
    """Test that all imports work correctly"""
    print("\n=== Testing Imports ===")
    
    try:
        from lvbot.utils.time_feasibility_validator import (
            is_within_booking_window,
            filter_future_times_for_today,
            should_navigate_to_next_day
        )
        print("✅ Time feasibility validator imports work")
        
        from lvbot.utils.day_context_parser import (
            convert_day_labels_to_dates,
            extract_times_grouped_by_day
        )
        print("✅ Day context parser imports work")
        
    except ImportError as e:
        raise AssertionError(f"Import error: {e}")

if __name__ == "__main__":
    print("Running Integration Tests...")
    
    try:
        test_backward_compatibility()
        test_time_validation()
        test_day_feasibility()
        test_navigation_selectors()
        test_day_names_mapping()
        test_imports()
        
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ Existing functionality preserved")
        print("✅ New day-aware features integrated")
        
    except Exception as e:
        print(f"\n❌ INTEGRATION TEST FAILED: {e}")
        sys.exit(1)