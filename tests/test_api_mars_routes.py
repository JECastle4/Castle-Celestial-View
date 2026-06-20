"""
Integration tests for Mars API endpoints (/mars-position)
"""
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


class TestMarsPositionEndpointBasic:
    """Basic tests for /mars-position endpoint."""

    def test_mars_position_valid_request(self):
        """Test valid Mars position request."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 10.0,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "altitude" in data
        assert "azimuth" in data
        assert "is_visible" in data
        assert "illumination" in data
        assert "phase_angle" in data
        assert "phase_name" in data
        assert "retrograde_status" in data
        assert "julian_date" in data
        assert "input_datetime" in data
        assert "location" in data

    def test_mars_position_valid_response_types(self):
        """Test that response types are correct."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 0.0,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["altitude"], (int, float))
        assert isinstance(data["azimuth"], (int, float))
        assert isinstance(data["is_visible"], bool)
        assert isinstance(data["illumination"], (int, float))
        assert isinstance(data["phase_angle"], (int, float))
        assert isinstance(data["phase_name"], str)
        assert isinstance(data["retrograde_status"], str)
        assert isinstance(data["julian_date"], (int, float))

    def test_mars_position_response_ranges(self):
        """Test that response values are in valid ranges."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 10.0,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Check value ranges
        assert -90 <= data["altitude"] <= 90
        assert 0 <= data["azimuth"] <= 360
        assert 0.5 <= data["illumination"] <= 1.0  # Mars: superior planet
        assert 0.0 <= data["phase_angle"] < 360.0

    def test_mars_position_without_elevation(self):
        """Test Mars position request without elevation (should default to 0)."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["location"]["elevation"] == 0.0


class TestMarsPositionEndpointLocations:
    """Tests for Mars position at various locations."""

    def test_mars_position_equator(self):
        """Test Mars position at equator."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 0.0,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        assert "altitude" in response.json()

    def test_mars_position_north_pole(self):
        """Test Mars position at North Pole."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 90.0,
                "longitude": 0.0,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        assert "altitude" in response.json()

    def test_mars_position_south_pole(self):
        """Test Mars position at South Pole."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": -90.0,
                "longitude": 0.0,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        assert "altitude" in response.json()

    def test_mars_position_sydney(self):
        """Test Mars position in Sydney, Australia (southern hemisphere)."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": -33.8688,
                "longitude": 151.2093,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        assert "altitude" in response.json()

    def test_mars_position_tokyo(self):
        """Test Mars position in Tokyo."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 35.6762,
                "longitude": 139.6503,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        assert "altitude" in response.json()

    def test_mars_position_london(self):
        """Test Mars position in London, UK."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 51.5074,
                "longitude": -0.1278,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        assert "altitude" in response.json()


class TestMarsPositionPhase:
    """Tests for Mars phase information in response."""

    def test_mars_phase_name_valid(self):
        """Test that Mars phase name is one of valid phases."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["phase_name"] in ["Full", "Gibbous", "Crescent"]

    def test_mars_illumination_range(self):
        """Test that Mars illumination is in valid range."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert 0.5 <= data["illumination"] <= 1.0

    def test_mars_phase_angle_range(self):
        """Test that Mars phase angle is in valid range."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert 0.0 <= data["phase_angle"] < 360.0

    def test_mars_retrograde_status_valid(self):
        """Test that retrograde status is valid."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 0.0,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["retrograde_status"] in ["prograde", "retrograde"]

    def test_mars_phases_throughout_year(self):
        """Test that Mars phase calculation is consistent throughout year."""
        # Note: As a superior planet, Mars may remain in same phase for extended periods
        # especially near opposition. Just verify phases are valid.
        phase_names = set()

        for month in range(1, 13):
            response = client.post(
                "/api/v1/mars-position",
                json={
                    "date": f"2026-{month:02d}-15",
                    "time": "12:00:00",
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "elevation": 0.0,
                },
            )

            assert response.status_code == 200
            phase_names.add(response.json()["phase_name"])

        # All phase names should be valid (even if only one phase throughout 2026)
        assert all(name in ["Full", "Gibbous", "Crescent"] for name in phase_names)


class TestMarsPositionTimes:
    """Tests for different times."""

    def test_mars_position_midnight(self):
        """Test Mars position at midnight."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "00:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        assert "altitude" in response.json()

    def test_mars_position_noon(self):
        """Test Mars position at noon."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        assert "altitude" in response.json()

    def test_mars_position_near_midnight(self):
        """Test Mars position near midnight."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "23:59:59",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        assert "altitude" in response.json()


class TestMarsPositionDates:
    """Tests for different dates."""

    def test_mars_position_new_year(self):
        """Test Mars position on New Year's Day."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-01-01",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 0.0,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        assert "altitude" in response.json()

    def test_mars_position_year_end(self):
        """Test Mars position on year end."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-12-31",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 0.0,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        assert "altitude" in response.json()

    def test_mars_position_leap_day(self):
        """Test Mars position on leap day (2024 is leap year)."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2024-02-29",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 0.0,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        assert "altitude" in response.json()


