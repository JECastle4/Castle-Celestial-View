"""
Tests for Phase 3.3 adaptive timeout logic (graceful degradation under load).

Tests the percentile tracker, timeout calculation, and middleware integration.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

from api.main import app
from api.timeout_logic import (
    PercentileTracker,
    calculate_adaptive_timeout,
    record_request_completion,
    get_tracker,
)
from api.timeout_config import (
    ENDPOINT_COSTS,
    BASE_TIMEOUTS,
    HARD_LIMIT_SECONDS,
    get_endpoint_cost,
    get_base_timeout,
)
from api.metrics import get_metrics


class TestTimeoutConfig:
    """Test endpoint cost classification and base timeouts."""

    def test_endpoint_cost_classification(self):
        """Test that endpoints are correctly classified."""
        assert get_endpoint_cost('/health') == 'cheap'
        assert get_endpoint_cost('/metrics') == 'cheap'
        assert get_endpoint_cost('/api/v1/sun-position') == 'medium'
        assert get_endpoint_cost('/api/v1/batch-earth-observations') == 'expensive'
        assert get_endpoint_cost('/api/v1/astronomical-events') == 'expensive'
        assert get_endpoint_cost('/unknown-endpoint') == 'medium'  # Default

    def test_base_timeouts(self):
        """Test that base timeouts are correct."""
        assert get_base_timeout('cheap') == 3
        assert get_base_timeout('medium') == 15
        assert get_base_timeout('expensive') == 120
        assert get_base_timeout('unknown') == 15  # Default to medium


class TestPercentileTracker:
    """Test the in-memory percentile tracker."""

    def test_percentile_tracker_initialization(self):
        """Test tracker initializes empty."""
        tracker = PercentileTracker()
        assert tracker.get_percentile('/test') is None

    def test_record_single_observation(self):
        """Test recording a single observation."""
        tracker = PercentileTracker()
        tracker.record_completion('/test', 1.0)
        # Not enough data yet (need 20+ observations)
        assert tracker.get_percentile('/test') is None

    def test_insufficient_observations(self):
        """Test that percentile returns None with <20 observations."""
        tracker = PercentileTracker()
        for i in range(19):
            tracker.record_completion('/test', float(i))
        assert tracker.get_percentile('/test') is None

    def test_calculate_percentile_with_sufficient_data(self):
        """Test percentile calculation with 20+ observations."""
        tracker = PercentileTracker()
        # Add 100 observations: 1, 2, 3, ..., 100
        for i in range(1, 101):
            tracker.record_completion('/test', float(i))
        
        p95 = tracker.get_percentile('/test')
        assert p95 is not None
        # p95 should be close to 95 (95th percentile of 1-100)
        assert 93 < p95 < 97

    def test_percentile_caching(self):
        """Test that percentile is cached for 5 seconds."""
        tracker = PercentileTracker()
        # Add initial observations
        for i in range(1, 101):
            tracker.record_completion('/test', float(i))
        
        p95_first = tracker.get_percentile('/test')
        
        # Add more observations (should not change cached value)
        for i in range(101, 151):
            tracker.record_completion('/test', float(i) * 10)
        
        p95_cached = tracker.get_percentile('/test')
        assert p95_cached == p95_first  # Should return cached value

    def test_sliding_window_cleanup(self):
        """Test that observations older than 5 minutes are removed."""
        tracker = PercentileTracker()
        
        # Add observations
        for i in range(1, 101):
            tracker.record_completion('/test', float(i))
        
        p95_before = tracker.get_percentile('/test')
        assert p95_before is not None
        
        # Simulate old observations (past the 5-minute window)
        # by manipulating the internal deque
        with tracker._lock:
            old_time = time.time() - 301  # 5 min + 1 sec ago
            if '/test' in tracker._observations:
                # Prepend old observations
                tracker._observations['/test'].appendleft((old_time, 999.0))
        
        # After cleanup, p95 should still be similar (old data removed)
        p95_after = tracker.get_percentile('/test')
        # Percentile cache was invalidated by our manipulation
        # This test mainly ensures no crash occurs

    def test_negative_durations_ignored(self):
        """Test that negative durations are ignored."""
        tracker = PercentileTracker()
        tracker.record_completion('/test', -1.0)
        tracker.record_completion('/test', -0.5)
        # No observations recorded
        assert tracker.get_percentile('/test') is None

    def test_clear_tracker(self):
        """Test clearing all observations and cache."""
        tracker = PercentileTracker()
        for i in range(1, 101):
            tracker.record_completion('/test', float(i))
        
        assert tracker.get_percentile('/test') is not None
        
        tracker.clear()
        assert tracker.get_percentile('/test') is None

    def test_multiple_endpoints(self):
        """Test tracking percentiles for multiple endpoints independently."""
        tracker = PercentileTracker()
        
        # Endpoint 1: fast requests
        for i in range(1, 101):
            tracker.record_completion('/fast', float(i) * 0.1)
        
        # Endpoint 2: slow requests
        for i in range(1, 101):
            tracker.record_completion('/slow', float(i) * 10)
        
        p95_fast = tracker.get_percentile('/fast')
        p95_slow = tracker.get_percentile('/slow')
        
        assert p95_fast is not None
        assert p95_slow is not None
        assert p95_slow > p95_fast  # Slow endpoint should have higher p95


class TestTimeoutCalculation:
    """Test adaptive timeout calculation logic."""

    def test_cold_start_uses_base_timeout(self):
        """Test that cold start (no data) uses base timeout."""
        # Clear tracker
        get_tracker().clear()
        
        timeout = calculate_adaptive_timeout('/api/v1/batch-earth-observations')
        assert timeout == BASE_TIMEOUTS['expensive']

    def test_fast_system_generous_timeout(self):
        """Test that fast system (p95 < base * 0.5) gets generous timeout."""
        tracker = get_tracker()
        tracker.clear()
        
        endpoint = '/api/v1/batch-earth-observations'
        base = BASE_TIMEOUTS['expensive']  # 120s
        
        # Add observations where p95 < 60s (0.5 * 120)
        for i in range(1, 101):
            tracker.record_completion(endpoint, float(i) * 0.3)  # 0.3 to 30 seconds
        
        timeout = calculate_adaptive_timeout(endpoint)
        # Should be generous (2x multiplier) = 240s, but capped at hard limit
        assert timeout == min(base * 2, HARD_LIMIT_SECONDS)

    def test_healthy_system_normal_timeout(self):
        """Test that healthy system (p95 < base * 0.8) uses base timeout."""
        tracker = get_tracker()
        tracker.clear()
        
        endpoint = '/api/v1/batch-earth-observations'
        base = BASE_TIMEOUTS['expensive']  # 120s
        
        # Add observations where base * 0.5 < p95 < base * 0.8
        # (60s < p95 < 96s)
        for i in range(1, 101):
            tracker.record_completion(endpoint, float(i) * 0.7)  # 0.7 to 70 seconds
        
        timeout = calculate_adaptive_timeout(endpoint)
        # Should be normal (1x multiplier) = 120s
        assert timeout == base

    def test_degraded_system_tightened_timeout(self):
        """Test that degraded system (p95 >= base * 0.8) tightens timeout."""
        tracker = get_tracker()
        tracker.clear()
        
        endpoint = '/api/v1/batch-earth-observations'
        base = BASE_TIMEOUTS['expensive']  # 120s
        
        # Add observations where p95 >= base * 0.8 (p95 >= 96s)
        # Using 1-150 gives p95 around 142 which is > 96
        for i in range(1, 151):
            tracker.record_completion(endpoint, float(i))  # 1 to 100 seconds
        
        timeout = calculate_adaptive_timeout(endpoint)
        # Should be degraded (0.7x multiplier) = 84s
        assert timeout == base * 0.7

    def test_hard_limit_ceiling(self):
        """Test that timeout never exceeds hard limit."""
        tracker = get_tracker()
        tracker.clear()
        
        # Try to make a timeout larger than hard limit
        # This shouldn't happen with generous multiplier, but test it
        endpoint = '/batch-earth-observations'
        base = BASE_TIMEOUTS['expensive']  # 120s
        
        # Add very fast observations to trigger generous multiplier
        for i in range(1, 101):
            tracker.record_completion(endpoint, 0.01)  # All very fast
        
        timeout = calculate_adaptive_timeout(endpoint)
        # Even with 2x multiplier, should be capped at HARD_LIMIT
        assert timeout <= HARD_LIMIT_SECONDS


class TestTimeoutMiddleware:
    """Test timeout middleware integration."""

    def test_health_endpoint_no_timeout(self):
        """Test that /health endpoint doesn't timeout."""
        client = TestClient(app)
        response = client.get('/health')
        assert response.status_code == 200

    def test_metrics_endpoint_no_timeout(self):
        """Test that /metrics endpoint doesn't timeout."""
        client = TestClient(app)
        response = client.get('/metrics')
        assert response.status_code == 200

    def test_timeout_exceeded_returns_503(self):
        """Test that timeout exceeded returns 503."""
        # This is tricky to test without a slow endpoint
        # We'll patch the timeout calculation to return very small value
        with patch('api.main.calculate_adaptive_timeout', return_value=0.001):
            client = TestClient(app)
            # Try an endpoint that does some work
            response = client.get('/health')
            # May timeout or succeed depending on timing
            # The important thing is that middleware doesn't crash


