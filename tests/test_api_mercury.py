"""
Tests for Mercury position calculation services and API endpoints
"""
import pytest
from api.models import ObservationDateTime, LocationModel
from api.services.mercury import calculate_mercury_position


class TestMercuryPositionService:
    """Tests for Mercury position calculation service"""

    def test_mercury_position_valid_date_time(self):
        """Test Mercury position calculation with valid date/time"""
        obs_time = ObservationDateTime(date="2026-06-01", time="12:00:00")
        location = LocationModel(latitude=40.7128, longitude=-74.0060, elevation=10.0)

        result = calculate_mercury_position(obs_time, location, locale="en")

        assert "altitude" in result
        assert "azimuth" in result
        assert "is_visible" in result
        assert "illumination" in result
        assert "phase_angle" in result
        assert "phase_name" in result
        assert "sun_separation" in result
        assert "naked_eye_visible" in result
        assert "julian_date" in result
        assert "input_datetime" in result
        assert "location" in result

    def test_mercury_position_illumination_range(self):
        """Test that Mercury illumination is between 0 and 1"""
        obs_time = ObservationDateTime(date="2026-06-01", time="12:00:00")
        location = LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)

        result = calculate_mercury_position(obs_time, location)

        assert 0.0 <= result["illumination"] <= 1.0

    def test_mercury_position_phase_angle_range(self):
        """Test that Mercury phase angle is between 0 and 360 degrees"""
        obs_time = ObservationDateTime(date="2026-06-01", time="12:00:00")
        location = LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)

        result = calculate_mercury_position(obs_time, location)

        assert 0.0 <= result["phase_angle"] <= 360.0

    def test_mercury_position_altitude_range(self):
        """Test that Mercury altitude is within valid range"""
        obs_time = ObservationDateTime(date="2026-06-01", time="12:00:00")
        location = LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)

        result = calculate_mercury_position(obs_time, location)

        # Altitude should be between -90 and 90 degrees
        assert -90 <= result["altitude"] <= 90

    def test_mercury_position_azimuth_range(self):
        """Test that Mercury azimuth is between 0 and 360 degrees"""
        obs_time = ObservationDateTime(date="2026-06-01", time="12:00:00")
        location = LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)

        result = calculate_mercury_position(obs_time, location)

        # Azimuth should be between 0 and 360 degrees
        assert 0 <= result["azimuth"] < 360

    def test_mercury_position_invalid_latitude(self):
        """Test that invalid latitude raises ValidationError"""
        obs_time = ObservationDateTime(date="2026-06-01", time="12:00:00")

        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            location = LocationModel(latitude=91.0, longitude=-74.0060, elevation=0.0)

    def test_mercury_position_invalid_longitude(self):
        """Test that invalid longitude raises ValidationError"""
        obs_time = ObservationDateTime(date="2026-06-01", time="12:00:00")

        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            location = LocationModel(latitude=40.7128, longitude=181.0, elevation=0.0)

    def test_mercury_position_various_locations(self):
        """Test Mercury position calculation at various global locations"""
        obs_time = ObservationDateTime(date="2026-06-01", time="12:00:00")
        locations = [
            LocationModel(latitude=0.0, longitude=0.0),      # Null Island
            LocationModel(latitude=90.0, longitude=0.0),     # North Pole
            LocationModel(latitude=-90.0, longitude=0.0),    # South Pole
            LocationModel(latitude=51.5074, longitude=-0.1278),  # London
            LocationModel(latitude=-33.8688, longitude=151.2093),  # Sydney
        ]

        for location in locations:
            result = calculate_mercury_position(obs_time, location)
            assert result["illumination"] >= 0.0
            assert result["illumination"] <= 1.0

    def test_mercury_position_midnight_utc(self):
        """Test Mercury position at midnight UTC"""
        obs_time = ObservationDateTime(date="2026-06-01", time="00:00:00")
        location = LocationModel(latitude=40.7128, longitude=-74.0060)

        result = calculate_mercury_position(obs_time, location)

        assert "altitude" in result
        assert isinstance(result["altitude"], float)

    def test_mercury_position_end_of_day_utc(self):
        """Test Mercury position at end of UTC day"""
        obs_time = ObservationDateTime(date="2026-06-01", time="23:59:59")
        location = LocationModel(latitude=40.7128, longitude=-74.0060)

        result = calculate_mercury_position(obs_time, location)

        assert "altitude" in result
        assert isinstance(result["altitude"], float)

    def test_mercury_position_phase_names(self):
        """Test that Mercury phase names are valid"""
        obs_time = ObservationDateTime(date="2026-06-01", time="12:00:00")
        location = LocationModel(latitude=40.7128, longitude=-74.0060)

        result = calculate_mercury_position(obs_time, location)

        # Phase name should be one of the valid phase names
        valid_phases = ["New", "Crescent", "Quarter", "Gibbous", "Full"]
        assert result["phase_name"] in valid_phases

    def test_mercury_position_visibility_logic(self):
        """Test that visibility flags are consistent"""
        obs_time = ObservationDateTime(date="2026-06-01", time="12:00:00")
        location = LocationModel(latitude=40.7128, longitude=-74.0060)

        result = calculate_mercury_position(obs_time, location)

        # If naked_eye_visible is True, is_visible must also be True
        if result["naked_eye_visible"]:
            assert result["is_visible"] is True

        # naked_eye_visible requires sufficient sun separation
        if result["naked_eye_visible"]:
            assert result["sun_separation"] > 14.5

    def test_mercury_position_minimum_elongation_threshold(self):
        """Test that Mercury minimum elongation threshold is ~14.5 degrees"""
        obs_time = ObservationDateTime(date="2026-06-01", time="12:00:00")
        location = LocationModel(latitude=40.7128, longitude=-74.0060)

        result = calculate_mercury_position(obs_time, location)

        # If sun_separation > 14.5 and altitude > 0, should be visible
        if result["altitude"] > 0 and result["sun_separation"] > 14.5:
            assert result["naked_eye_visible"] is True

    def test_mercury_position_leo_year_september(self):
        """Test Mercury position in September 2026"""
        obs_time = ObservationDateTime(date="2026-09-15", time="18:00:00")
        location = LocationModel(latitude=40.7128, longitude=-74.0060)

        result = calculate_mercury_position(obs_time, location)

        assert result["illumination"] >= 0.0
        assert result["illumination"] <= 1.0
        assert result["sun_separation"] >= 0.0

    def test_mercury_position_different_times_same_day(self):
        """Test that Mercury position changes throughout the day"""
        location = LocationModel(latitude=40.7128, longitude=-74.0060)
        
        result_midnight = calculate_mercury_position(
            ObservationDateTime(date="2026-06-01", time="00:00:00"),
            location
        )
        result_noon = calculate_mercury_position(
            ObservationDateTime(date="2026-06-01", time="12:00:00"),
            location
        )

        # Position should differ (though only slightly for Mercury)
        assert result_midnight["altitude"] != result_noon["altitude"] or \
               result_midnight["azimuth"] != result_noon["azimuth"]

    def test_mercury_position_preserves_location_data(self):
        """Test that location data is preserved in response"""
        obs_time = ObservationDateTime(date="2026-06-01", time="12:00:00")
        location = LocationModel(latitude=40.7128, longitude=-74.0060, elevation=100.5)

        result = calculate_mercury_position(obs_time, location)

        assert result["location"]["latitude"] == 40.7128
        assert result["location"]["longitude"] == -74.0060
        assert result["location"]["elevation"] == 100.5


