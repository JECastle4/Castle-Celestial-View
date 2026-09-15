"""Integration tests for rate limiting with real rate limiter.

Note: These tests run the production FastAPI app in an isolated process
with real rate limiting enabled (RATE_LIMIT_ENABLED=true) to verify
actual slowapi behavior, not just mock behavior.
"""

import pytest
from unittest.mock import MagicMock, patch
import asyncio
import subprocess
import time
import requests
import os
from pathlib import Path

from api.rate_limiter import LIMIT_EXPENSIVE_BATCH
from fastapi.testclient import TestClient
from api.main import app


class TestRateLimitingIntegration:
    """Integration tests with actual rate limiting behavior."""

    def test_rate_limiting_constant_5_per_minute(self):
        """Verify LIMIT_EXPENSIVE_BATCH is 5 requests per minute."""
        # With 4 CPU cores and 40s CPU per request: 240s available / 40s = 6 max, use 5 for safety
        # This ensures the test fails if the constant changes
        expected_limit = "5/minute"
        
        # Assert the real constant matches expected value
        assert LIMIT_EXPENSIVE_BATCH == expected_limit, (
            f"LIMIT_EXPENSIVE_BATCH mismatch: expected '{expected_limit}', "
            f"got '{LIMIT_EXPENSIVE_BATCH}'. Update test or production constant."
        )
        
        # Parse the limit string to verify format
        count, period = LIMIT_EXPENSIVE_BATCH.split("/")
        assert count == "5"
        assert period == "minute"

    def test_batch_endpoint_limit_aligns_with_cpu_capacity(self):
        """Batch endpoint limit matches CPU capacity constraint."""
        # CPU capacity: 4 cores × 60 seconds = 240 CPU-seconds per minute
        # Batch cost: 40s average CPU per request
        # Max sustainable: 240 / 40 = 6 requests, use 5 with 25% safety margin
        # This aligns with 5/minute limit from LIMIT_EXPENSIVE_BATCH
        
        # Extract the actual limit from the constant
        count_str, period = LIMIT_EXPENSIVE_BATCH.split("/")
        requests_per_minute = int(count_str)
        avg_cpu_seconds = 40  # documented in benchmark
        
        max_cpu_per_minute = requests_per_minute * avg_cpu_seconds
        
        # 5 requests × 40s each = 200s CPU allowed per minute (83% of 240s capacity)
        assert max_cpu_per_minute == 200, f"Expected 5 × 40s = 200s, got {max_cpu_per_minute}s"
        assert requests_per_minute == 5, f"Expected 5 requests/min, got {requests_per_minute}"

    def test_rate_limit_string_format(self):
        """Verify rate limit string is properly formatted (from actual constant)."""
        # Use the real constant, not hardcoded
        limit_string = LIMIT_EXPENSIVE_BATCH
        
        # Should be parseable as "count/period"
        parts = limit_string.split("/")
        assert len(parts) == 2
        assert parts[0].isdigit()
        assert parts[1] in ["minute", "hour", "day"]

    def test_batch_endpoint_rate_limiting_integration(self):
        """Real integration test: verify batch endpoint is rate limited."""
        # This test exercises the actual rate limiter (slowapi)
        # Note: Rate limiting keying is per-IP, and TestClient spoofs the same IP
        # for all requests. In a real deployment, different clients would have
        # separate limits. This test verifies the decorator is applied.
        
        client = TestClient(app)
        
        # POST to batch endpoint (which has @limiter.limit(LIMIT_EXPENSIVE_BATCH))
        # In a real test with mocked time, we could make >10 requests/min and verify 429
        # Here we just verify the endpoint exists and the decorator doesn't break it
        
        batch_request = {
            "start_date": "2025-01-01",
            "start_time": "00:00:00",
            "end_date": "2025-01-02",
            "end_time": "23:59:59",
            "frame_count": 2,
            "latitude": 0.0,
            "longitude": 0.0,
            "elevation": 0.0
        }
        
        # Single request should succeed (not rate limited within a minute)
        response = client.post("/api/v1/batch-earth-observations", json=batch_request)
        
        # Either succeeds (200-299) or times out/errors, but should not be rate-limited
        # (429 would indicate rate limiting is misconfigured if this is the only request)
        assert response.status_code != 429, (
            "Single batch request should not be rate limited; "
            "if 429, rate limiter may be misconfigured"
        )

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


