"""
Integration tests for Venus API endpoints (/venus-position)
"""
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


class TestVenusPositionEndpointBasic:
    """Basic tests for /venus-position endpoint."""

    def test_venus_position_valid_request(self):
        """Test valid Venus position request."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
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
        assert "sun_separation" in data
        assert "naked_eye_visible" in data
        assert "illumination" in data
        assert "phase_angle" in data
        assert "phase_name" in data
        assert "julian_date" in data
        assert "input_datetime" in data
        assert "location" in data

    def test_venus_position_valid_response_types(self):
        """Test that response types are correct."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
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
        assert isinstance(data["sun_separation"], (int, float))
        assert isinstance(data["naked_eye_visible"], bool)
        assert isinstance(data["illumination"], (int, float))
        assert isinstance(data["phase_angle"], (int, float))
        assert isinstance(data["phase_name"], str)
        assert isinstance(data["julian_date"], (int, float))

    def test_venus_position_response_ranges(self):
        """Test that response values are in valid ranges."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
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
        assert data["sun_separation"] >= 0
        assert 0.0 <= data["illumination"] <= 1.0
        assert 0.0 <= data["phase_angle"] < 360.0

    def test_venus_position_without_elevation(self):
        """Test Venus position request without elevation (should default to 0)."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["location"]["elevation"] == 0.0


class TestVenusPositionLocations:
    """Tests for Venus position at different locations."""

    def test_venus_position_equator(self):
        """Test Venus position at equator."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 0.0,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "altitude" in data

    def test_venus_position_new_york(self):
        """Test Venus position in New York City."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 10.0,
            },
        )

        assert response.status_code == 200
        assert "altitude" in response.json()

    def test_venus_position_sydney(self):
        """Test Venus position in Sydney, Australia."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": -33.8688,
                "longitude": 151.2093,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        assert "altitude" in response.json()

    def test_venus_position_north_pole(self):
        """Test Venus position at North Pole."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 90.0,
                "longitude": 0.0,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        assert "altitude" in response.json()

    def test_venus_position_south_pole(self):
        """Test Venus position at South Pole."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": -90.0,
                "longitude": 0.0,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        assert "altitude" in response.json()

    def test_venus_position_tokyo(self):
        """Test Venus position in Tokyo, Japan."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 35.6762,
                "longitude": 139.6503,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        assert "altitude" in response.json()

    def test_venus_position_london(self):
        """Test Venus position in London, UK."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 51.5074,
                "longitude": -0.1278,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        assert "altitude" in response.json()


class TestVenusPositionPhase:
    """Tests for Venus phase information in response."""

    def test_venus_phase_name_valid(self):
        """Test that Venus phase name is one of valid phases."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["phase_name"] in ["New", "Crescent", "Quarter", "Gibbous", "Full"]

    def test_venus_illumination_range(self):
        """Test that Venus illumination is in valid range."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert 0.0 <= data["illumination"] <= 1.0

    def test_venus_phase_angle_range(self):
        """Test that Venus phase angle is in valid range."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert 0.0 <= data["phase_angle"] < 360.0

    def test_venus_phases_throughout_year(self):
        """Test that Venus shows different phases throughout year."""
        phase_names = set()

        for month in range(1, 13):
            response = client.post(
                "/api/v1/venus-position",
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

        # Venus should show multiple phase names throughout year
        assert len(phase_names) > 1


class TestVenusPositionVisibility:
    """Tests for Venus visibility information."""

    def test_venus_is_visible_when_above_horizon(self):
        """Test that is_visible correlates with positive altitude."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "20:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        data = response.json()

        if data["altitude"] > 0:
            assert data["is_visible"] is True
        else:
            assert data["is_visible"] is False

    def test_venus_sun_separation_exists(self):
        """Test that sun_separation is provided."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["sun_separation"] >= 0

    def test_venus_naked_eye_visible_requires_separation(self):
        """Test that naked_eye_visible requires sufficient sun separation."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "20:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # If altitude <= 0, should not be naked eye visible
        if data["altitude"] <= 0:
            assert data["naked_eye_visible"] is False

        # If sun_separation < 10, should not be naked eye visible
        if data["sun_separation"] < 10:
            assert data["naked_eye_visible"] is False


class TestVenusPositionInputValidation:
    """Tests for input validation."""

    def test_venus_latitude_too_high(self):
        """Test that latitude > 90 returns validation error."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 91.0,
                "longitude": 0.0,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 422

    def test_venus_latitude_too_low(self):
        """Test that latitude < -90 returns validation error."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": -91.0,
                "longitude": 0.0,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 422

    def test_venus_longitude_too_high(self):
        """Test that longitude > 180 returns validation error."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 181.0,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 422

    def test_venus_longitude_too_low(self):
        """Test that longitude < -180 returns validation error."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": -181.0,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 422

    def test_venus_missing_required_date(self):
        """Test that missing date returns validation error."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 422

    def test_venus_missing_required_time(self):
        """Test that missing time returns validation error."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 422

    def test_venus_missing_required_latitude(self):
        """Test that missing latitude returns validation error."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "longitude": -74.0060,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 422

    def test_venus_missing_required_longitude(self):
        """Test that missing longitude returns validation error."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 40.7128,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 422

    def test_venus_invalid_date_format(self):
        """Test that invalid date format returns error."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "not-a-date",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 400

    def test_venus_invalid_time_format(self):
        """Test that invalid time format returns error."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "not-a-time",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 400

    def test_venus_latitude_boundary_90(self):
        """Test that latitude = 90 is valid."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 90.0,
                "longitude": 0.0,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200

    def test_venus_latitude_boundary_minus_90(self):
        """Test that latitude = -90 is valid."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": -90.0,
                "longitude": 0.0,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200

    def test_venus_longitude_boundary_180(self):
        """Test that longitude = 180 is valid."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 180.0,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200

    def test_venus_longitude_boundary_minus_180(self):
        """Test that longitude = -180 is valid."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": -180.0,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200


class TestVenusPositionEdgeCases:
    """Tests for edge cases."""

    def test_venus_midnight_utc(self):
        """Test Venus position at midnight UTC."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "00:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        assert response.json()["input_datetime"] == "2026-06-01T00:00:00Z"

    def test_venus_end_of_day(self):
        """Test Venus position at end of day."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "23:59:59",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        assert response.json()["input_datetime"] == "2026-06-01T23:59:59Z"

    def test_venus_leap_year_february_29(self):
        """Test Venus position on leap year February 29."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2024-02-29",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200

    def test_venus_high_elevation(self):
        """Test Venus position at high elevation."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 8848.0,  # Mount Everest height
            },
        )

        assert response.status_code == 200

    def test_venus_zero_elevation(self):
        """Test Venus position at sea level."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        assert response.json()["location"]["elevation"] == 0.0


class TestVenusPositionConsistency:
    """Tests for consistency across requests."""

    def test_venus_same_request_returns_same_result(self):
        """Test that same request returns same result."""
        request_data = {
            "date": "2026-06-01",
            "time": "12:00:00",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "elevation": 10.0,
        }

        response1 = client.post("/api/v1/venus-position", json=request_data)
        response2 = client.post("/api/v1/venus-position", json=request_data)

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json() == response2.json()

    def test_venus_location_dict_preserved_in_response(self):
        """Test that location information is preserved in response."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 10.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["location"]["latitude"] == 40.7128
        assert data["location"]["longitude"] == -74.0060
        assert data["location"]["elevation"] == 10.0


class TestVenusPositionResponseStructure:
    """Tests for response structure and format."""

    def test_venus_response_has_all_required_fields(self):
        """Test that response has all required fields."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        data = response.json()

        required_fields = [
            "altitude",
            "azimuth",
            "is_visible",
            "sun_separation",
            "naked_eye_visible",
            "illumination",
            "phase_angle",
            "phase_name",
            "julian_date",
            "input_datetime",
            "location",
        ]

        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_venus_location_has_required_fields(self):
        """Test that location dict has required fields."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 10.0,
            },
        )

        assert response.status_code == 200
        location = response.json()["location"]

        assert "latitude" in location
        assert "longitude" in location
        assert "elevation" in location

    def test_venus_input_datetime_format(self):
        """Test that input_datetime is in ISO format."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 0.0,
                "elevation": 0.0,
            },
        )

        assert response.status_code == 200
        input_datetime = response.json()["input_datetime"]
        assert "T" in input_datetime  # ISO format has T separator


