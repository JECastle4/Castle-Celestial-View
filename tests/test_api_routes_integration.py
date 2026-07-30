"""Integration tests for API routes error handling.

Tests the HTTP exception handlers for all planetary position endpoints.
These tests verify that invalid inputs produce proper HTTP error responses:
- 422: Pydantic validation errors (invalid lat/lon, invalid data types)
- 400: Application-level validation errors (invalid date/time values)
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app


client = TestClient(app)


class TestVenusRouteErrors:
    """Integration tests for Venus endpoint error handling."""

    def test_venus_pydantic_invalid_latitude_too_high(self):
        """Test Venus endpoint with latitude > 90 (Pydantic validation)."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 91.0,
                "longitude": 0.0,
                "elevation": 0.0
            }
        )
        assert response.status_code == 422

    def test_venus_pydantic_invalid_latitude_too_low(self):
        """Test Venus endpoint with latitude < -90 (Pydantic validation)."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": -91.0,
                "longitude": 0.0,
                "elevation": 0.0
            }
        )
        assert response.status_code == 422

    def test_venus_pydantic_invalid_longitude_too_high(self):
        """Test Venus endpoint with longitude > 180 (Pydantic validation)."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 181.0,
                "elevation": 0.0
            }
        )
        assert response.status_code == 422

    def test_venus_pydantic_invalid_longitude_too_low(self):
        """Test Venus endpoint with longitude < -180 (Pydantic validation)."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": -181.0,
                "elevation": 0.0
            }
        )
        assert response.status_code == 422

    def test_venus_app_invalid_date_format(self):
        """Test Venus endpoint with invalid date format (app validation)."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-13-45",  # Invalid date: month 13, day 45
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 0.0,
                "elevation": 0.0
            }
        )
        assert response.status_code == 400
        assert "Invalid input" in response.json()["detail"]

    def test_venus_app_invalid_time_format(self):
        """Test Venus endpoint with invalid time format (app validation)."""
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2026-06-18",
                "time": "25:99:99",  # Invalid time: hour 25, minute 99, second 99
                "latitude": 0.0,
                "longitude": 0.0,
                "elevation": 0.0
            }
        )
        assert response.status_code == 400
        assert "Invalid input" in response.json()["detail"]


class TestMercuryRouteErrors:
    """Integration tests for Mercury endpoint error handling."""

    def test_mercury_pydantic_invalid_latitude(self):
        """Test Mercury endpoint with invalid latitude (Pydantic validation)."""
        response = client.post(
            "/api/v1/mercury-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 95.0,
                "longitude": 0.0,
                "elevation": 0.0
            }
        )
        assert response.status_code == 422

    def test_mercury_pydantic_invalid_longitude(self):
        """Test Mercury endpoint with invalid longitude (Pydantic validation)."""
        response = client.post(
            "/api/v1/mercury-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 200.0,
                "elevation": 0.0
            }
        )
        assert response.status_code == 422

    def test_mercury_app_invalid_date(self):
        """Test Mercury endpoint with invalid date (app validation)."""
        response = client.post(
            "/api/v1/mercury-position",
            json={
                "date": "2026-13-45",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 0.0,
                "elevation": 0.0
            }
        )
        assert response.status_code == 400


class TestMarsRouteErrors:
    """Integration tests for Mars endpoint error handling."""

    def test_mars_pydantic_invalid_latitude(self):
        """Test Mars endpoint with invalid latitude (Pydantic validation)."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": -95.0,
                "longitude": 0.0,
                "elevation": 0.0
            }
        )
        assert response.status_code == 422

    def test_mars_pydantic_invalid_longitude(self):
        """Test Mars endpoint with invalid longitude (Pydantic validation)."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": -200.0,
                "elevation": 0.0
            }
        )
        assert response.status_code == 422

    def test_mars_app_invalid_time(self):
        """Test Mars endpoint with invalid time (app validation)."""
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2026-06-18",
                "time": "26:00:00",
                "latitude": 0.0,
                "longitude": 0.0,
                "elevation": 0.0
            }
        )
        assert response.status_code == 400


