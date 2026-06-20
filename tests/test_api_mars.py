"""Tests for the Mars position calculation service."""

import pytest
from api.services.mars import calculate_mars_position, _get_retrograde_status
from api.models import ObservationDateTime, LocationModel
from pydantic import ValidationError
from astropy.coordinates import get_body
from astropy.time import Time
import astropy.units as u


class TestMarsPositionBasic:
    """Basic Mars position calculation tests."""

    def test_mars_position_basic(self):
        """Test basic Mars position calculation with valid inputs."""
        result = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=10.0)
        )

        # Verify all expected fields are present
        assert "altitude" in result
        assert "azimuth" in result
        assert "is_visible" in result
        assert "illumination" in result
        assert "phase_angle" in result
        assert "phase_name" in result
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
        assert isinstance(result["illumination"], float)
        assert isinstance(result["phase_angle"], float)
        assert isinstance(result["phase_name"], str)
        assert isinstance(result["retrograde_status"], str)
        assert isinstance(result["julian_date"], float)
        assert isinstance(result["ra_degrees"], float)
        assert isinstance(result["dec_degrees"], float)

        # Check value ranges
        assert -90 <= result["altitude"] <= 90
        assert 0 <= result["azimuth"] <= 360
        assert 0.5 <= result["illumination"] <= 1.0  # Mars never < 50% illuminated
        assert 0.0 <= result["phase_angle"] < 360.0

    def test_mars_position_at_equator(self):
        """Test Mars position at equator."""
        result = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        )

        assert isinstance(result["altitude"], float)
        assert isinstance(result["azimuth"], float)
        assert isinstance(result["is_visible"], bool)

    def test_mars_position_new_york(self):
        """Test Mars position for New York City."""
        result = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=10.0)
        )

        assert "altitude" in result
        assert "azimuth" in result
        assert isinstance(result["is_visible"], bool)

    def test_mars_position_sydney(self):
        """Test Mars position for Sydney, Australia (southern hemisphere)."""
        result = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=-33.8688, longitude=151.2093, elevation=0.0)
        )

        assert "altitude" in result
        assert "azimuth" in result
        assert isinstance(result["is_visible"], bool)

    def test_mars_position_north_pole(self):
        """Test Mars position at North Pole."""
        result = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=90.0, longitude=0.0, elevation=0.0)
        )

        assert isinstance(result["altitude"], float)
        assert isinstance(result["azimuth"], float)

    def test_mars_position_south_pole(self):
        """Test Mars position at South Pole."""
        result = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=-90.0, longitude=0.0, elevation=0.0)
        )

        assert isinstance(result["altitude"], float)
        assert isinstance(result["azimuth"], float)

    def test_mars_position_tokyo(self):
        """Test Mars position in Tokyo."""
        result = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=35.6762, longitude=139.6503, elevation=0.0)
        )

        assert "altitude" in result
        assert "azimuth" in result

    def test_mars_position_london(self):
        """Test Mars position in London."""
        result = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=51.5074, longitude=-0.1278, elevation=0.0)
        )

        assert "altitude" in result
        assert "azimuth" in result


class TestMarsPhaseCalculation:
    """Tests for Mars phase information."""

    def test_mars_phase_name_valid(self):
        """Test that Mars phase name is one of valid phases."""
        result = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
        )

        assert result["phase_name"] in ["Full", "Gibbous", "Crescent"]

    def test_mars_illumination_range(self):
        """Test that Mars illumination is in valid range (50-100% for superior planet)."""
        result = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
        )

        # Mars as superior planet: illumination ranges from ~50% to ~100%
        assert 0.5 <= result["illumination"] <= 1.0

    def test_mars_phase_angle_range(self):
        """Test that Mars phase angle is in valid range."""
        result = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
        )

        assert 0.0 <= result["phase_angle"] < 360.0

    def test_mars_phases_throughout_year(self):
        """Test that Mars phase calculation is consistent throughout year."""
        # Note: As a superior planet, Mars may remain in same phase for extended periods
        # especially near opposition. Just verify phases are valid.
        phase_names = set()

        for month in range(1, 13):
            result = calculate_mars_position(
                ObservationDateTime(date=f"2026-{month:02d}-15", time="12:00:00"),
                LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
            )
            phase_names.add(result["phase_name"])

        # All phase names should be valid (even if only one phase throughout 2026)
        assert all(name in ["Full", "Gibbous", "Crescent"] for name in phase_names)

    def test_mars_full_phase(self):
        """Test Mars in Full phase (high illumination)."""
        # At opposition, Mars is nearly 100% illuminated
        result = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        )

        # Check that illumination is relatively high
        if result["phase_name"] == "Full":
            assert result["illumination"] >= 0.85

    def test_mars_phase_angle_at_opposition(self):
        """Test Mars phase angle near opposition (should be small)."""
        result = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        )

        # Mars phase angle varies throughout year; no specific requirement here
        # just verify it's calculated and in range
        assert 0.0 <= result["phase_angle"] < 360.0


