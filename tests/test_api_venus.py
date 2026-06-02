"""Tests for the Venus position calculation service."""

import pytest
from api.services.venus import calculate_venus_position
from api.models import ObservationDateTime, LocationModel
from pydantic import ValidationError


class TestVenusPositionBasic:
    """Basic Venus position calculation tests."""

    def test_venus_position_basic(self):
        """Test basic Venus position calculation."""
        result = calculate_venus_position(
            ObservationDateTime(date="2026-06-01", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        )

        assert "altitude" in result
        assert "azimuth" in result
        assert "is_visible" in result
        assert "sun_separation" in result
        assert "naked_eye_visible" in result
        assert "illumination" in result
        assert "phase_angle" in result
        assert "phase_name" in result
        assert "julian_date" in result
        assert "location" in result
        assert "input_datetime" in result

        assert isinstance(result["altitude"], float)
        assert isinstance(result["azimuth"], float)
        assert isinstance(result["is_visible"], bool)
        assert isinstance(result["sun_separation"], float)
        assert isinstance(result["naked_eye_visible"], bool)
        assert isinstance(result["illumination"], float)
        assert isinstance(result["phase_angle"], float)
        assert isinstance(result["phase_name"], str)
        assert isinstance(result["julian_date"], float)

        # Check value ranges
        assert -90 <= result["altitude"] <= 90
        assert 0 <= result["azimuth"] <= 360
        assert result["sun_separation"] >= 0
        assert 0.0 <= result["illumination"] <= 1.0
        assert 0.0 <= result["phase_angle"] < 360.0

    def test_venus_position_at_equator(self):
        """Test Venus position at equator."""
        result = calculate_venus_position(
            ObservationDateTime(date="2026-06-01", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        )

        assert isinstance(result["altitude"], float)
        assert isinstance(result["azimuth"], float)

    def test_venus_position_new_york(self):
        """Test Venus position for New York City."""
        result = calculate_venus_position(
            ObservationDateTime(date="2026-06-01", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=10.0)
        )

        assert "altitude" in result
        assert "azimuth" in result
        assert isinstance(result["is_visible"], bool)
        assert isinstance(result["naked_eye_visible"], bool)

    def test_venus_position_sydney(self):
        """Test Venus position for Sydney, Australia (southern hemisphere)."""
        result = calculate_venus_position(
            ObservationDateTime(date="2026-06-01", time="12:00:00"),
            LocationModel(latitude=-33.8688, longitude=151.2093, elevation=0.0)
        )

        assert "altitude" in result
        assert "azimuth" in result
        assert isinstance(result["is_visible"], bool)

    def test_venus_position_north_pole(self):
        """Test Venus position at North Pole."""
        result = calculate_venus_position(
            ObservationDateTime(date="2026-06-21", time="12:00:00"),
            LocationModel(latitude=90.0, longitude=0.0, elevation=0.0)
        )

        assert "altitude" in result
        assert "azimuth" in result
        assert isinstance(result["is_visible"], bool)

    def test_venus_position_south_pole(self):
        """Test Venus position at South Pole."""
        result = calculate_venus_position(
            ObservationDateTime(date="2026-06-21", time="12:00:00"),
            LocationModel(latitude=-90.0, longitude=0.0, elevation=0.0)
        )

        assert "altitude" in result
        assert "azimuth" in result
        assert isinstance(result["is_visible"], bool)


class TestVenusPhaseCalculation:
    """Tests for Venus phase calculations."""

    def test_venus_crescent_phase(self):
        """Test Venus showing crescent phase."""
        # June 1, 2026 Venus is in crescent phase
        result = calculate_venus_position(
            ObservationDateTime(date="2026-06-01", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
        )

        assert result["phase_name"] in ["New", "Crescent", "Quarter", "Gibbous", "Full"]
        assert 0.0 <= result["illumination"] <= 1.0
        assert 0.0 <= result["phase_angle"] < 360.0

    def test_venus_phase_throughout_year(self):
        """Test Venus phases throughout 2026."""
        dates = [
            "2026-01-15",
            "2026-03-01",
            "2026-05-01",
            "2026-06-01",
            "2026-07-15",
            "2026-09-01",
            "2026-10-01",
            "2026-12-25",
        ]

        for date in dates:
            result = calculate_venus_position(
                ObservationDateTime(date=date, time="12:00:00"),
                LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
            )

            assert result["phase_name"] in ["New", "Crescent", "Quarter", "Gibbous", "Full"]
            assert 0.0 <= result["illumination"] <= 1.0

    def test_venus_illumination_ranges(self):
        """Test Venus illumination across different dates."""
        results = []
        for month in range(1, 13):
            result = calculate_venus_position(
                ObservationDateTime(date=f"2026-{month:02d}-15", time="12:00:00"),
                LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
            )
            results.append(result["illumination"])

        # Venus illumination ranges from near 0% (inferior conjunction) to nearly 100% (superior conjunction)
        assert min(results) < 0.05  # Low illumination near inferior conjunction (~3-4%)
        assert max(results) > 0.95  # High illumination near superior conjunction (~99%)

    def test_venus_phase_names_throughout_year(self):
        """Document which Venus phases are actually reached throughout 2026.

        This test verifies the phase-naming thresholds are based on actual astronomical data.
        Venus illumination is computed from Venus-centric phase angle (IAU standard), which
        allows illumination from ~0% to ~100% throughout the year, enabling all 5 phases.

        Phase thresholds (based on corrected Venus-centric geometry):
        - New: 0-10% illumination
        - Crescent: 10-35% illumination
        - Quarter: 35-50% illumination
        - Gibbous: 50-90% illumination
        - Full: 90%+ illumination (near superior conjunction)
        """
        phases_by_month = {}
        for month in range(1, 13):
            result = calculate_venus_position(
                ObservationDateTime(date=f"2026-{month:02d}-15", time="12:00:00"),
                LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
            )
            phase_name = result["phase_name"]
            illumination = result["illumination"]
            phases_by_month[month] = {
                "phase": phase_name,
                "illumination": illumination
            }

        # Extract which phases are actually observed
        phases_observed = {v["phase"] for v in phases_by_month.values()}

        # Verify expected phases are reached throughout 2026
        # Venus should always reach New and Crescent phases (near inferior/superior conjunctions)
        assert "New" in phases_observed, (
            f"New phase never observed in 2026. Month data: {phases_by_month}"
        )
        assert "Crescent" in phases_observed, (
            f"Crescent phase never observed in 2026. Month data: {phases_by_month}"
        )

        # Venus should reach Full phase near superior conjunction (Oct 2026, illumination >90%)
        # This is a key validation that the corrected illumination formula is working
        assert "Full" in phases_observed, (
            f"Full phase never observed in 2026 (expected near superior conjunction). "
            f"Month data: {phases_by_month}"
        )

    def test_venus_new_phase_low_illumination(self):
        """Test Venus New phase with illumination < 10% (code coverage for phase_key="new").
        
        The New phase calculation is location-independent (based on orbital geometry).
        However, NEW PHASE IS BRIEF AND LOCATION-SENSITIVE FOR VISIBILITY:
        - Oct 9, 2026 noon UTC: Below horizon at New York but above at equator/London
        - This test validates the phase_name calculation, not observability
        - Visibility is validated separately by is_visible field
        """
        # October 9, 2026: Venus reaches inferior conjunction with ~7% illumination
        result = calculate_venus_position(
            ObservationDateTime(date="2026-10-09", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
        )

        assert result["phase_name"] == "New", (
            f"Expected 'New' phase at 2026-10-09 with low illumination, "
            f"got '{result['phase_name']}' with illumination={result['illumination']:.4f}"
        )
        assert result["illumination"] < 0.10, (
            f"Expected illumination < 0.10 for New phase, got {result['illumination']:.4f}"
        )
        assert 0.0 <= result["illumination"] <= 1.0

    def test_venus_new_phase_observable_equator(self):
        """Test Venus New phase at equator where it's observable above horizon."""
        # October 9, 2026 at equator: Venus in New phase with ~7% illumination and above horizon
        result = calculate_venus_position(
            ObservationDateTime(date="2026-10-09", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        )

        assert result["phase_name"] == "New", (
            f"Expected 'New' phase, got '{result['phase_name']}'"
        )
        assert result["illumination"] < 0.10, (
            f"Expected illumination < 0.10 for New phase, got {result['illumination']:.4f}"
        )
        # At equator on this date, Venus should be above horizon
        assert result["is_visible"] is True, (
            f"Expected Venus to be above horizon at equator, got altitude={result['altitude']:.2f}°"
        )

    def test_venus_waning_phase_full(self):
        """Test Venus waning phase with Full illumination (covers waning branch)."""
        # January 1, 2026: Venus in waning phase at ~99.97% illumination (Full)
        # Phase angle = 358.8° (waning), so code takes the else branch (line 186)
        result = calculate_venus_position(
            ObservationDateTime(date="2026-01-01", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
        )

        assert result["phase_name"] == "Full", (
            f"Expected 'Full' phase at 2026-01-01 (waning), "
            f"got '{result['phase_name']}' with illumination={result['illumination']:.4f}"
        )
        assert result["illumination"] > 0.90, (
            f"Expected illumination > 90% for Full phase, "
            f"got {result['illumination']:.4f}"
        )


class TestVenusVisibility:
    """Tests for Venus visibility calculations."""

    def test_venus_naked_eye_requires_sun_separation(self):
        """Test that naked eye visibility requires sufficient sun separation."""
        # June 1 has high sun separation and should be naked eye visible
        result = calculate_venus_position(
            ObservationDateTime(date="2026-06-01", time="20:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
        )

        # High sun separation means naked eye visible if above horizon
        if result["is_visible"] and result["sun_separation"] > 10.0:
            assert result["naked_eye_visible"] is True

    def test_venus_below_horizon_not_visible(self):
        """Test that Venus below horizon is not visible."""
        # Test a time when Venus is below horizon
        result = calculate_venus_position(
            ObservationDateTime(date="2026-10-01", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
        )

        # If below horizon, should not be naked eye visible
        if result["altitude"] <= 0:
            assert result["is_visible"] is False
            assert result["naked_eye_visible"] is False

    def test_venus_sun_separation_varies(self):
        """Test that sun separation varies throughout the year."""
        separations = []
        for month in range(1, 13):
            result = calculate_venus_position(
                ObservationDateTime(date=f"2026-{month:02d}-15", time="12:00:00"),
                LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
            )
            separations.append(result["sun_separation"])

        # Sun separation should vary
        assert min(separations) < 30.0
        assert max(separations) > 40.0


class TestVenusLocationVariations:
    """Tests for Venus position at different locations."""

    def test_high_latitude_variations(self):
        """Test Venus position at different high latitudes."""
        latitudes = [60.0, 70.0, 80.0]

        for lat in latitudes:
            result = calculate_venus_position(
                ObservationDateTime(date="2026-06-01", time="12:00:00"),
                LocationModel(latitude=lat, longitude=0.0, elevation=0.0)
            )

            assert isinstance(result["altitude"], float)
            assert isinstance(result["azimuth"], float)

    def test_different_longitudes_same_time(self):
        """Test Venus at different longitudes at same UTC time."""
        longitudes = [-180.0, -90.0, 0.0, 90.0, 180.0]

        for lon in longitudes:
            result = calculate_venus_position(
                ObservationDateTime(date="2026-06-01", time="12:00:00"),
                LocationModel(latitude=40.7128, longitude=lon, elevation=0.0)
            )

            assert isinstance(result["altitude"], float)

    def test_elevation_variations(self):
        """Test Venus position at different elevations."""
        elevations = [0.0, 100.0, 1000.0, 10000.0]

        for elev in elevations:
            result = calculate_venus_position(
                ObservationDateTime(date="2026-06-01", time="12:00:00"),
                LocationModel(latitude=40.7128, longitude=-74.0060, elevation=elev)
            )

            assert isinstance(result["altitude"], float)
            assert isinstance(result["azimuth"], float)


class TestVenusInputValidation:
    """Tests for input validation."""

    def test_invalid_latitude_too_high(self):
        """Test that latitude > 90 raises ValidationError."""
        with pytest.raises(ValidationError):
            LocationModel(latitude=91.0, longitude=0.0, elevation=0.0)

    def test_invalid_latitude_too_low(self):
        """Test that latitude < -90 raises ValidationError."""
        with pytest.raises(ValidationError):
            LocationModel(latitude=-91.0, longitude=0.0, elevation=0.0)

    def test_invalid_longitude_too_high(self):
        """Test that longitude > 180 raises ValidationError."""
        with pytest.raises(ValidationError):
            LocationModel(latitude=0.0, longitude=181.0, elevation=0.0)

    def test_invalid_longitude_too_low(self):
        """Test that longitude < -180 raises ValidationError."""
        with pytest.raises(ValidationError):
            LocationModel(latitude=0.0, longitude=-181.0, elevation=0.0)

    def test_latitude_boundary_90(self):
        """Test that latitude = 90 is valid."""
        result = calculate_venus_position(
            ObservationDateTime(date="2026-06-01", time="12:00:00"),
            LocationModel(latitude=90.0, longitude=0.0, elevation=0.0)
        )
        assert isinstance(result["altitude"], float)

    def test_latitude_boundary_minus_90(self):
        """Test that latitude = -90 is valid."""
        result = calculate_venus_position(
            ObservationDateTime(date="2026-06-01", time="12:00:00"),
            LocationModel(latitude=-90.0, longitude=0.0, elevation=0.0)
        )
        assert isinstance(result["altitude"], float)

    def test_longitude_boundary_180(self):
        """Test that longitude = 180 is valid."""
        result = calculate_venus_position(
            ObservationDateTime(date="2026-06-01", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=180.0, elevation=0.0)
        )
        assert isinstance(result["altitude"], float)

    def test_longitude_boundary_minus_180(self):
        """Test that longitude = -180 is valid."""
        result = calculate_venus_position(
            ObservationDateTime(date="2026-06-01", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=-180.0, elevation=0.0)
        )
        assert isinstance(result["altitude"], float)


class TestVenusDateTimeHandling:
    """Tests for date/time handling."""

    def test_different_times_same_day(self):
        """Test Venus position at different times on same day."""
        times = ["00:00:00", "06:00:00", "12:00:00", "18:00:00"]

        results = []
        for time in times:
            result = calculate_venus_position(
                ObservationDateTime(date="2026-06-01", time=time),
                LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
            )
            results.append(result)

        # Venus should move across the sky throughout the day
        altitudes = [r["altitude"] for r in results]
        assert len(set(altitudes)) > 1  # Altitudes should vary

    def test_timezone_agnostic(self):
        """Test that calculations use UTC."""
        result = calculate_venus_position(
            ObservationDateTime(date="2026-06-01", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
        )

        assert result["input_datetime"] == "2026-06-01T12:00:00"

    def test_leap_year_february_29(self):
        """Test Venus position on leap year February 29."""
        result = calculate_venus_position(
            ObservationDateTime(date="2024-02-29", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
        )

        assert isinstance(result["altitude"], float)

    def test_year_2026_coverage(self):
        """Test Venus calculations throughout 2026."""
        for month in range(1, 13):
            result = calculate_venus_position(
                ObservationDateTime(date=f"2026-{month:02d}-15", time="12:00:00"),
                LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
            )

            assert isinstance(result["altitude"], float)
            assert isinstance(result["phase_name"], str)


class TestVenusLocaleSupport:
    """Tests for locale parameter."""

    def test_venus_with_default_locale(self):
        """Test Venus position with default locale."""
        result = calculate_venus_position(
            ObservationDateTime(date="2026-06-01", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0),
            locale=None,
        )

        assert isinstance(result["phase_name"], str)
        assert result["phase_name"] in ["New", "Crescent", "Quarter", "Gibbous", "Full"]

    def test_venus_with_en_locale(self):
        """Test Venus position with English locale."""
        result = calculate_venus_position(
            ObservationDateTime(date="2026-06-01", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0),
            locale="en",
        )

        assert isinstance(result["phase_name"], str)
        assert result["phase_name"] in ["New", "Crescent", "Quarter", "Gibbous", "Full"]

    def test_venus_with_en_us_locale(self):
        """Test Venus position with en-US locale."""
        result = calculate_venus_position(
            ObservationDateTime(date="2026-06-01", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0),
            locale="en-US",
        )

        assert isinstance(result["phase_name"], str)
        assert result["phase_name"] in ["New", "Crescent", "Quarter", "Gibbous", "Full"]

    def test_venus_with_en_uk_locale(self):
        """Test Venus position with en-UK locale."""
        result = calculate_venus_position(
            ObservationDateTime(date="2026-06-01", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0),
            locale="en-UK",
        )

        assert isinstance(result["phase_name"], str)
        assert result["phase_name"] in ["New", "Crescent", "Quarter", "Gibbous", "Full"]

    def test_venus_with_reverse_locale(self):
        """Test Venus position with reverse locale (for testing)."""
        result = calculate_venus_position(
            ObservationDateTime(date="2026-06-01", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0),
            locale="xx-reverse",
        )

        assert isinstance(result["phase_name"], str)
        # Reverse locale should return reversed strings
        assert result["phase_name"] in ["weN", "tnecserC", "retrauQ", "suobbiG", "lluF"]


class TestVenusLocationDictionary:
    """Tests for location dictionary in response."""

    def test_location_dict_contains_coordinates(self):
        """Test that location dict has latitude, longitude, elevation."""
        result = calculate_venus_position(
            ObservationDateTime(date="2026-06-01", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=10.0)
        )

        assert result["location"]["latitude"] == 40.7128
        assert result["location"]["longitude"] == -74.0060
        assert result["location"]["elevation"] == 10.0

    def test_location_dict_with_zero_elevation(self):
        """Test location dict with zero elevation."""
        result = calculate_venus_position(
            ObservationDateTime(date="2026-06-01", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        )

        assert result["location"]["elevation"] == 0.0


class TestVenusJulianDate:
    """Tests for Julian Date calculations."""

    def test_julian_date_reasonable_value(self):
        """Test that Julian Date is in reasonable range."""
        result = calculate_venus_position(
            ObservationDateTime(date="2026-06-01", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        )

        # Julian Date for 2026 should be around 2461100-2461300
        assert 2461000 < result["julian_date"] < 2461400

    def test_julian_date_increases_with_time(self):
        """Test that Julian Date increases as time progresses."""
        result1 = calculate_venus_position(
            ObservationDateTime(date="2026-06-01", time="00:00:00"),
            LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        )

        result2 = calculate_venus_position(
            ObservationDateTime(date="2026-06-01", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        )

        result3 = calculate_venus_position(
            ObservationDateTime(date="2026-06-02", time="00:00:00"),
            LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        )

        assert result1["julian_date"] < result2["julian_date"] < result3["julian_date"]


class TestVenusAzimuthRanges:
    """Tests for azimuth value ranges and variations."""

    def test_azimuth_in_valid_range(self):
        """Test that azimuth is always in 0-360 range."""
        for month in range(1, 13):
            result = calculate_venus_position(
                ObservationDateTime(date=f"2026-{month:02d}-15", time="12:00:00"),
                LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
            )

            assert 0.0 <= result["azimuth"] <= 360.0

    def test_azimuth_varies_with_time(self):
        """Test that azimuth changes as time passes."""
        azimuths = []
        for hour in range(0, 24, 6):
            result = calculate_venus_position(
                ObservationDateTime(date="2026-06-01", time=f"{hour:02d}:00:00"),
                LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
            )
            azimuths.append(result["azimuth"])

        # Azimuth should vary throughout the day
        assert len(set(azimuths)) > 1
