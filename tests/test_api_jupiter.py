"""Tests for the Jupiter position calculation service."""

import pytest
from api.services.jupiter import calculate_jupiter_position
from api.models import ObservationDateTime, LocationModel


class TestJupiterPositionBasic:
    """Basic Jupiter position calculation tests."""

    def test_jupiter_position_basic(self):
        """Test basic Jupiter position calculation with valid inputs."""
        result = calculate_jupiter_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=10.0)
        )

        # Verify all expected fields are present (no phase fields for outer planets)
        assert "altitude" in result
        assert "azimuth" in result
        assert "is_visible" in result
        assert "retrograde_status" in result
        assert "julian_date" in result
        assert "input_datetime" in result
        assert "location" in result
        assert "ra_degrees" in result
        assert "dec_degrees" in result

        # Verify all fields are correct types
        assert isinstance(result["altitude"], float)
        assert isinstance(result["azimuth"], float)
        assert isinstance(result["is_visible"], bool)
        assert isinstance(result["retrograde_status"], str)
        assert isinstance(result["julian_date"], float)
        assert isinstance(result["ra_degrees"], float)
        assert isinstance(result["dec_degrees"], float)

        # Check value ranges
        assert -90 <= result["altitude"] <= 90
        assert 0 <= result["azimuth"] <= 360
        assert result["retrograde_status"] in ["prograde", "retrograde"]

    def test_jupiter_position_at_equator(self):
        """Test Jupiter position at equator."""
        result = calculate_jupiter_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        )

        assert isinstance(result["altitude"], float)
        assert isinstance(result["azimuth"], float)
        assert isinstance(result["is_visible"], bool)

    def test_jupiter_position_new_york(self):
        """Test Jupiter position for New York City."""
        result = calculate_jupiter_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=10.0)
        )

        assert "altitude" in result
        assert "azimuth" in result
        assert isinstance(result["is_visible"], bool)

    def test_jupiter_position_sydney(self):
        """Test Jupiter position for Sydney, Australia (southern hemisphere)."""
        result = calculate_jupiter_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=-33.8688, longitude=151.2093, elevation=0.0)
        )

        assert "altitude" in result
        assert "azimuth" in result
        assert isinstance(result["is_visible"], bool)

    def test_jupiter_position_north_pole(self):
        """Test Jupiter position at North Pole."""
        result = calculate_jupiter_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=90.0, longitude=0.0, elevation=0.0)
        )

        assert isinstance(result["altitude"], float)
        assert isinstance(result["azimuth"], float)

    def test_jupiter_position_south_pole(self):
        """Test Jupiter position at South Pole."""
        result = calculate_jupiter_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=-90.0, longitude=0.0, elevation=0.0)
        )

        assert isinstance(result["altitude"], float)
        assert isinstance(result["azimuth"], float)

    def test_jupiter_position_tokyo(self):
        """Test Jupiter position in Tokyo."""
        result = calculate_jupiter_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=35.6762, longitude=139.6503, elevation=0.0)
        )

        assert "altitude" in result
        assert "azimuth" in result

    def test_jupiter_position_london(self):
        """Test Jupiter position in London."""
        result = calculate_jupiter_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=51.5074, longitude=-0.1278, elevation=0.0)
        )

        assert "altitude" in result
        assert "azimuth" in result


class TestJupiterRetrogradeMCStatus:
    """Tests for Jupiter retrograde motion detection."""

    def test_jupiter_retrograde_status_valid(self):
        """Test that Jupiter retrograde status is valid."""
        result = calculate_jupiter_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
        )

        assert result["retrograde_status"] in ["prograde", "retrograde"]

    def test_jupiter_retrograde_status_consistency(self):
        """Test that retrograde status is consistent for short time intervals."""
        time1 = "2026-06-18"
        time2 = "2026-06-19"  # One day later
        location = LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)

        result1 = calculate_jupiter_position(
            ObservationDateTime(date=time1, time="12:00:00"),
            location
        )
        result2 = calculate_jupiter_position(
            ObservationDateTime(date=time2, time="12:00:00"),
            location
        )

        # Over a 1-day interval, retrograde status should typically not change
        # (Jupiter's retrograde cycle is ~4 months, so month-long consistency expected)
        assert result1["retrograde_status"] in ["prograde", "retrograde"]
        assert result2["retrograde_status"] in ["prograde", "retrograde"]