class TestJupiterRouteErrors:
    """Integration tests for Jupiter endpoint error handling."""

    def test_jupiter_pydantic_invalid_latitude(self):
        """Test Jupiter endpoint with invalid latitude (Pydantic validation)."""
        response = client.post(
            "/api/v1/jupiter-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 100.0,
                "longitude": 0.0,
                "elevation": 0.0
            }
        )
        assert response.status_code == 422

    def test_jupiter_pydantic_invalid_longitude(self):
        """Test Jupiter endpoint with invalid longitude (Pydantic validation)."""
        response = client.post(
            "/api/v1/jupiter-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 210.0,
                "elevation": 0.0
            }
        )
        assert response.status_code == 422

    def test_jupiter_app_invalid_date(self):
        """Test Jupiter endpoint with invalid date (app validation)."""
        response = client.post(
            "/api/v1/jupiter-position",
            json={
                "date": "2026-02-30",  # Invalid: Feb 30 doesn't exist
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 0.0,
                "elevation": 0.0
            }
        )
        assert response.status_code == 400


class TestSaturnRouteErrors:
    """Integration tests for Saturn endpoint error handling."""

    def test_saturn_pydantic_invalid_latitude(self):
        """Test Saturn endpoint with invalid latitude (Pydantic validation)."""
        response = client.post(
            "/api/v1/saturn-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 100.0,
                "longitude": 0.0,
                "elevation": 0.0
            }
        )
        assert response.status_code == 422

    def test_saturn_pydantic_invalid_longitude(self):
        """Test Saturn endpoint with invalid longitude (Pydantic validation)."""
        response = client.post(
            "/api/v1/saturn-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 210.0,
                "elevation": 0.0
            }
        )
        assert response.status_code == 422

    def test_saturn_app_invalid_time(self):
        """Test Saturn endpoint with invalid time (app validation)."""
        response = client.post(
            "/api/v1/saturn-position",
            json={
                "date": "2026-06-18",
                "time": "12:60:60",
                "latitude": 0.0,
                "longitude": 0.0,
                "elevation": 0.0
            }
        )
        assert response.status_code == 400


class TestUranusRouteErrors:
    """Integration tests for Uranus endpoint error handling."""

    def test_uranus_pydantic_invalid_latitude(self):
        """Test Uranus endpoint with invalid latitude (Pydantic validation)."""
        response = client.post(
            "/api/v1/uranus-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 100.0,
                "longitude": 0.0,
                "elevation": 0.0
            }
        )
        assert response.status_code == 422

    def test_uranus_pydantic_invalid_longitude(self):
        """Test Uranus endpoint with invalid longitude (Pydantic validation)."""
        response = client.post(
            "/api/v1/uranus-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 210.0,
                "elevation": 0.0
            }
        )
        assert response.status_code == 422

    def test_uranus_app_invalid_date(self):
        """Test Uranus endpoint with invalid date (app validation)."""
        response = client.post(
            "/api/v1/uranus-position",
            json={
                "date": "2026-11-31",  # Invalid: Nov 31 doesn't exist
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 0.0,
                "elevation": 0.0
            }
        )
        assert response.status_code == 400


class TestNeptuneRouteErrors:
    """Integration tests for Neptune endpoint error handling."""

    def test_neptune_pydantic_invalid_latitude(self):
        """Test Neptune endpoint with invalid latitude (Pydantic validation)."""
        response = client.post(
            "/api/v1/neptune-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 100.0,
                "longitude": 0.0,
                "elevation": 0.0
            }
        )
        assert response.status_code == 422

    def test_neptune_pydantic_invalid_longitude(self):
        """Test Neptune endpoint with invalid longitude (Pydantic validation)."""
        response = client.post(
            "/api/v1/neptune-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 210.0,
                "elevation": 0.0
            }
        )
        assert response.status_code == 422

    def test_neptune_app_invalid_time(self):
        """Test Neptune endpoint with invalid time (app validation)."""
        response = client.post(
            "/api/v1/neptune-position",
            json={
                "date": "2026-06-18",
                "time": "23:60:00",
                "latitude": 0.0,
                "longitude": 0.0,
                "elevation": 0.0
            }
        )
        assert response.status_code == 400


class TestRouteErrorMessages:
    """Test that error messages are informative."""

    def test_pydantic_error_response_format(self):
        """Verify Pydantic validation error response includes proper format."""
        response = client.post(
            "/api/v1/jupiter-position",
            json={
                "date": "2026-06-18",
                "time": "12:00:00",
                "latitude": 200.0,  # Invalid: Pydantic should catch this
                "longitude": 0.0,
                "elevation": 0.0
            }
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_app_error_response_format(self):
        """Verify app-level validation error response includes detail field."""
        response = client.post(
            "/api/v1/jupiter-position",
            json={
                "date": "2026-12-32",  # Invalid date (Dec has 31 days)
                "time": "12:00:00",
                "latitude": 0.0,
                "longitude": 0.0,
                "elevation": 0.0
            }
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)
        assert len(data["detail"]) > 0
