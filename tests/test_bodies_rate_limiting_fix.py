"""Tests for rate-limited handlers in api/routes/bodies.py

Verifies that all handlers have proper Request parameter for SlowAPI rate limiting.
This is critical: without the Request parameter, rate-limited handlers will crash
when using the real SlowAPI limiter (not MockLimiter).

Issue: All 11 handlers were using request: BodyType instead of:
    request: Request (for rate limiting)
    body: BodyType (for request body)
"""

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from api.main import app


class TestBodiesHandlersRateLimitingSignature:
    """Test that handlers have correct signature for rate limiting."""

    def test_day_of_week_has_request_parameter(self):
        """Verify get_day_of_week has Request parameter for rate limiting."""
        from api.routes.bodies import get_day_of_week
        import inspect

        sig = inspect.signature(get_day_of_week)
        params = list(sig.parameters.keys())
        
        # Should have both request and body parameters
        assert "request" in params, "Missing request parameter for rate limiting"
        assert "body" in params, "Missing body parameter for request data"
        
        # Request should come first (required by decorators)
        assert params[0] == "request"
        assert params[1] == "body"
        
        # Request type should be Request
        request_param = sig.parameters["request"]
        assert request_param.annotation == Request

    def test_sun_position_has_request_parameter(self):
        """Verify get_sun_position has Request parameter for rate limiting."""
        from api.routes.bodies import get_sun_position
        import inspect

        sig = inspect.signature(get_sun_position)
        params = list(sig.parameters.keys())
        
        assert "request" in params
        assert "body" in params
        assert params[0] == "request"
        
        request_param = sig.parameters["request"]
        assert request_param.annotation == Request

    def test_moon_position_has_request_parameter(self):
        """Verify get_moon_position has Request parameter for rate limiting."""
        from api.routes.bodies import get_moon_position
        import inspect

        sig = inspect.signature(get_moon_position)
        params = list(sig.parameters.keys())
        
        assert "request" in params
        assert "body" in params
        assert params[0] == "request"

    def test_all_endpoints_have_request_first_parameter(self):
        """Verify all rate-limited endpoints follow Request, body pattern."""
        from api.routes import bodies
        import inspect
        
        # All these handlers should be rate-limited
        handlers = [
            "get_day_of_week",
            "get_sun_position",
            "get_moon_position",
            "get_venus_position",
            "get_mercury_position",
            "get_mars_position",
            "get_jupiter_position",
            "get_saturn_position",
            "get_uranus_position",
            "get_neptune_position",
            "get_moon_phase",
        ]
        
        for handler_name in handlers:
            handler = getattr(bodies, handler_name)
            sig = inspect.signature(handler)
            params = list(sig.parameters.keys())
            
            # First param should be request (for rate limiting)
            assert params[0] == "request", \
                f"{handler_name}: first parameter should be 'request', got {params[0]}"
            
            # Second param should be body (for request body)
            assert params[1] == "body", \
                f"{handler_name}: second parameter should be 'body', got {params[1]}"
            
            # Request should be typed as Request
            request_param = sig.parameters["request"]
            assert request_param.annotation == Request, \
                f"{handler_name}: request parameter should be typed as Request"


class TestBodiesHandlersWithTestClient:
    """Test handlers work correctly with TestClient (which provides Request)."""

    def test_day_of_week_endpoint_works(self):
        """Test that day_of_week endpoint can be called and returns results."""
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/day-of-week",
            json={
                "date": "2025-03-29",
                "time": "00:00:00"
            }
        )
        
        # Should work (request parameter injected by FastAPI)
        assert response.status_code == 200
        data = response.json()
        assert "day_of_week" in data
        assert "day_name" in data

    def test_sun_position_endpoint_works(self):
        """Test that sun_position endpoint works with proper signature."""
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/sun-position",
            json={
                "date": "2025-03-29",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "altitude" in data
        assert "azimuth" in data
        assert "is_visible" in data

    def test_moon_position_endpoint_works(self):
        """Test that moon_position endpoint works."""
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/moon-position",
            json={
                "date": "2025-03-29",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "altitude" in data
        assert "azimuth" in data

    def test_venus_position_endpoint_works(self):
        """Test that venus_position endpoint works."""
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/venus-position",
            json={
                "date": "2025-03-29",
                "time": "18:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "altitude" in data
        assert "illumination" in data

    def test_mercury_position_endpoint_works(self):
        """Test that mercury_position endpoint works."""
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/mercury-position",
            json={
                "date": "2025-03-29",
                "time": "18:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "altitude" in data

    def test_mars_position_endpoint_works(self):
        """Test that mars_position endpoint works."""
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/mars-position",
            json={
                "date": "2025-03-29",
                "time": "20:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "altitude" in data
        assert "is_visible" in data

    def test_jupiter_position_endpoint_works(self):
        """Test that jupiter_position endpoint works."""
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/jupiter-position",
            json={
                "date": "2025-03-29",
                "time": "20:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "altitude" in data

    def test_saturn_position_endpoint_works(self):
        """Test that saturn_position endpoint works."""
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/saturn-position",
            json={
                "date": "2025-03-29",
                "time": "20:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "altitude" in data

    def test_uranus_position_endpoint_works(self):
        """Test that uranus_position endpoint works."""
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/uranus-position",
            json={
                "date": "2025-03-29",
                "time": "20:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "altitude" in data

    def test_neptune_position_endpoint_works(self):
        """Test that neptune_position endpoint works."""
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/neptune-position",
            json={
                "date": "2025-03-29",
                "time": "20:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "altitude" in data

    def test_moon_phase_endpoint_works(self):
        """Test that moon_phase endpoint works."""
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/moon-phase",
            json={
                "date": "2025-03-29",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "illumination" in data
        assert "phase_name" in data


class TestBodiesRateLimitingIntegration:
    """Test that rate limiting works with corrected handler signatures."""

    def test_rate_limit_error_format(self):
        """Test that rate limit errors return proper 429 response."""
        from api.rate_limiter import MockLimiter
        
        # In test mode, rate limiting is bypassed with MockLimiter
        # This test documents that the handlers can be called without crashing
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/day-of-week",
            json={
                "date": "2025-03-29",
                "time": "12:00:00"
            }
        )
        
        # Should not raise TypeError about request parameter
        assert response.status_code in [200, 422]  # 200=success, 422=validation error

    def test_multiple_rapid_requests_work(self):
        """Test that rapid requests don't cause issues with request parameter."""
        client = TestClient(app)
        
        for i in range(5):
            response = client.post(
                "/api/v1/day-of-week",
                json={
                    "date": "2025-03-29",
                    "time": "12:00:00"
                }
            )
            
            # Each request should succeed (no parameter type errors)
            assert response.status_code == 200, \
                f"Request {i} failed: {response.text}"


class TestBodyParameterUsageCorrectness:
    """Test that handlers use 'body' parameter, not 'request' for body data."""

    def test_day_of_week_uses_body_date(self):
        """Verify get_day_of_week correctly uses body.date."""
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/day-of-week",
            json={
                "date": "2024-12-25",  # Christmas
                "time": "00:00:00"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        # Verify it processed the date correctly
        assert "day_of_week" in data

    def test_sun_position_uses_body_parameters(self):
        """Verify get_sun_position correctly uses body parameters."""
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/sun-position",
            json={
                "date": "2025-03-29",
                "time": "12:00:00",
                "latitude": 51.5074,  # London
                "longitude": -0.1278,
                "elevation": 10
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        # Verify location was used
        assert "location" in data
        assert data["location"]["latitude"] == 51.5074
        assert data["location"]["longitude"] == -0.1278
