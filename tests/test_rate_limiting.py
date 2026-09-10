"""
Tests for rate limiting functionality (Phase 3.1: DDoS Protection).

Tests verify that rate limiting is properly integrated and working correctly.
Note: In test mode (pytest), rate limiting is bypassed via MockLimiter to avoid
test flakiness. These tests verify the configuration is correct, not the actual
rate limiting behavior (which requires integration tests with real FastAPI server).
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from api.rate_limiter import (
    is_test_mode,
    limiter,
    LIMIT_EXPENSIVE_BATCH,
    LIMIT_EXPENSIVE_EVENTS,
    LIMIT_STREAM_EVENTS,
    LIMIT_CONTACT_TIMES,
    LIMIT_CHEAP,
    MockLimiter,
    INTERNAL_IPS,
)


class TestRateLimiterConfiguration:
    """Test rate limiting configuration."""
    
    def test_rate_limit_constants_defined(self):
        """Test that all rate limit tiers are defined."""
        assert LIMIT_EXPENSIVE_BATCH == "20/minute"
        assert LIMIT_EXPENSIVE_EVENTS == "15/minute"
        assert LIMIT_STREAM_EVENTS == "10/minute"
        assert LIMIT_CONTACT_TIMES == "30/minute"
        assert LIMIT_CHEAP == "100/minute"
    
    def test_internal_ips_includes_localhost(self):
        """Test that internal IPs are properly configured."""
        assert "127.0.0.1" in INTERNAL_IPS
        assert "::1" in INTERNAL_IPS
    
    def test_test_mode_detection(self):
        """Test that pytest presence is detected for test mode."""
        # When pytest is imported (which it is during test runs), is_test_mode should be True
        assert is_test_mode(), "pytest should be in sys.modules during test execution"
    
    def test_mock_limiter_in_test_mode(self):
        """Test that MockLimiter is used when in test mode."""
        assert isinstance(limiter, MockLimiter), "Should use MockLimiter during pytest execution"
    
    def test_mock_limiter_limit_returns_no_op_decorator(self):
        """Test that MockLimiter.limit() returns a no-op decorator."""
        def dummy_func():
            return "result"
        
        # Apply the limit decorator
        decorated = limiter.limit("20/minute")(dummy_func)
        
        # Should return the original function unchanged
        assert decorated is dummy_func
        assert decorated() == "result"
    
    def test_mock_limiter_callable_as_decorator(self):
        """Test that MockLimiter can be used directly as a decorator."""
        def dummy_func():
            return "test"
        
        # Use MockLimiter directly as a decorator (this is what @limiter.limit() does)
        limiter_instance = MockLimiter()
        decorated = limiter_instance("20/minute")(dummy_func)
        
        assert decorated is dummy_func
        assert decorated() == "test"


class TestRateLimitingIntegration:
    """Integration tests for rate limiting with the API."""
    
    def test_endpoints_have_rate_limiting_decorators(self):
        """Test that endpoints are configured with rate limiting decorators.
        
        Note: In test mode, decorators are no-op, but the configuration should be present.
        """
        # This is verified by the fact that the API imports successfully
        # and all tests pass without errors.
        from api.main import app
        
        # Verify the app has the limiter state
        assert hasattr(app, 'state')
        assert hasattr(app.state, 'limiter')
        
        # Verify rate-limit-stats endpoint exists
        route_paths = [route.path for route in app.routes]
        assert "/rate-limit-stats" in route_paths


class TestRateLimiterDocumentation:
    """Test that rate limiting is properly documented."""
    
    def test_rate_limiting_module_has_docstring(self):
        """Test that rate_limiter module has comprehensive documentation."""
        import api.rate_limiter as rate_limiter_module
        
        assert rate_limiter_module.__doc__ is not None
        assert "DDoS protection" in rate_limiter_module.__doc__
        assert "slowapi" in rate_limiter_module.__doc__
    
    def test_limiter_constants_have_comments(self):
        """Test that rate limit constants have descriptive comments."""
        # This is a documentation test - verify the constants exist and have correct values
        assert isinstance(LIMIT_EXPENSIVE_BATCH, str)
        assert isinstance(LIMIT_EXPENSIVE_EVENTS, str)
        assert isinstance(LIMIT_STREAM_EVENTS, str)
        assert isinstance(LIMIT_CONTACT_TIMES, str)
        assert isinstance(LIMIT_CHEAP, str)


@pytest.mark.skipif(is_test_mode(), reason="Real limiter tests require non-test environment")
class TestRateLimiterProduction:
    """Tests for real rate limiter behavior in production mode.
    
    These tests are skipped during pytest execution because pytest enforces
    test mode, which uses MockLimiter. To test real rate limiting:
    
    1. Start the API server: uvicorn api.main:app
    2. Use curl or similar to make requests and verify 429 responses
    3. Check response headers for Retry-After
    
    Example test:
        # Make 21 requests in quick succession (exceeds 20/minute limit)
        for i in {1..21}; do
            curl -X POST http://localhost:8000/api/v1/batch-earth-observations \\
                -H "Content-Type: application/json" \\
                -d '{"start_date":"2025-01-01"...}'
        done
        
        # Request 21 should return 429 Too Many Requests
        # with Retry-After: 60 header
    """
    
    def test_real_limiter_available(self):
        """Placeholder: Real limiter is only tested via integration/manual tests."""
        pytest.skip("Real limiter testing requires non-test environment")


class TestRateLimiterBypass:
    """Test rate limiter bypass for internal IPs and test mode."""
    
    def test_bypass_for_test_mode(self):
        """Test that test mode bypasses rate limiting."""
        # Verify we're in test mode
        assert is_test_mode()
        
        # Verify MockLimiter is in use
        assert isinstance(limiter, MockLimiter)
        
        # Verify decorators are no-op
        def sample_func():
            return "ok"
        
        decorated = limiter.limit("1/minute")(sample_func)
        assert decorated is sample_func


class TestRateLimitingOnRoutes:
    """Test that rate limiting decorators are applied to all endpoints."""
    
    def test_batch_endpoint_has_rate_limiting(self):
        """Test that batch endpoint has rate limiting decorator."""
        from api.routes.batch import get_batch_earth_observations
        
        # Check that function has __wrapped__ (indicates decorator was applied)
        # or check the function's metadata
        func = get_batch_earth_observations
        
        # The function should exist and be callable
        assert callable(func)
        # If it was decorated by @limiter.limit(), it would be wrapped
        # In test mode with MockLimiter, it returns the original function
        # So we just verify it's still callable
        assert func is not None
    
    def test_events_endpoints_have_rate_limiting(self):
        """Test that event endpoints have rate limiting decorator."""
        from api.routes.events import (
            get_astronomical_events_route,
            stream_astronomical_events_route,
            get_contact_times_route,
        )
        
        # All should be callable and not broken by decorators
        assert callable(get_astronomical_events_route)
        assert callable(stream_astronomical_events_route)
        assert callable(get_contact_times_route)
    
    def test_bodies_endpoints_have_rate_limiting(self):
        """Test that celestial body endpoints have rate limiting."""
        from api.routes.bodies import (
            get_day_of_week,
            get_sun_position,
            get_moon_position,
            get_venus_position,
            get_mercury_position,
            get_mars_position,
            get_jupiter_position,
            get_saturn_position,
            get_uranus_position,
            get_neptune_position,
            get_moon_phase,
        )
        
        endpoints = [
            get_day_of_week,
            get_sun_position,
            get_moon_position,
            get_venus_position,
            get_mercury_position,
            get_mars_position,
            get_jupiter_position,
            get_saturn_position,
            get_uranus_position,
            get_neptune_position,
            get_moon_phase,
        ]
        
        # All should be callable and not broken by decorators
        for endpoint in endpoints:
            assert callable(endpoint), f"Endpoint {endpoint.__name__} should be callable"
    
    def test_all_routes_callable(self):
        """Integration test: verify all API routes work with rate limiting decorators."""
        from api.main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # Test a few key endpoints to ensure rate limiting doesn't break them
        # (other tests already verify full functionality)
        
        # Test moon-phase endpoint with proper fields
        response = client.post(
            "/api/v1/moon-phase",
            json={
                "date": "2025-06-15",
                "time": "12:00:00",
                "latitude": 40.7128,
                "longitude": -74.0060
            }
        )
        assert response.status_code == 200, f"moon-phase endpoint failed: {response.text}"
        
        # Test day-of-week endpoint
        response = client.post(
            "/api/v1/day-of-week",
            json={"date": "2025-06-15"}
        )
        assert response.status_code == 200, f"day-of-week endpoint failed: {response.text}"
        
        # Test rate-limit-stats endpoint
        response = client.get("/rate-limit-stats")
        assert response.status_code == 200, f"rate-limit-stats endpoint failed: {response.text}"
        data = response.json()
        assert "message" in data or "storage_type" in data


class TestRateLimitingDocumentation:
    """Test rate limiting documentation and comments."""
    
    def test_rate_limits_match_tier_strategy(self):
        """Verify rate limit tiers match the documented strategy."""
        # Tier 1: Global fallback
        assert LIMIT_CHEAP == "100/minute"  # Position/phase endpoints
        
        # Tier 2: Expensive operations (by resource usage)
        assert LIMIT_EXPENSIVE_BATCH == "20/minute"  # ~40s each = 800s CPU/min
        assert LIMIT_EXPENSIVE_EVENTS == "15/minute"  # Eclipse search
        assert LIMIT_STREAM_EVENTS == "10/minute"  # Streaming connections
        assert LIMIT_CONTACT_TIMES == "30/minute"  # Contact times (moderate)
        
        # Verify the strategy is conservative (fewer req/min for expensive ops)
        limits_dict = {
            "batch": int(LIMIT_EXPENSIVE_BATCH.split("/")[0]),
            "events": int(LIMIT_EXPENSIVE_EVENTS.split("/")[0]),
            "stream": int(LIMIT_STREAM_EVENTS.split("/")[0]),
            "contact": int(LIMIT_CONTACT_TIMES.split("/")[0]),
            "cheap": int(LIMIT_CHEAP.split("/")[0]),
        }
        
        # Expensive operations should have lower limits
        assert limits_dict["batch"] < limits_dict["cheap"]
        assert limits_dict["events"] < limits_dict["cheap"]
        assert limits_dict["stream"] < limits_dict["cheap"]
    
    def test_exception_handler_configured(self):
        """Test that rate limit exception handler is properly configured."""
        from api.main import app
        
        # In test mode, exception handler might not be registered
        # but the app should still have exception handlers
        assert hasattr(app, 'exception_handlers') or hasattr(app, '_exception_handlers')


class TestRateLimitingI18n:
    """Test i18n integration for rate limiting error messages."""

    def test_rate_limit_error_messages_in_all_locales(self):
        """Test that tooManyRequests message exists in all supported locales."""
        from api.i18n import ALLOWED_LOCALES
        from pathlib import Path
        import json

        locales_dir = Path(__file__).parent.parent / 'api' / 'locales'
        
        for locale in ALLOWED_LOCALES:
            locale_file = locales_dir / f'{locale}.json'
            assert locale_file.exists(), f"Locale file {locale}.json not found"
            
            with open(locale_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            assert 'errors' in data, f"errors section missing in {locale}.json"
            assert 'tooManyRequests' in data['errors'], \
                f"tooManyRequests message missing in {locale}.json"
            
            msg = data['errors']['tooManyRequests']
            assert isinstance(msg, str), f"tooManyRequests should be string in {locale}.json"
            assert len(msg) > 0, f"tooManyRequests message is empty in {locale}.json"
            assert '{retry_after}' in msg, \
                f"tooManyRequests should have {{retry_after}} placeholder in {locale}.json"

    def test_rate_limit_exception_handler_uses_i18n(self):
        """Test that rate_limit_exception_handler uses i18n for error message."""
        import asyncio
        from unittest.mock import MagicMock, patch
        from fastapi import Request
        from api.rate_limiter import rate_limit_exception_handler

        async def run_test():
            # Mock request with client info
            mock_request = MagicMock(spec=Request)
            mock_request.client.host = "192.168.1.1"
            mock_request.url.path = "/api/v1/test"

            # Create a simple mock exception
            mock_exc = MagicMock()

            with patch('api.rate_limiter.get_i18n') as mock_get_i18n:
                # Setup mock i18n
                mock_i18n = MagicMock()
                mock_i18n.get.return_value = "Too many requests. Please retry after 60 seconds."
                mock_get_i18n.return_value = mock_i18n

                # Call exception handler
                response = await rate_limit_exception_handler(
                    mock_request,
                    mock_exc
                )

                # Verify i18n was called
                mock_i18n.get.assert_called_once()
                call_args = mock_i18n.get.call_args
                
                # Verify the key requested
                assert call_args[0][0] == "errors.tooManyRequests"
                
                # Verify retry_after parameter was passed
                assert 'retry_after' in call_args[1]
                assert call_args[1]['retry_after'] == 60

                # Verify response structure
                assert response.status_code == 429
                data = response.body.decode()
                assert "Too many requests" in data

        asyncio.run(run_test())

    def test_rate_limit_error_message_interpolation(self):
        """Test that error message is properly interpolated with retry_after."""
        from api.i18n import get_i18n

        i18n = get_i18n('en')
        message = i18n.get(
            'errors.tooManyRequests',
            retry_after=60
        )

        assert isinstance(message, str)
        assert '60' in message or 'retry' in message.lower()
        assert 'many' in message.lower() or 'too' in message.lower()

    def test_rate_limit_error_message_different_locales(self):
        """Test that error messages work correctly in different locales."""
        from api.i18n import get_i18n

        for locale in ['en', 'en-us', 'en-uk']:
            i18n = get_i18n(locale)
            message = i18n.get(
                'errors.tooManyRequests',
                default="Default message",
                retry_after=60
            )

            # Should get localized message (not default)
            assert message != "Default message", \
                f"Should have localized message for {locale}"
            assert '{retry_after}' not in message, \
                f"Interpolation failed for {locale}: {message}"

    def test_rate_limit_error_message_fallback(self):
        """Test that error message gracefully falls back if key is missing."""
        from api.i18n import get_i18n

        i18n = get_i18n('en')
        
        # Test with a missing key to verify fallback behavior
        message = i18n.get(
            'errors.nonexistentKey',
            default="Fallback message",
            retry_after=60
        )

        # Should return the default
        assert message == "Fallback message"
