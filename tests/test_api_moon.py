"""Tests for the moon position calculation service."""

import pytest
from pydantic import ValidationError
from api.services.moon import calculate_moon_position
from api.models import ObservationDateTime, LocationModel


def test_moon_position_basic():
    """Test basic moon position calculation."""
    result = calculate_moon_position(
        ObservationDateTime(date="2025-01-01", time="00:00:00"),
        LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
    )

    assert "altitude" in result
    assert "azimuth" in result
    assert "is_visible" in result
    assert "julian_date" in result
    assert "location" in result
    assert "input_datetime" in result

    assert isinstance(result["altitude"], float)
    assert isinstance(result["azimuth"], float)
    assert isinstance(result["is_visible"], bool)
    assert isinstance(result["julian_date"], float)

    # Check value ranges
    assert -90 <= result["altitude"] <= 90
    assert 0 <= result["azimuth"] <= 360


def test_moon_position_new_york():
    """Test moon position for New York City."""
    result = calculate_moon_position(
        ObservationDateTime(date="2025-01-15", time="20:00:00"),
        LocationModel(latitude=40.7128, longitude=-74.0060, elevation=10.0)
    )

    assert "altitude" in result
    assert "azimuth" in result
    assert isinstance(result["is_visible"], bool)


def test_moon_position_sydney():
    """Test moon position for Sydney, Australia (southern hemisphere)."""
    result = calculate_moon_position(
        ObservationDateTime(date="2025-01-15", time="12:00:00"),
        LocationModel(latitude=-33.8688, longitude=151.2093, elevation=0.0)
    )

    assert "altitude" in result
    assert "azimuth" in result
    assert isinstance(result["is_visible"], bool)


def test_moon_position_north_pole():
    """Test moon position at North Pole."""
    result = calculate_moon_position(
        ObservationDateTime(date="2025-06-21", time="12:00:00"),
        LocationModel(latitude=90.0, longitude=0.0, elevation=0.0)
    )

    assert "altitude" in result
    assert "azimuth" in result
    assert isinstance(result["is_visible"], bool)


def test_moon_position_south_pole():
    """Test moon position at South Pole."""
    result = calculate_moon_position(
        ObservationDateTime(date="2025-12-21", time="12:00:00"),
        LocationModel(latitude=-90.0, longitude=0.0, elevation=0.0)
    )

    assert "altitude" in result
    assert "azimuth" in result
    assert isinstance(result["is_visible"], bool)


def test_moon_visibility_threshold():
    """Test that visibility is correctly determined by altitude > 0."""
    # This is a spot check - moon visibility varies by date/location
    result = calculate_moon_position(
        ObservationDateTime(date="2025-01-15", time="12:00:00"),
        LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
    )

    if result["altitude"] > 0:
        assert result["is_visible"] is True
    else:
        assert result["is_visible"] is False


def test_moon_visibility_changes_over_time():
    """Test that moon visibility explicitly changes between day and night."""
    # Check moon at multiple times throughout the day to find visibility flip
    # The moon rises and sets approximately once per day, so we check several times
    times = ["00:00:00", "06:00:00", "12:00:00", "18:00:00"]
    results = []
    
    for time in times:
        result = calculate_moon_position(
            ObservationDateTime(date="2025-01-15", time=time),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
        )
        results.append(result)
        
        # Verify visibility matches altitude
        assert result["is_visible"] == (result["altitude"] > 0), \
            f"At {time}, visibility {result['is_visible']} doesn't match altitude {result['altitude']}"
    
    # Check that visibility changes at least once during the day
    visibility_states = [r["is_visible"] for r in results]
    
    # There should be both True and False in the visibility states
    # (moon should rise and set during a 24-hour period)
    assert True in visibility_states and False in visibility_states, \
        f"Moon visibility should change throughout the day. Visibility states: {visibility_states}"


def test_moon_position_with_elevation():
    """Test moon position with non-zero elevation."""
    result_sea_level = calculate_moon_position(
        ObservationDateTime(date="2025-01-15", time="12:00:00"),
        LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
    )

    result_elevated = calculate_moon_position(
        ObservationDateTime(date="2025-01-15", time="12:00:00"),
        LocationModel(latitude=40.7128, longitude=-74.0060, elevation=1000.0)
    )

    # Positions should be slightly different due to elevation
    assert result_sea_level["altitude"] != result_elevated["altitude"]
    assert result_sea_level["location"]["elevation"] == 0.0
    assert result_elevated["location"]["elevation"] == 1000.0


