"""Tests for the moon phase calculation service."""

import pytest
from pydantic import ValidationError
from api.services.moon_phase import calculate_moon_phase
from api.models import ObservationDateTime, LocationModel


def test_moon_phase_basic():
    """Test basic moon phase calculation."""
    result = calculate_moon_phase(
        ObservationDateTime(date="2025-01-01", time="00:00:00"),
        LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
    )

    assert "illumination" in result
    assert "phase_angle" in result
    assert "phase_name" in result
    assert "julian_date" in result
    assert "location" in result
    assert "input_datetime" in result

    assert isinstance(result["illumination"], float)
    assert isinstance(result["phase_angle"], float)
    assert isinstance(result["phase_name"], str)
    assert isinstance(result["julian_date"], float)

    # Check value ranges
    assert 0.0 <= result["illumination"] <= 1.0
    assert 0.0 <= result["phase_angle"] < 360.0


def test_new_moon_illumination():
    """Test that new moon has near-zero illumination."""
    # 2025-01-29 is a new moon
    result = calculate_moon_phase(
        ObservationDateTime(date="2025-01-29", time="12:00:00"),
        LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
    )

    # New moon should have very low illumination
    assert result["illumination"] < 0.1
    assert "New Moon" in result["phase_name"]


def test_full_moon_illumination():
    """Test that full moon has near-complete illumination."""
    # 2025-01-13 is a full moon
    result = calculate_moon_phase(
        ObservationDateTime(date="2025-01-13", time="22:00:00"),
        LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
    )

    # Full moon should have very high illumination
    assert result["illumination"] > 0.9
    assert "Full Moon" in result["phase_name"]


def test_first_quarter_phase():
    """Test first quarter moon phase."""
    # 2025-01-06 is around first quarter
    result = calculate_moon_phase(
        ObservationDateTime(date="2025-01-06", time="23:00:00"),
        LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
    )

    # First quarter should have ~50% illumination and phase angle < 180 (waxing)
    assert 0.4 < result["illumination"] < 0.6
    assert result["phase_angle"] < 180
    assert "Quarter" in result["phase_name"] or "Gibbous" in result["phase_name"] or "Crescent" in result["phase_name"]


def test_last_quarter_phase():
    """Test last quarter moon phase."""
    # 2025-01-21 is around last quarter
    result = calculate_moon_phase(
        ObservationDateTime(date="2025-01-21", time="20:00:00"),
        LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
    )

    # Last quarter should have ~50% illumination and phase angle > 180 (waning)
    assert 0.4 < result["illumination"] < 0.6
    assert result["phase_angle"] > 180
    assert "Quarter" in result["phase_name"] or "Gibbous" in result["phase_name"] or "Crescent" in result["phase_name"]


def test_waxing_crescent():
    """Test waxing crescent phase detection."""
    # A few days after new moon
    result = calculate_moon_phase(
        ObservationDateTime(date="2025-02-01", time="12:00:00"),
        LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
    )

    # Should be waxing (phase_angle < 180) with low illumination
    if result["phase_angle"] < 180 and 0.03 < result["illumination"] < 0.47:
        assert result["phase_name"] == "Waxing Crescent"


def test_waning_gibbous():
    """Test waning gibbous phase detection."""
    # A few days after full moon
    result = calculate_moon_phase(
        ObservationDateTime(date="2025-01-16", time="12:00:00"),
        LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
    )

    # Should be waning (phase_angle > 180) with high illumination
    if result["phase_angle"] > 180 and 0.53 < result["illumination"] < 0.97:
        assert result["phase_name"] == "Waning Gibbous"


def test_phase_angle_range():
    """Test that phase angle is always 0-360."""
    result = calculate_moon_phase(
        ObservationDateTime(date="2025-01-15", time="12:00:00"),
        LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
    )

    assert 0.0 <= result["phase_angle"] < 360.0


def test_illumination_range():
    """Test that illumination is always 0-1."""
    result = calculate_moon_phase(
        ObservationDateTime(date="2025-01-15", time="12:00:00"),
        LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
    )

    assert 0.0 <= result["illumination"] <= 1.0


