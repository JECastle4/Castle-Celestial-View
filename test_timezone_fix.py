#!/usr/bin/env python
"""Test that API services return datetime strings with UTC 'Z' suffix"""

from api.services.dates import calculate_day_of_week
from api.services.sun import calculate_sun_position
from api.models import LocationModel, ObservationDateTime

def test_datetime_formats():
    """Verify all services return datetime with Z suffix"""
    
    # Test 1: Check dates service returns datetime with Z suffix
    result = calculate_day_of_week("2026-02-01", "12:00:00")
    print("Day of Week Result:")
    print(f"  input_datetime: {result['input_datetime']}")
    assert result['input_datetime'].endswith('Z'), "datetime should end with 'Z'"
    print("  ✓ Passes: ends with Z")

    # Test 2: Check sun position service returns datetime with Z suffix  
    location = LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0)
    obs_time = ObservationDateTime(date="2026-02-01", time="12:00:00")
    sun_result = calculate_sun_position(obs_time, location)
    print("\nSun Position Result:")
    print(f"  input_datetime: {sun_result['input_datetime']}")
    assert sun_result['input_datetime'].endswith('Z'), "datetime should end with 'Z'"
    print("  ✓ Passes: ends with Z")

    print("\n✓ All datetime formatting tests passed!")

if __name__ == "__main__":
    test_datetime_formats()