def test_moon_position_different_times():
    """Test that moon position changes over time."""
    result1 = calculate_moon_position(
        ObservationDateTime(date="2025-01-15", time="00:00:00"),
        LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
    )

    result2 = calculate_moon_position(
        ObservationDateTime(date="2025-01-15", time="12:00:00"),
        LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
    )

    # Moon should move significantly in 12 hours
    assert result1["altitude"] != result2["altitude"]
    assert result1["azimuth"] != result2["azimuth"]


def test_moon_position_different_dates():
    """Test that moon position changes over days."""
    result1 = calculate_moon_position(
        ObservationDateTime(date="2025-01-01", time="12:00:00"),
        LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
    )

    result2 = calculate_moon_position(
        ObservationDateTime(date="2025-01-15", time="12:00:00"),
        LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
    )

    # Moon position should be different on different dates
    assert result1["altitude"] != result2["altitude"]
    assert result1["azimuth"] != result2["azimuth"]


def test_moon_julian_date_calculation():
    """Test that Julian Date is calculated correctly."""
    result = calculate_moon_position(
        ObservationDateTime(date="2025-01-01", time="00:00:00"),
        LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
    )

    # JD for 2025-01-01 00:00:00 UTC should be around 2460676.5
    assert 2460676 < result["julian_date"] < 2460677


def test_moon_input_datetime_format():
    """Test that input_datetime is formatted correctly."""
    result = calculate_moon_position(
        ObservationDateTime(date="2025-01-15", time="14:30:45"),
        LocationModel(latitude=40.7128, longitude=-74.0060, elevation=10.0)
    )

    assert result["input_datetime"] == "2025-01-15T14:30:45Z"


def test_moon_location_data():
    """Test that location data is correctly stored in response."""
    lat = 51.5074
    lon = -0.1278
    elev = 11.0

    result = calculate_moon_position(
        ObservationDateTime(date="2025-01-15", time="12:00:00"),
        LocationModel(latitude=lat, longitude=lon, elevation=elev)
    )

    assert result["location"]["latitude"] == lat
    assert result["location"]["longitude"] == lon
    assert result["location"]["elevation"] == elev


def test_moon_negative_elevation():
    """Test moon position with negative elevation (below sea level)."""
    result = calculate_moon_position(
        ObservationDateTime(date="2025-01-15", time="12:00:00"),
        LocationModel(latitude=31.5, longitude=35.5, elevation=-400.0)
    )

    assert result["location"]["elevation"] == -400.0
    assert "altitude" in result
    assert "azimuth" in result


def test_moon_azimuth_range():
    """Test that azimuth is always in the 0-360 range."""
    result = calculate_moon_position(
        ObservationDateTime(date="2025-01-15", time="12:00:00"),
        LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
    )

    assert 0 <= result["azimuth"] <= 360


def test_moon_altitude_range():
    """Test that altitude is always in the -90 to 90 range."""
    result = calculate_moon_position(
        ObservationDateTime(date="2025-01-15", time="12:00:00"),
        LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
    )

    assert -90 <= result["altitude"] <= 90


def test_moon_extreme_longitudes():
    """Test moon position at extreme longitude values."""
    result_west = calculate_moon_position(
        ObservationDateTime(date="2025-01-15", time="12:00:00"),
        LocationModel(latitude=0.0, longitude=-180.0, elevation=0.0)
    )

    result_east = calculate_moon_position(
        ObservationDateTime(date="2025-01-15", time="12:00:00"),
        LocationModel(latitude=0.0, longitude=180.0, elevation=0.0)
    )

    # Both should be valid
    assert "altitude" in result_west
    assert "altitude" in result_east


def test_invalid_latitude():
    """Test that latitude outside valid range raises ValidationError."""
    with pytest.raises(ValidationError, match="less_than_equal|greater_than_equal"):
        calculate_moon_position(
            ObservationDateTime(date="2025-01-15", time="12:00:00"),
            LocationModel(latitude=100.0, longitude=0.0, elevation=0.0)
        )


def test_invalid_longitude():
    """Test that longitude outside valid range raises ValidationError."""
    with pytest.raises(ValidationError, match="less_than_equal|greater_than_equal"):
        calculate_moon_position(
            ObservationDateTime(date="2025-01-15", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=200.0, elevation=0.0)
        )


def test_moon_types_are_python_native():
    """Test that returned values are Python native types, not numpy types."""
    result = calculate_moon_position(
        ObservationDateTime(date="2025-01-15", time="12:00:00"),
        LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
    )

    # Check that we get Python native types, not numpy
    assert type(result["altitude"]).__name__ == "float"
    assert type(result["azimuth"]).__name__ == "float"
    assert type(result["is_visible"]).__name__ == "bool"
    assert type(result["julian_date"]).__name__ == "float"