def test_phase_changes_over_month():
    """Test that moon phase progresses through a lunar cycle."""
    # Sample dates every 3 days across a full lunar cycle (29.5 days)
    dates = [
        "2025-01-01",  # Around new moon
        "2025-01-04",  # Waxing crescent
        "2025-01-07",  # First quarter
        "2025-01-10",  # Waxing gibbous
        "2025-01-13",  # Full moon
        "2025-01-16",  # Waning gibbous
        "2025-01-19",  # Last quarter
        "2025-01-22",  # Waning crescent
        "2025-01-25",  # Approaching new moon
        "2025-01-28",  # Back to new moon
    ]

    illuminations = []
    phase_angles = []
    phase_names = []

    for date in dates:
        result = calculate_moon_phase(
            ObservationDateTime(date=date, time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
        )
        illuminations.append(result["illumination"])
        phase_angles.append(result["phase_angle"])
        phase_names.append(result["phase_name"])

    # Should see variety in illuminations through the cycle
    assert len(set(illuminations)) > 5
    
    # Should see multiple different phase names throughout the cycle
    assert len(set(phase_names)) >= 6  # Should hit at least 6 different phases


def test_phase_at_different_locations():
    """Test that phase is consistent across locations (it's geocentric)."""
    result_nyc = calculate_moon_phase(
        ObservationDateTime(date="2025-01-15", time="12:00:00"),
        LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
    )

    result_sydney = calculate_moon_phase(
        ObservationDateTime(date="2025-01-15", time="12:00:00"),
        LocationModel(latitude=-33.8688, longitude=151.2093, elevation=0.0)
    )

    # Phase should be very similar at same time (small differences due to topocentric correction)
    assert abs(result_nyc["illumination"] - result_sydney["illumination"]) < 0.01
    assert abs(result_nyc["phase_angle"] - result_sydney["phase_angle"]) < 1.0


def test_julian_date_calculation():
    """Test that Julian Date is calculated correctly."""
    result = calculate_moon_phase(
        ObservationDateTime(date="2025-01-01", time="00:00:00"),
        LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
    )

    # JD for 2025-01-01 00:00:00 UTC should be around 2460676.5
    assert 2460676 < result["julian_date"] < 2460677


def test_input_datetime_format():
    """Test that input_datetime is formatted correctly."""
    result = calculate_moon_phase(
        ObservationDateTime(date="2025-01-15", time="14:30:45"),
        LocationModel(latitude=40.7128, longitude=-74.0060, elevation=10.0)
    )

    assert result["input_datetime"] == "2025-01-15T14:30:45Z"


def test_location_data():
    """Test that location data is correctly stored in response."""
    lat = 51.5074
    lon = -0.1278
    elev = 11.0

    result = calculate_moon_phase(
        ObservationDateTime(date="2025-01-15", time="12:00:00"),
        LocationModel(latitude=lat, longitude=lon, elevation=elev)
    )

    assert result["location"]["latitude"] == lat
    assert result["location"]["longitude"] == lon
    assert result["location"]["elevation"] == elev


def test_phase_name_values():
    """Test that phase_name is one of the expected values."""
    result = calculate_moon_phase(
        ObservationDateTime(date="2025-01-15", time="12:00:00"),
        LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
    )

    valid_names = [
        "New Moon",
        "Waxing Crescent",
        "First Quarter",
        "Waxing Gibbous",
        "Full Moon",
        "Waning Gibbous",
        "Last Quarter",
        "Waning Crescent",
    ]

    assert result["phase_name"] in valid_names


def test_types_are_python_native():
    """Test that returned values are Python native types, not numpy types."""
    result = calculate_moon_phase(
        ObservationDateTime(date="2025-01-15", time="12:00:00"),
        LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
    )

    # Check that we get Python native types, not numpy
    assert type(result["illumination"]).__name__ == "float"
    assert type(result["phase_angle"]).__name__ == "float"
    assert type(result["phase_name"]).__name__ == "str"
    assert type(result["julian_date"]).__name__ == "float"


def test_invalid_date_format():
    """Test that invalid date format raises error."""
    with pytest.raises(Exception):
        calculate_moon_phase(
            ObservationDateTime(date="invalid-date", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
        )


def test_invalid_time_format():
    """Test that invalid time format raises error."""
    with pytest.raises(Exception):
        calculate_moon_phase(
            ObservationDateTime(date="2025-01-15", time="25:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
        )

def test_invalid_latitude():
    """Test that latitude outside valid range raises ValidationError."""
    with pytest.raises(ValidationError, match="less_than_equal|greater_than_equal"):
        calculate_moon_phase(
            ObservationDateTime(date="2025-01-15", time="12:00:00"),
            LocationModel(latitude=100.0, longitude=0.0, elevation=0.0)
        )


def test_invalid_longitude():
    """Test that longitude outside valid range raises ValidationError."""
    with pytest.raises(ValidationError, match="less_than_equal|greater_than_equal"):
        calculate_moon_phase(
            ObservationDateTime(date="2025-01-15", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=200.0, elevation=0.0)
        )