class TestMarsPositionErrorHandling:
    """Tests for error handling."""

    def test_mars_malformed_json(self):
        """Test malformed JSON handling."""
        response = client.post(
            "/api/v1/mars-position",
            content="not json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_mars_missing_date(self):
        """Test request with missing date field."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 0.0,
            },
        )

        assert response.status_code == 422

    def test_mars_missing_time(self):
        """Test request with missing time field."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "latitude": 0.0,
                "longitude": 0.0,
            },
        )

        assert response.status_code == 422

    def test_mars_missing_latitude(self):
        """Test request with missing latitude field."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "longitude": 0.0,
            },
        )

        assert response.status_code == 422

    def test_mars_missing_longitude(self):
        """Test request with missing longitude field."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 0.0,
            },
        )

        assert response.status_code == 422

    def test_mars_missing_all_fields(self):
        """Test request with no fields."""
        response = client.post(
            "/api/v1/mars-position",
            json={},
        )

        assert response.status_code == 422

    def test_mars_invalid_latitude_over_90(self):
        """Test invalid latitude > 90."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 91.0,
                "longitude": 0.0,
            },
        )

        assert response.status_code == 422

    def test_mars_invalid_latitude_under_minus_90(self):
        """Test invalid latitude < -90."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": -91.0,
                "longitude": 0.0,
            },
        )

        assert response.status_code == 422

    def test_mars_invalid_longitude_over_180(self):
        """Test invalid longitude > 180."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 181.0,
            },
        )

        assert response.status_code == 422

    def test_mars_invalid_longitude_under_minus_180(self):
        """Test invalid longitude < -180."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": -181.0,
            },
        )

        assert response.status_code == 422

    def test_mars_wrong_method_get(self):
        """Test that GET method is not allowed."""
        response = client.get("/api/v1/mars-position")

        assert response.status_code == 405  # Method Not Allowed

    def test_mars_wrong_method_put(self):
        """Test that PUT method is not allowed."""
        response = client.put(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 0.0,
            },
        )

        assert response.status_code == 405

    def test_mars_value_error_handling(self):
        """Test ValueError exception handling in Mars endpoint."""
        from unittest.mock import patch

        with patch("api.routes.calculate_mars_position") as mock_calc:
            mock_calc.side_effect = ValueError("Test calculation error")

            response = client.post(
                "/api/v1/mars-position",
                json={
                    "date": "2026-06-18",
                    "time": "12:00:00",
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                },
            )

            assert response.status_code == 400
            assert "Invalid input" in response.json()["detail"]

    def test_mars_unexpected_error_handling(self):
        """Test unexpected exception handling in Mars endpoint."""
        from unittest.mock import patch

        with patch("api.routes.calculate_mars_position") as mock_calc:
            mock_calc.side_effect = RuntimeError("Unexpected error")

            response = client.post(
                "/api/v1/mars-position",
                json={
                    "date": "2026-06-18",
                    "time": "12:00:00",
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                },
            )

            assert response.status_code == 500
            assert "Error calculating Mars position" in response.json()["detail"]


class TestMarsPositionLocalization:
    """Tests for localization support."""

    def test_mars_position_with_english_locale(self):
        """Test Mars position with English locale."""
        response = client.post(
            "/api/v1/mars-position?lang=en",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["phase_name"] in ["Full", "Gibbous", "Crescent"]

    def test_mars_position_with_en_us_locale(self):
        """Test Mars position with en-US locale."""
        response = client.post(
            "/api/v1/mars-position?lang=en-US",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["phase_name"] in ["Full", "Gibbous", "Crescent"]

    def test_mars_position_default_locale(self):
        """Test Mars position uses default locale when none specified."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        # Default locale should return English phase names
        assert data["phase_name"] in ["Full", "Gibbous", "Crescent"]


class TestMarsLocationValidation:
    """Tests for location data in response."""

    def test_mars_location_data_correct(self):
        """Test that location data in response matches input."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 123.45,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["location"]["latitude"] == 40.7128
        assert data["location"]["longitude"] == -74.0060
        assert data["location"]["elevation"] == 123.45

    def test_mars_input_datetime_preserved(self):
        """Test that input datetime is preserved in response."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 0.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "2026-06-18T12:00:00Z" in data["input_datetime"]
