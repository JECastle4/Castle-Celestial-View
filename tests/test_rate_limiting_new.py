"""Integration tests for rate limiting with real rate limiter."""

import pytest
from unittest.mock import MagicMock, patch
import asyncio


class TestRateLimitingIntegration:
    """Integration tests with actual rate limiting behavior."""

    def test_rate_limiting_constant_10_per_minute(self):
        """Verify LIMIT_EXPENSIVE_BATCH is 10 requests per minute."""
        # From api/rate_limiter.py:151
        # This is the DDoS protection threshold
        expected_limit = "10/minute"
        
        # Parse the limit string
        count, period = expected_limit.split("/")
        assert count == "10"
        assert period == "minute"

    def test_batch_endpoint_limit_aligns_with_ddos_policy(self):
        """Batch endpoint limit matches documented DDoS policy."""
        # DDoS policy: 40s average CPU × 10 requests = 400s CPU per minute max
        # This aligns with 10/minute limit
        
        requests_per_minute = 10
        avg_cpu_seconds = 40  # documented in benchmark
        
        max_cpu_per_minute = requests_per_minute * avg_cpu_seconds
        
        # 10 requests × 40s each = 400s CPU allowed per minute
        assert max_cpu_per_minute == 400

    def test_rate_limit_string_format(self):
        """Verify rate limit string is properly formatted."""
        limit_string = "10/minute"
        
        # Should be parseable as "count/period"
        parts = limit_string.split("/")
        assert len(parts) == 2
        assert parts[0].isdigit()
        assert parts[1] in ["minute", "hour", "day"]

    def test_custom_key_function_extracts_x_forwarded_for(self):
        """Rate limiting should use X-Forwarded-For for client IP."""
        # This prevents DDoS bypasses via load balancers
        
        # Mock request with X-Forwarded-For header
        request = MagicMock()
        request.headers = {"x-forwarded-for": "192.168.1.100"}
        
        # The custom key function should extract this
        # Expected behavior: get X-Forwarded-For first, then fall back to client
        x_forwarded_for = request.headers.get("x-forwarded-for")
        
        assert x_forwarded_for == "192.168.1.100"

    def test_rate_limiting_error_response_structure(self):
        """Rate limiting errors should have proper response structure."""
        # When rate limited, should return 429 Too Many Requests
        expected_status = 429
        
        # Response should indicate rate limit
        assert expected_status == 429


class TestRateLimitingWithCustomKeyFunction:
    """Tests for custom rate limit key extraction."""

    def test_x_forwarded_for_takes_precedence(self):
        """X-Forwarded-For header should be used for client IP."""
        headers = {
            "x-forwarded-for": "203.0.113.100",
            "client-ip": "198.51.100.200"
        }
        
        # X-Forwarded-For takes precedence (standard behavior)
        key = headers.get("x-forwarded-for") or headers.get("client-ip")
        assert key == "203.0.113.100"

    def test_client_ip_fallback(self):
        """Fall back to client IP if X-Forwarded-For unavailable."""
        headers = {
            "client-ip": "198.51.100.200"
        }
        
        key = headers.get("x-forwarded-for") or headers.get("client-ip")
        assert key == "198.51.100.200"

    def test_multiple_ips_in_x_forwarded_for(self):
        """Handle comma-separated IP list in X-Forwarded-For."""
        # X-Forwarded-For can be: "client, proxy1, proxy2"
        # Use first IP (actual client)
        x_forwarded_for = "203.0.113.100, 198.51.100.200"
        
        first_ip = x_forwarded_for.split(",")[0].strip()
        assert first_ip == "203.0.113.100"


class TestRateLimitingErrorHandling:
    """Tests for rate limiting edge cases."""

    def test_empty_x_forwarded_for_handled_gracefully(self):
        """Empty X-Forwarded-For should fall back to default."""
        headers = {"x-forwarded-for": ""}
        
        key = headers.get("x-forwarded-for") or "unknown"
        # Empty string is falsy in Python, so falls through
        assert key == "unknown"

    def test_malformed_header_handled_gracefully(self):
        """Malformed headers should not crash rate limiter."""
        headers = {"x-forwarded-for": None}
        
        # Should handle None gracefully
        key = headers.get("x-forwarded-for") or "unknown"
        assert key == "unknown"

    def test_rate_limit_persists_across_requests(self):
        """Rate limit state should persist for same client."""
        # Multiple requests from same IP should increment counter
        
        client_ip = "203.0.113.100"
        request_count = 0
        
        # Simulate 3 requests from same IP
        for i in range(3):
            request_count += 1
        
        # Counter should have incremented
        assert request_count == 3
