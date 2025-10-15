#!/usr/bin/env python3
"""
Test the day context parser functions
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, timedelta
from utils.day_context_parser import (
    convert_day_labels_to_dates,
    # Note: DOM-based functions require Playwright and can't be unit tested easily
    # We'll test the pure functions here and save DOM testing for integration tests
)

def test_day_label_to_date_conversion():
    """Test converting Spanish day labels to actual dates"""
    print("=== Testing Day Label to Date Conversion ===")
    
    # Test with a known reference date: Monday July 21, 2025
    reference_date = date(2025, 7, 21)
    
    # Test data with Spanish day labels
    times_by_day = {
        'HOY': ['11:00', '12:00', '13:00'],
        'MAÑANA': ['08:00', '09:00', '10:00', '11:00', '12:00', '13:00'],
        'ESTA SEMANA': ['08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '19:15']
    }
    
    result = convert_day_labels_to_dates(times_by_day, reference_date)
    
    print(f"Reference date: {reference_date}")
    print(f"Input: {times_by_day}")
    print(f"Result: {result}")
    
    # Expected conversions
    expected = {
        '2025-07-21': ['11:00', '12:00', '13:00'],           # HOY = Monday
        '2025-07-22': ['08:00', '09:00', '10:00', '11:00', '12:00', '13:00'],  # MAÑANA = Tuesday 
        '2025-07-23': ['08:00', '09:00', '10:00', '11:00', '12:00', '13:00', '19:15']  # ESTA SEMANA = Wednesday
    }
    
    assert result == expected, f"Expected {expected}, got {result}"
    print("✅ Day label to date conversion works correctly")

def test_unknown_day_labels():
    """Test handling of unknown day labels"""
    print("\n=== Testing Unknown Day Labels ===")
    
    reference_date = date(2025, 7, 21)
    
    times_by_day = {
        'HOY': ['11:00', '12:00'],
        'UNKNOWN': ['14:00', '15:00'],
        'WEIRD_LABEL': ['16:00']
    }
    
    result = convert_day_labels_to_dates(times_by_day, reference_date)
    
    expected = {
        '2025-07-21': ['11:00', '12:00'],  # HOY converted
        'UNKNOWN': ['14:00', '15:00'],     # Unknown label kept as-is
        'WEIRD_LABEL': ['16:00']           # Weird label kept as-is
    }
    
    assert result == expected, f"Expected {expected}, got {result}"
    print("✅ Unknown day labels handled correctly")

def test_empty_input():
    """Test handling of empty input"""
    print("\n=== Testing Empty Input ===")
    
    result = convert_day_labels_to_dates({})
    expected = {}
    
    assert result == expected, f"Expected {expected}, got {result}"
    print("✅ Empty input handled correctly")

def test_default_reference_date():
    """Test default reference date (today)"""
    print("\n=== Testing Default Reference Date ===")
    
    times_by_day = {'HOY': ['10:00']}
    result = convert_day_labels_to_dates(times_by_day)
    
    # Should use today's date
    today = date.today()
    expected_key = today.strftime('%Y-%m-%d')
    
    assert expected_key in result, f"Expected key {expected_key} in result {result}"
    assert result[expected_key] == ['10:00'], f"Expected ['10:00'], got {result[expected_key]}"
    print(f"✅ Default reference date works correctly (using {expected_key})")

def test_weekend_edge_case():
    """Test day conversion over weekend"""
    print("\n=== Testing Weekend Edge Case ===")
    
    # Friday July 25, 2025
    reference_date = date(2025, 7, 25)
    
    times_by_day = {
        'HOY': ['10:00'],        # Friday
        'MAÑANA': ['11:00'],     # Saturday  
        'ESTA SEMANA': ['12:00'] # Sunday
    }
    
    result = convert_day_labels_to_dates(times_by_day, reference_date)
    
    expected = {
        '2025-07-25': ['10:00'],  # Friday
        '2025-07-26': ['11:00'],  # Saturday
        '2025-07-27': ['12:00']   # Sunday
    }
    
    assert result == expected, f"Expected {expected}, got {result}"
    print("✅ Weekend edge case works correctly")

if __name__ == "__main__":
    print("Testing Day Context Parser...")
    
    try:
        test_day_label_to_date_conversion()
        test_unknown_day_labels()
        test_empty_input()
        test_default_reference_date()
        test_weekend_edge_case()
        
        print("\n🎉 ALL DAY CONTEXT PARSER TESTS PASSED!")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)