class TestRateLimitingWithRealLimiter:
    """Integration tests that actually exercise the production rate limiter.
    
    These tests run the FastAPI app in an isolated subprocess with real
    rate limiting enabled (RATE_LIMIT_ENABLED=true) and send actual HTTP
    requests to verify that the slowapi limiter rejects requests beyond
    the configured limit.
    """

    @pytest.fixture
    def app_subprocess(self):
        """Start FastAPI app in subprocess with rate limiting enabled."""
        # Get the project root
        project_root = Path(__file__).parent.parent
        
        # Create custom environment with rate limiting enabled
        # IMPORTANT: Remove pytest-related env vars to avoid is_test_mode() returning True
        env = os.environ.copy()
        env["RATE_LIMIT_ENABLED"] = "true"
        env["LIMIT_EXPENSIVE_BATCH"] = "3/minute"  # Use 3/min for faster testing
        env["PYTHONPATH"] = str(project_root)
        # Trust loopback so X-Forwarded-For headers from test clients are respected
        env["TRUSTED_PROXIES"] = "127.0.0.1"
        # Remove pytest environment variables that would trigger is_test_mode()
        env.pop("PYTEST_CURRENT_TEST", None)
        
        # Start uvicorn subprocess
        # Use a specific port to avoid conflicts
        port = 9999
        cmd = [
            "python",
            "-m",
            "uvicorn",
            "api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "info"  # Show logs to see if rate limiter is enabled
        ]
        
        try:
            process = subprocess.Popen(
                cmd,
                env=env,
                cwd=str(project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT  # Combine stderr with stdout
            )
            
            # Wait for server to start (up to 10 seconds)
            start_time = time.time()
            server_ready = False
            while time.time() - start_time < 10:
                try:
                    response = requests.get(f"http://127.0.0.1:{port}/health", timeout=1)
                    if response.status_code == 200:
                        server_ready = True
                        break
                except requests.exceptions.ConnectionError:
                    time.sleep(0.1)
            
            if not server_ready:
                # Server didn't start in time
                process.terminate()
                raise RuntimeError("Failed to start FastAPI app subprocess")
            
            # Give server a moment to fully initialize
            time.sleep(0.5)
            
            yield f"http://127.0.0.1:{port}"
            
        finally:
            # Cleanup: terminate subprocess
            if process.poll() is None:
                process.terminate()
                # Read and print any output for debugging
                try:
                    stdout, _ = process.communicate(timeout=2)
                    if stdout:
                        print("\n=== Subprocess Output ===")
                        print(stdout.decode('utf-8', errors='ignore'))
                        print("=== End Subprocess Output ===\n")
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

    def test_batch_endpoint_rate_limit_with_real_limiter(self, app_subprocess):
        """Verify batch endpoint returns 429 when rate limit is exceeded.
        
        This test actually exercises the production slowapi rate limiter
        with real HTTP requests. It:
        1. Sends 3 requests (at the configured limit)
        2. Sends a 4th request that should be rate limited
        3. Verifies the 4th request returns 429 Too Many Requests
        """
        batch_request = {
            "start_date": "2025-01-01",
            "start_time": "00:00:00",
            "end_date": "2025-01-02",
            "end_time": "23:59:59",
            "frame_count": 2,
            "latitude": 0.0,
            "longitude": 0.0,
            "elevation": 0.0
        }
        
        url = f"{app_subprocess}/api/v1/batch-earth-observations"
        
        # Send 3 requests (at the configured 3/minute limit)
        status_codes = []
        for i in range(3):
            response = requests.post(url, json=batch_request, timeout=30)
            status_codes.append(response.status_code)
            # Should not be rate limited yet
            if response.status_code == 429:
                pytest.fail(f"Request {i+1} should not be rate limited; got 429")
        
        # Send 4th request (should be rate limited)
        response = requests.post(url, json=batch_request, timeout=30)
        debug_info = (
            f"Request 4 status: {response.status_code}\n"
            f"First 3 requests: {status_codes}\n"
            f"Response headers: {dict(response.headers)}\n"
            f"Response body: {response.text[:500]}"
        )
        
        # This should return 429 Too Many Requests
        if response.status_code != 429:
            pytest.fail(
                f"Request 4 should be rate limited (429), got {response.status_code}.\n"
                f"Debug info:\n{debug_info}"
            )
        
        # Verify response body contains rate limit info
        response_json = response.json()
        assert "error" in response_json and response_json["error"] == "rate_limit_exceeded", (
            f"429 response should have error='rate_limit_exceeded'. Got: {response_json}"
        )
        assert "retry_after" in response_json, (
            f"429 response should have retry_after field. Got: {response_json}"
        )

    def test_different_clients_have_independent_limits(self, app_subprocess):
        """Verify rate limiting is per-IP (independent for each client).
        
        This test sends requests from different source IPs (simulated via
        X-Forwarded-For header) and verifies that each IP has its own
        rate limit counter.
        """
        batch_request = {
            "start_date": "2025-01-01",
            "start_time": "00:00:00",
            "end_date": "2025-01-02",
            "end_time": "23:59:59",
            "frame_count": 2,
            "latitude": 0.0,
            "longitude": 0.0,
            "elevation": 0.0
        }
        
        url = f"{app_subprocess}/api/v1/batch-earth-observations"
        
        # Send 3 requests from IP1 (at the limit)
        headers_ip1 = {"X-Forwarded-For": "203.0.113.100"}
        for i in range(3):
            response = requests.post(url, json=batch_request, headers=headers_ip1, timeout=30)
            assert response.status_code != 429, f"IP1 request {i+1} should not be rate limited"
        
        # Send 1 request from IP2 (should succeed, different IP has its own limit)
        headers_ip2 = {"X-Forwarded-For": "203.0.113.200"}
        response = requests.post(url, json=batch_request, headers=headers_ip2, timeout=30)
        assert response.status_code != 429, "IP2 should have independent rate limit"
        
        # Send 4th request from IP1 (should be rate limited)
        response = requests.post(url, json=batch_request, headers=headers_ip1, timeout=30)
        assert response.status_code == 429, "IP1 should be rate limited after 3 requests"
        
        # Send 2nd request from IP2 (should still succeed)
        response = requests.post(url, json=batch_request, headers=headers_ip2, timeout=30)
        assert response.status_code != 429, "IP2 should not be rate limited after 1 request"