class TestMercuryRoutes:
    """Tests for Mercury API routes"""

    def test_mercury_position_endpoint_valid_request(self, client):
        """Test /api/v1/mercury-position endpoint with valid request"""
        response = client.post(
            "/api/v1/mercury-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 10.0
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "altitude" in data
        assert "azimuth" in data
        assert "illumination" in data
        assert "phase_name" in data

    def test_mercury_position_endpoint_missing_field(self, client):
        """Test /api/v1/mercury-position endpoint with missing required field"""
        response = client.post(
            "/api/v1/mercury-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 40.7128
                # Missing longitude
            }
        )

        assert response.status_code == 422  # Validation error

    def test_mercury_position_endpoint_invalid_latitude(self, client):
        """Test /api/v1/mercury-position endpoint with invalid latitude"""
        response = client.post(
            "/api/v1/mercury-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 91.0,  # Invalid
                "longitude": -74.0060
            }
        )

        assert response.status_code == 422

    def test_mercury_position_endpoint_default_elevation(self, client):
        """Test /api/v1/mercury-position endpoint uses default elevation"""
        response = client.post(
            "/api/v1/mercury-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060
                # No elevation specified
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["location"]["elevation"] == 0.0

    def test_mercury_position_endpoint_default_time(self, client):
        """Test /api/v1/mercury-position endpoint requires explicit time"""
        response = client.post(
            "/api/v1/mercury-position",
            json={
                "date": "2026-06-01",
                # No time specified
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        )

        # Time is required, so this should fail validation
        assert response.status_code == 422

    def test_mercury_position_endpoint_response_structure(self, client):
        """Test /api/v1/mercury-position endpoint response has correct structure"""
        response = client.post(
            "/api/v1/mercury-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Check all required response fields
        required_fields = [
            "altitude", "azimuth", "is_visible", "illumination",
            "phase_angle", "phase_name", "sun_separation",
            "naked_eye_visible", "julian_date", "input_datetime", "location"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_mercury_position_endpoint_various_dates(self, client):
        """Test /api/v1/mercury-position endpoint with various dates"""
        dates_times = [
            ("2026-01-01", "12:00:00"),
            ("2026-03-21", "09:30:00"),  # Vernal equinox
            ("2026-06-21", "18:00:00"),  # Summer solstice
            ("2026-09-23", "12:00:00"),  # Autumnal equinox
            ("2026-12-21", "00:00:00"),  # Winter solstice
        ]

        for date_str, time_str in dates_times:
            response = client.post(
                "/api/v1/mercury-position",
                json={
                    "date": date_str,
                    "time": time_str,
                    "latitude": 40.7128,
                    "longitude": -74.0060
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert 0.0 <= data["illumination"] <= 1.0


class TestMercuryEphemerisAccuracy:
    """
    Cross-validation of Mercury's computed position against JPL Horizons DE441
    to confirm relativistic (GR) corrections are being applied.

    GR Background
    -------------
    Mercury's perihelion precesses ~574 arcseconds/century in total, of which
    43.0 arcseconds/century is due to General Relativity — the anomalous advance
    that Einstein's GR famously explained in 1915. A purely Newtonian/Keplerian
    propagator would accumulate an increasing positional error from any fixed epoch:

        10 years from J2000:  43.0 × 10/100 =  4.3 arcseconds
        26 years from J2000:  43.0 × 26/100 = 11.2 arcseconds
       100 years from J2000:  43.0           = 43.0 arcseconds

    Reference Data
    --------------
    JPL Horizons DE441 (https://ssd.jpl.nasa.gov/horizons/), retrieved 2026-06-10.
    Settings: COMMAND='199' (Mercury), CENTER='500@399' (geocentric), EPHEM_TYPE=OBSERVER.
    - QUANTITIES='1': Astrometric ICRF RA/Dec (light-time corrected, no stellar aberration)
    DE441 solves full GR equations of motion, includes gravitational light deflection
    and light-time corrections (no atmospheric refraction).

    Coordinate Frame Note
    ---------------------
    astropy's get_body("mercury", time) returns GCRS (geocentric, apparent, including
    stellar aberration). Horizons QUANTITIES='1' is the astrometric position (no stellar
    aberration), in the same ICRF/J2000 frame. For Mercury near RA~270° observed in
    January, stellar aberration produces a ~20-22" constant offset predominantly in RA.

    This offset is ~20" for all January dates regardless of year, because Earth's orbital
    velocity direction relative to Mercury is nearly the same each January. This means
    it does NOT accumulate over time and is NOT related to GR.

    Test Strategy — GR Detection
    -----------------------------
    Since stellar aberration is constant for same-season dates, comparing the CHANGE
    in the offset between J2000 (2000-01-01) and 2026 (2026-01-01) cancels it out.
    Only GR drift would cause the offset to grow between these same-season dates:

      With GR (astropy DE430/ERFA):
        offset at J2000 ≈ 20.4"   (stellar aberration only)
        offset at 2026  ≈ 20.3"   (stellar aberration, GR correctly applied)
        change ≈ 0.1"              ← passes 5" tolerance

      Without GR (hypothetical Newtonian propagator from J2000 elements):
        offset at J2000 ≈ 20.4"   (same; calibrated to J2000 epoch)
        offset at 2026  ≈ 31.5"   (stellar aberration + 11.2" accumulated GR drift)
        change ≈ 11.1"             ← FAILS 5" tolerance
    """

    # Angular tolerance for the GR drift detection test (arcseconds)
    # Must be LESS than the expected GR drift from J2000 to 2026 (11.2") to be meaningful
    GR_DRIFT_TOLERANCE_ARCSEC = 5.0

    # Sanity-check tolerance for absolute positions (arcseconds)
    # Set to accommodate the known ~20-22" stellar aberration offset between
    # astropy GCRS (apparent) and Horizons Q=1 (astrometric ICRF)
    ABSOLUTE_TOLERANCE_ARCSEC = 25.0

    # JPL Horizons DE441 geocentric ASTROMETRIC ICRF positions (QUANTITIES='1')
    # No stellar aberration; light-time corrected. Retrieved 2026-06-10.
    # https://ssd.jpl.nasa.gov/horizons/
    HORIZONS_ASTROMETRIC = {
        "2000-01-01T12:00:00": {"ra_deg": 272.08522, "dec_deg": -24.42038},
        "2010-01-01T12:00:00": {"ra_deg": 289.59622, "dec_deg": -20.40631},
        "2026-01-01T12:00:00": {"ra_deg": 268.96622, "dec_deg": -24.05733},
    }

    def _angular_separation_arcsec(self, ra1, dec1, ra2, dec2):
        """Angular separation in arcseconds via the haversine formula."""
        import math
        ra1_r, dec1_r = math.radians(ra1), math.radians(dec1)
        ra2_r, dec2_r = math.radians(ra2), math.radians(dec2)
        d_ra = ra2_r - ra1_r
        d_dec = dec2_r - dec1_r
        a = (math.sin(d_dec / 2) ** 2
             + math.cos(dec1_r) * math.cos(dec2_r) * math.sin(d_ra / 2) ** 2)
        return math.degrees(2 * math.asin(math.sqrt(a))) * 3600.0

    @pytest.mark.parametrize(
        "datetime_utc",
        ["2000-01-01T12:00:00", "2010-01-01T12:00:00", "2026-01-01T12:00:00"],
    )
    def test_mercury_absolute_position_within_25_arcseconds_of_horizons(self, datetime_utc):
        """
        Ephemeris baseline validation: astropy's Mercury position (apparent GCRS) should be within
        25 arcseconds of JPL Horizons astrometric ICRF at each test epoch.

        NOTE: This test validates astropy's bundled ephemeris (DE441) behavior directly,
        not the application's calculate_mercury_position(). Failures here indicate
        astropy/ephemeris data changes, not regressions in our code. Failures may occur
        across astropy/ephemeris updates without code changes.

        The expected offset is ~20-22" due to stellar aberration (not GR drift).
        A separation above 25" indicates a serious ephemeris compatibility issue.
        """
        from astropy.coordinates import get_body
        from astropy.time import Time

        ref = self.HORIZONS_ASTROMETRIC[datetime_utc]
        mercury_gcrs = get_body("mercury", Time(datetime_utc, format="isot", scale="utc"))
        ra = float(mercury_gcrs.ra.degree)
        dec = float(mercury_gcrs.dec.degree)

        sep_arcsec = self._angular_separation_arcsec(ra, dec, ref["ra_deg"], ref["dec_deg"])

        assert sep_arcsec < self.ABSOLUTE_TOLERANCE_ARCSEC, (
            f"{datetime_utc}: separation {sep_arcsec:.2f}\" from Horizons DE441 exceeds "
            f"{self.ABSOLUTE_TOLERANCE_ARCSEC}\" tolerance. "
            f"Computed RA={ra:.5f}°, Dec={dec:.5f}° (GCRS apparent). "
            f"Horizons DE441: RA={ref['ra_deg']}°, Dec={ref['dec_deg']}° (astrometric ICRF). "
            f"Note: ~20\" offset is expected from stellar aberration."
        )

    def test_mercury_gr_drift_not_detectable_between_2000_and_2026(self):
        """
        Primary GR detection test.

        The CHANGE in separation between astropy and Horizons Q=1 from J2000 (2000-01-01)
        to 2026 (2026-01-01) must be < 5 arcseconds. Because both dates are in January,
        stellar aberration is approximately constant and cancels in the difference.
        Only accumulated GR drift (or its absence) affects the change.

        With relativistic ephemeris (astropy DE430/ERFA):
            change ≈ 0.1"   → passes

        With a hypothetical Newtonian propagator from J2000 orbital elements:
            change ≈ 11.2"  → FAILS (43.0"/century × 26 years / 100)

        This test would therefore FAIL if get_body("mercury") were replaced with a
        purely Newtonian/Keplerian orbit that ignores perihelion precession from GR.
        """
        from astropy.coordinates import get_body
        from astropy.time import Time

        t_j2000 = Time("2000-01-01T12:00:00", format="isot", scale="utc")
        t_2026 = Time("2026-01-01T12:00:00", format="isot", scale="utc")

        m_j2000 = get_body("mercury", t_j2000)
        m_2026 = get_body("mercury", t_2026)

        ref_j2000 = self.HORIZONS_ASTROMETRIC["2000-01-01T12:00:00"]
        ref_2026 = self.HORIZONS_ASTROMETRIC["2026-01-01T12:00:00"]

        sep_j2000 = self._angular_separation_arcsec(
            float(m_j2000.ra.degree), float(m_j2000.dec.degree),
            ref_j2000["ra_deg"], ref_j2000["dec_deg"]
        )
        sep_2026 = self._angular_separation_arcsec(
            float(m_2026.ra.degree), float(m_2026.dec.degree),
            ref_2026["ra_deg"], ref_2026["dec_deg"]
        )

        # Stellar aberration (~20") cancels; only GR drift changes this delta
        sep_change = abs(sep_2026 - sep_j2000)

        assert sep_change < self.GR_DRIFT_TOLERANCE_ARCSEC, (
            f"Separation-from-Horizons changed by {sep_change:.2f}\" between J2000 and 2026 "
            f"(J2000: {sep_j2000:.2f}\", 2026: {sep_2026:.2f}\"). "
            f"Tolerance is {self.GR_DRIFT_TOLERANCE_ARCSEC}\". "
            f"A Newtonian propagator would show ~11.2\" change (43.0\"/century × 26 yrs). "
            f"GR corrections appear to be absent from Mercury's ephemeris."
        )

    def test_mercury_gr_drift_at_2026_exceeds_gr_detection_tolerance(self):
        """
        Guard test: confirm that the expected Newtonian drift at the 2026 epoch
        (11.2 arcseconds over 26 years) exceeds GR_DRIFT_TOLERANCE_ARCSEC.
        If this fails, lower GR_DRIFT_TOLERANCE_ARCSEC to preserve the GR-detection value.
        """
        GR_ARCSEC_PER_CENTURY = 43.0
        years_from_j2000 = 26.0
        expected_newtonian_drift = GR_ARCSEC_PER_CENTURY * years_from_j2000 / 100.0

        assert expected_newtonian_drift > self.GR_DRIFT_TOLERANCE_ARCSEC, (
            f"Expected Newtonian drift over {years_from_j2000} years "
            f"({expected_newtonian_drift:.2f}\") does not exceed GR_DRIFT_TOLERANCE_ARCSEC "
            f"({self.GR_DRIFT_TOLERANCE_ARCSEC}\"). "
            "The GR detection test is no longer sensitive — lower the tolerance."
        )


@pytest.fixture
def client():
    """FastAPI test client fixture"""
    from fastapi.testclient import TestClient
    from api.main import app

    return TestClient(app)