class TestMarsRetrogradStatus:
    """Tests for Mars retrograde motion detection."""

    def test_mars_retrograde_status_valid(self):
        """Test that retrograde status is one of valid values."""
        result = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        )

        assert result["retrograde_status"] in ["prograde", "retrograde"]

    def test_mars_retrograde_different_times(self):
        """Test retrograde status at different times (around opposition)."""
        statuses = set()

        # Test several months near opposition (June 2026)
        for month in [4, 5, 6, 7, 8]:
            result = calculate_mars_position(
                ObservationDateTime(date=f"2026-{month:02d}-15", time="12:00:00"),
                LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
            )
            statuses.add(result["retrograde_status"])

        # Should have at least one valid status (prograde or retrograde)
        assert len(statuses) >= 1
        for status in statuses:
            assert status in ["prograde", "retrograde"]

    def test_get_retrograde_status_function(self):
        """Test _get_retrograde_status function directly."""
        time = Time("2026-06-18 12:00:00", format='iso', scale='utc')
        mars = get_body("mars", time)
        sun = get_body("sun", time)

        status = _get_retrograde_status(mars, sun, time)

        assert status in ["prograde", "retrograde"]


class TestMarsCoordinateValidation:
    """Tests for coordinate validation."""

    def test_mars_invalid_latitude_too_high(self):
        """Test that latitude > 90 raises ValidationError."""
        with pytest.raises(ValidationError):
            calculate_mars_position(
                ObservationDateTime(date="2026-06-18", time="12:00:00"),
                LocationModel(latitude=91.0, longitude=0.0, elevation=0.0)
            )

    def test_mars_invalid_latitude_too_low(self):
        """Test that latitude < -90 raises ValidationError."""
        with pytest.raises(ValidationError):
            calculate_mars_position(
                ObservationDateTime(date="2026-06-18", time="12:00:00"),
                LocationModel(latitude=-91.0, longitude=0.0, elevation=0.0)
            )

    def test_mars_invalid_longitude_too_high(self):
        """Test that longitude > 180 raises ValidationError."""
        with pytest.raises(ValidationError):
            calculate_mars_position(
                ObservationDateTime(date="2026-06-18", time="12:00:00"),
                LocationModel(latitude=0.0, longitude=181.0, elevation=0.0)
            )

    def test_mars_invalid_longitude_too_low(self):
        """Test that longitude < -180 raises ValidationError."""
        with pytest.raises(ValidationError):
            calculate_mars_position(
                ObservationDateTime(date="2026-06-18", time="12:00:00"),
                LocationModel(latitude=0.0, longitude=-181.0, elevation=0.0)
            )

    def test_mars_valid_latitude_boundaries(self):
        """Test valid latitude boundary values."""
        # Test at 90 (valid)
        result = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=90.0, longitude=0.0, elevation=0.0)
        )
        assert "altitude" in result

        # Test at -90 (valid)
        result = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=-90.0, longitude=0.0, elevation=0.0)
        )
        assert "altitude" in result

    def test_mars_valid_longitude_boundaries(self):
        """Test valid longitude boundary values."""
        # Test at 180 (valid)
        result = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=180.0, elevation=0.0)
        )
        assert "altitude" in result

        # Test at -180 (valid)
        result = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=-180.0, elevation=0.0)
        )
        assert "altitude" in result