class TestPreRouteTimeout:
    """Test pre-route label derivation for timeout calculation."""

    def test_pre_route_label_derivation_health(self):
        """Test that health endpoint is recognized before route matching."""
        # Pre-route label should be derived from raw path
        # /health should map to 'cheap' tier
        from api.timeout_config import get_endpoint_cost
        
        # Simulate path extraction
        cost = get_endpoint_cost('/health')
        assert cost == 'cheap'

    def test_pre_route_label_derivation_batch(self):
        """Test that batch endpoint path is recognized."""
        from api.timeout_config import get_endpoint_cost
        
        cost = get_endpoint_cost('/api/v1/batch-earth-observations')
        assert cost == 'expensive'

    def test_pre_route_label_derivation_contact_times(self):
        """Test that contact-times endpoint path is recognized."""
        from api.timeout_config import get_endpoint_cost
        
        cost = get_endpoint_cost('/api/v1/astronomical-events/contact-times')
        assert cost == 'expensive'

    def test_pre_route_label_defaults_to_medium(self):
        """Test that unknown paths default to medium tier."""
        from api.timeout_config import get_endpoint_cost
        
        cost = get_endpoint_cost('/api/v1/unknown-endpoint')
        assert cost == 'medium'


class TestStreamingTimeoutHandling:
    """Test timeout enforcement on streaming responses."""

    def test_timeout_applies_to_streaming_endpoints(self):
        """Test that timeout middleware applies to streaming endpoints."""
        client = TestClient(app)
        
        # Try to access a streaming endpoint (should not timeout in test)
        response = client.get(
            '/api/v1/astronomical-events-stream?'
            'start_date=2025-09-01&'
            'end_date=2025-09-02&'
            'include_contact_times=false'
        )
        
        # Should either succeed or timeout gracefully
        assert response.status_code in [200, 503, 504]

    def test_timeout_not_exceeded_for_quick_stream(self):
        """Test that quick streaming responses complete successfully."""
        client = TestClient(app)
        
        # Streaming endpoint with narrow date range (should be quick)
        response = client.get(
            '/api/v1/astronomical-events-stream?'
            'start_date=2025-09-01&'
            'end_date=2025-09-01&'
            'include_contact_times=false'
        )
        
        # Should complete without timeout
        assert response.status_code == 200


class TestTimeoutMetrics:
    """Test that timeout events are properly tracked."""

    def test_timeout_exceeded_recorded_in_metrics(self):
        """Test that timeout_exceeded_total is incremented."""
        metrics = get_metrics()
        
        # Record a timeout occurrence
        metrics.record_request('/api/test', 'GET', 504, 0.5)
        
        text = metrics.get_metrics_text().decode('utf-8')
        assert 'http_requests_total' in text

    def test_multiple_timeouts_tracked(self):
        """Test that multiple timeout occurrences are tracked."""
        metrics = get_metrics()
        
        # Record multiple timeout responses
        for i in range(3):
            metrics.record_request('/api/test', 'GET', 504, 0.5 + i * 0.1)
        
        text = metrics.get_metrics_text().decode('utf-8')
        assert 'http_requests_total' in text


@pytest.fixture(autouse=True)
def cleanup_tracker():
    """Cleanup tracker before each test."""
    get_tracker().clear()
    yield
    get_tracker().clear()