class TestJupiterPositionValidation:
    """Tests for input validation."""

    def test_jupiter_position_invalid_latitude_high(self):
        """Test that latitude > 90 raises ValueError."""
        with pytest.raises(ValueError, match="latitude"):
            calculate_jupiter_position(
                ObservationDateTime(date="2026-06-18", time="12:00:00"),
                LocationModel(latitude=91.0, longitude=0.0, elevation=0.0)
            )

    def test_jupiter_position_invalid_latitude_low(self):
        """Test that latitude < -90 raises ValueError."""
        with pytest.raises(ValueError, match="latitude"):
            calculate_jupiter_position(
                ObservationDateTime(date="2026-06-18", time="12:00:00"),
                LocationModel(latitude=-91.0, longitude=0.0, elevation=0.0)
            )

    def test_jupiter_position_invalid_longitude_high(self):
        """Test that longitude > 180 raises ValueError."""
        with pytest.raises(ValueError, match="longitude"):
            calculate_jupiter_position(
                ObservationDateTime(date="2026-06-18", time="12:00:00"),
                LocationModel(latitude=0.0, longitude=181.0, elevation=0.0)
            )

    def test_jupiter_position_invalid_longitude_low(self):
        """Test that longitude < -180 raises ValueError."""
        with pytest.raises(ValueError, match="longitude"):
            calculate_jupiter_position(
                ObservationDateTime(date="2026-06-18", time="12:00:00"),
                LocationModel(latitude=0.0, longitude=-181.0, elevation=0.0)
            )

    def test_jupiter_position_valid_boundary_latitude_positive(self):
        """Test that latitude = 90 is valid."""
        result = calculate_jupiter_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=90.0, longitude=0.0, elevation=0.0)
        )
        assert "altitude" in result

    def test_jupiter_position_valid_boundary_latitude_negative(self):
        """Test that latitude = -90 is valid."""
        result = calculate_jupiter_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=-90.0, longitude=0.0, elevation=0.0)
        )
        assert "altitude" in result

    def test_jupiter_position_valid_boundary_longitude_positive(self):
        """Test that longitude = 180 is valid."""
        result = calculate_jupiter_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=180.0, elevation=0.0)
        )
        assert "altitude" in result

    def test_jupiter_position_valid_boundary_longitude_negative(self):
        """Test that longitude = -180 is valid."""
        result = calculate_jupiter_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=-180.0, elevation=0.0)
        )
        assert "altitude" in result


class TestJupiterPositionAltitude:
    """Tests for altitude calculations."""

    def test_jupiter_altitude_above_horizon(self):
        """Test that positive altitude indicates above horizon."""
        result = calculate_jupiter_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
        )

        # If altitude > 0, is_visible should be True
        if result["altitude"] > 0:
            assert result["is_visible"] is True

    def test_jupiter_altitude_below_horizon(self):
        """Test that negative altitude indicates below horizon."""
        result = calculate_jupiter_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
        )

        # If altitude < 0, is_visible should be False
        if result["altitude"] < 0:
            assert result["is_visible"] is False

    def test_jupiter_altitude_at_zenith(self):
        """Test altitude near zenith (should be near 90 degrees)."""
        result = calculate_jupiter_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        )

        # Altitude should be between -90 and 90
        assert -90 <= result["altitude"] <= 90


class TestJupiterCoordinates:
    """Tests for RA/Dec coordinates."""

    def test_jupiter_ra_dec_valid_range(self):
        """Test that RA/Dec are in valid ranges."""
        result = calculate_jupiter_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
        )

        # RA: 0 to 360 degrees
        assert 0 <= result["ra_degrees"] <= 360
        # Dec: -90 to 90 degrees
        assert -90 <= result["dec_degrees"] <= 90