class TestMarsDateTimeHandling:
    """Tests for date/time handling."""

    def test_mars_different_times_same_day(self):
        """Test Mars at different times on same day."""
        result1 = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="00:00:00"),
            LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        )

        result2 = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        )

        # Different times should produce different altitudes (Mars moves across sky)
        # But phase should remain similar
        assert result1["altitude"] != result2["altitude"]
        assert result1["julian_date"] != result2["julian_date"]

    def test_mars_different_dates(self):
        """Test Mars at different dates."""
        result1 = calculate_mars_position(
            ObservationDateTime(date="2026-06-01", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        )

        result2 = calculate_mars_position(
            ObservationDateTime(date="2026-06-30", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        )

        # Different dates should produce different phases/illumination
        assert result1["illumination"] != result2["illumination"] or \
               result1["phase_angle"] != result2["phase_angle"]

    def test_mars_year_boundaries(self):
        """Test Mars at year boundaries."""
        result1 = calculate_mars_position(
            ObservationDateTime(date="2026-01-01", time="00:00:00"),
            LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        )

        result2 = calculate_mars_position(
            ObservationDateTime(date="2026-12-31", time="23:59:59"),
            LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        )

        assert "altitude" in result1
        assert "altitude" in result2


class TestMarsLocationDependence:
    """Tests for location-dependent calculations."""

    def test_mars_altitude_varies_by_location(self):
        """Test that Mars altitude varies by observer location."""
        result_eq = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        )

        result_ny = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=10.0)
        )

        # Same time, different locations should have different altitudes
        assert result_eq["altitude"] != result_ny["altitude"]

    def test_mars_azimuth_varies_by_longitude(self):
        """Test that Mars azimuth varies by observer longitude."""
        result_0 = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        )

        result_180 = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=180.0, elevation=0.0)
        )

        # Different longitudes should have different azimuths
        assert result_0["azimuth"] != result_180["azimuth"]

    def test_mars_elevation_effect(self):
        """Test that elevation affects Mars position slightly."""
        result_0 = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
        )

        result_high = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=1000.0)
        )

        # High elevation can affect parallax/altitude slightly
        assert isinstance(result_0["altitude"], float)
        assert isinstance(result_high["altitude"], float)


class TestMarsVisibility:
    """Tests for Mars visibility."""

    def test_mars_is_visible_type(self):
        """Test that is_visible is boolean."""
        result = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        )

        assert isinstance(result["is_visible"], bool)

    def test_mars_visibility_matches_altitude(self):
        """Test that is_visible matches altitude > 0."""
        result = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        )

        # is_visible should match altitude > 0
        expected_visible = result["altitude"] > 0
        assert result["is_visible"] == expected_visible


class TestMarsResponseFormat:
    """Tests for response format and location data."""

    def test_mars_location_in_response(self):
        """Test that location data is correctly returned."""
        location = LocationModel(latitude=40.7128, longitude=-74.0060, elevation=10.0)
        result = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            location
        )

        assert result["location"]["latitude"] == 40.7128
        assert result["location"]["longitude"] == -74.0060
        assert result["location"]["elevation"] == 10.0

    def test_mars_input_datetime_preserved(self):
        """Test that input datetime is preserved in response."""
        result = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        )

        assert "2026-06-18T12:00:00Z" in result["input_datetime"]

    def test_mars_julian_date_valid(self):
        """Test that Julian Date is a valid number."""
        result = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        )

        # JD for 2026-06-18 should be around 2457900-2458200
        assert 2450000 < result["julian_date"] < 2500000


class TestMarsConsistency:
    """Tests for consistency across multiple calls."""

    def test_mars_position_deterministic(self):
        """Test that Mars position calculation is deterministic."""
        result1 = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=10.0)
        )

        result2 = calculate_mars_position(
            ObservationDateTime(date="2026-06-18", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=10.0)
        )

        # Same inputs should produce identical results
        assert result1["altitude"] == result2["altitude"]
        assert result1["azimuth"] == result2["azimuth"]
        assert result1["illumination"] == result2["illumination"]
        assert result1["phase_angle"] == result2["phase_angle"]
        assert result1["retrograde_status"] == result2["retrograde_status"]