class TestVenusPositionErrorHandling:
    """Tests for error handling."""

    def test_venus_malformed_json(self):
        """Test malformed JSON handling."""
        response = client.post(
            "/api/v1/venus-position",
            content="not json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_venus_missing_all_fields(self):
        """Test request with no fields."""
        response = client.post(
            "/api/v1/venus-position",
            json={},
        )

        assert response.status_code == 422

    def test_venus_wrong_method_get(self):
        """Test that GET method is not allowed."""
        response = client.get("/api/v1/venus-position")

        assert response.status_code == 405  # Method Not Allowed

    def test_venus_wrong_method_put(self):
        """Test that PUT method is not allowed."""
        response = client.put(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-01",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 0.0,
            },
        )

        assert response.status_code == 405

    def test_venus_value_error_handling(self):
        """Test ValueError exception handling in Venus endpoint."""
        from unittest.mock import patch
        
        with patch("api.routes.calculate_venus_position") as mock_calc:
            mock_calc.side_effect = ValueError("Test calculation error")
            
            response = client.post(
                "/api/v1/venus-position",
                json={
                    "date": "2026-06-01",
                    "time": "12:00:00",
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                },
            )
            
            assert response.status_code == 400
            assert "Invalid input" in response.json()["detail"]

    def test_venus_unexpected_error_handling(self):
        """Test unexpected exception handling in Venus endpoint."""
        from unittest.mock import patch
        
        with patch("api.routes.calculate_venus_position") as mock_calc:
            mock_calc.side_effect = RuntimeError("Unexpected error")
            
            response = client.post(
                "/api/v1/venus-position",
                json={
                    "date": "2026-06-01",
                    "time": "12:00:00",
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                },
            )
            
            assert response.status_code == 500
            assert "Error calculating Venus position" in response.json()["detail"]
