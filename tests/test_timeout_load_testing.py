"""
Phase 3.3b: Synthetic Load Testing for Adaptive Timeouts.

Tests the timeout system under simulated load patterns:
1. Light load scenario (p95 fast, timeouts generous)
2. Degraded load scenario (p95 slow, timeouts tight)
3. Mixed workload (cheap + expensive endpoints)
4. DDoS mitigation (cheap endpoint flooding)
5. Timeout accuracy and p95 extraction validation
"""

import asyncio
import time
import pytest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, MagicMock

from api.timeout_logic import (
    get_tracker,
    calculate_adaptive_timeout,
    record_request_completion,
)
from api.timeout_config import (
    BASE_TIMEOUTS,
    HARD_LIMIT_SECONDS,
)


class TestLightLoadScenario:
    """Test adaptive timeouts under light load (fast completion times)."""

    def test_light_load_generates_generous_timeouts(self):
        """Under light load (p95 < 0.5x base), timeouts should be generous."""
        tracker = get_tracker()
        tracker.clear()

        endpoint = "/api/v1/batch-earth-observations"
        base = BASE_TIMEOUTS["expensive"]  # 120s

        # Simulate light load: all requests complete in 10-20 seconds
        for i in range(50):
            duration = 10 + (i % 10)
            tracker.record_completion(endpoint, float(duration))

        # p95 should be around 19 seconds (< 0.5 * 120 = 60)
        p95 = tracker.get_percentile(endpoint)
        assert p95 is not None
        assert p95 < base * 0.5

        # Timeout should be generous (2x multiplier)
        timeout = calculate_adaptive_timeout(endpoint)
        expected = base * 2  # 240s, capped at HARD_LIMIT
        assert timeout == min(expected, HARD_LIMIT_SECONDS)

    def test_cold_start_scenario(self):
        """On startup with no data, timeouts use base values."""
        tracker = get_tracker()
        tracker.clear()

        endpoint = "/api/v1/batch-earth-observations"
        base = BASE_TIMEOUTS["expensive"]

        # No data recorded yet
        timeout = calculate_adaptive_timeout(endpoint)
        assert timeout == base


class TestDegradedLoadScenario:
    """Test adaptive timeouts under degraded/heavy load."""

    def test_degraded_load_tightens_timeouts(self):
        """Under degraded load (p95 >= 0.8x base), timeouts should tighten."""
        tracker = get_tracker()
        tracker.clear()

        endpoint = "/api/v1/batch-earth-observations"
        base = BASE_TIMEOUTS["expensive"]  # 120s

        # Simulate degraded load: completion times ranging 50-150 seconds
        # p95 should be around 143 (> 0.8 * 120 = 96)
        for i in range(50):
            duration = 50 + (i * 2)  # 50 to 148 seconds
            tracker.record_completion(endpoint, float(duration))

        p95 = tracker.get_percentile(endpoint)
        assert p95 is not None
        assert p95 >= base * 0.8

        # Timeout should be degraded (0.7x multiplier)
        timeout = calculate_adaptive_timeout(endpoint)
        expected = base * 0.7  # 84s
        assert timeout == expected

    def test_health_endpoint_always_fast(self):
        """Health endpoints should stay cheap and responsive."""
        tracker = get_tracker()
        tracker.clear()

        endpoint = "/health"
        base = BASE_TIMEOUTS["cheap"]  # 3s

        # Health checks are fast even under load
        for i in range(50):
            tracker.record_completion(endpoint, 0.05)  # 50ms

        timeout = calculate_adaptive_timeout(endpoint)
        # Should still use base timeout or generous
        assert timeout >= base
        assert timeout <= base * 2


class TestMixedWorkloadScenario:
    """Test multiple endpoints with different characteristics."""

    def test_cheap_vs_expensive_endpoints_independent(self):
        """Timeouts for different endpoints should calculate independently."""
        tracker = get_tracker()
        tracker.clear()

        cheap = "/health"
        expensive = "/api/v1/batch-earth-observations"

        # Cheap endpoint: always fast
        for i in range(50):
            tracker.record_completion(cheap, 0.05)

        # Expensive endpoint: degraded
        for i in range(50):
            tracker.record_completion(expensive, float(50 + i * 2))

        cheap_timeout = calculate_adaptive_timeout(cheap)
        expensive_timeout = calculate_adaptive_timeout(expensive)

        # Cheap should be generous (2x base = 6s)
        # Expensive should be degraded (0.7x base = 84s)
        assert cheap_timeout == BASE_TIMEOUTS["cheap"] * 2  # 6s
        assert expensive_timeout == BASE_TIMEOUTS["expensive"] * 0.7  # 84s
        assert cheap_timeout < expensive_timeout  # 6s < 84s


class TestDDoSMitigationScenario:
    """Test that cheap endpoints die fast under flood attack."""

    def test_cheap_endpoint_flooding_kills_fast(self):
        """Cheap endpoint under DDoS flood should have tight timeouts."""
        tracker = get_tracker()
        tracker.clear()

        cheap_endpoint = "/health"
        expensive_endpoint = "/api/v1/batch-earth-observations"

        # Simulate severe DDoS: cheap requests are flooding server
        # Each cheap request takes 2.5s (server struggling)
        # p95 ≈ 2.5s, which is > 3 * 0.8 = 2.4s, so DEGRADED (0.7x)
        for i in range(100):
            tracker.record_completion(cheap_endpoint, 2.5)

        # Expensive endpoint still completes normally (lower volume)
        for i in range(50):
            tracker.record_completion(expensive_endpoint, 30.0)

        cheap_timeout = calculate_adaptive_timeout(cheap_endpoint)
        expensive_timeout = calculate_adaptive_timeout(expensive_endpoint)

        # Under this DDoS:
        # cheap p95 ≈ 2.5s > base(3s) * 0.8 = 2.4s → degraded (0.7x = 2.1s)
        # expensive p95 ≈ 30s < base(120s) * 0.5 = 60s → generous (2x = 240s)
        assert cheap_timeout == BASE_TIMEOUTS["cheap"] * 0.7  # 2.1s (tight)
        assert expensive_timeout == BASE_TIMEOUTS["expensive"] * 2  # 240s (generous)
        # DDoS mitigation: cheap requests killed fast, expensive preserved
        assert cheap_timeout < expensive_timeout


class TestPercentileAccuracy:
    """Validate that p95 calculations are accurate."""

    def test_p95_accuracy_uniform_distribution(self):
        """Test p95 calculation with uniform distribution."""
        tracker = get_tracker()
        tracker.clear()

        endpoint = "/test"
        # Add 100 observations: 1, 2, 3, ..., 100
        for i in range(1, 101):
            tracker.record_completion(endpoint, float(i))

        p95 = tracker.get_percentile(endpoint)
        assert p95 is not None

        # p95 of 1-100 should be approximately 95
        # With linear interpolation: 95 + 0.5*(96-95) = 95.5
        assert 93 < p95 < 97

    def test_p95_with_bimodal_distribution(self):
        """Test p95 with bimodal distribution (fast + slow requests)."""
        tracker = get_tracker()
        tracker.clear()

        endpoint = "/test"
        # 50 fast requests (1-5 seconds)
        for i in range(50):
            tracker.record_completion(endpoint, float(1 + (i % 5)))

        # 50 slow requests (95-100 seconds)
        for i in range(50):
            tracker.record_completion(endpoint, float(95 + (i % 5)))

        p95 = tracker.get_percentile(endpoint)
        assert p95 is not None

        # p95 should be closer to the slow side (around 95-100)
        assert p95 > 50  # Definitely in slow territory

    def test_p95_caching_stability(self):
        """Test that p95 cache returns consistent values."""
        tracker = get_tracker()
        tracker.clear()

        endpoint = "/test"
        for i in range(50):
            tracker.record_completion(endpoint, float(10 + i))

        p95_first = tracker.get_percentile(endpoint)
        p95_second = tracker.get_percentile(endpoint)

        # Should return cached value (identical)
        assert p95_first == p95_second


class TestTimeoutDynamics:
    """Test timeout behavior changes as load changes."""

    def test_timeout_tightens_as_load_increases(self):
        """Timeout should reduce as p95 increases."""
        tracker = get_tracker()
        tracker.clear()

        endpoint = "/test"
        base = BASE_TIMEOUTS["medium"]  # 15s

        # Phase 1: Light load (1-10s requests)
        for i in range(50):
            tracker.record_completion(endpoint, float(1 + (i % 10)))
        phase1_timeout = calculate_adaptive_timeout(endpoint)

        # Phase 2: Moderate load (5-20s requests)
        for i in range(50):
            tracker.record_completion(endpoint, float(5 + (i % 15)))
        phase2_timeout = calculate_adaptive_timeout(endpoint)

        # Phase 3: Heavy load (10-30s requests)
        for i in range(50):
            tracker.record_completion(endpoint, float(10 + (i % 20)))
        phase3_timeout = calculate_adaptive_timeout(endpoint)

        # Timeouts should get progressively tighter
        assert phase1_timeout >= phase2_timeout >= phase3_timeout

    def test_timeout_recovers_as_load_decreases(self):
        """Timeout should increase as p95 decreases (system recovers)."""
        tracker = get_tracker()
        tracker.clear()

        endpoint = "/test"

        # Start with heavy load
        for i in range(50):
            tracker.record_completion(endpoint, float(50 + i))
        heavy_timeout = calculate_adaptive_timeout(endpoint)

        # Clear and go back to light load
        tracker.clear()
        for i in range(50):
            tracker.record_completion(endpoint, float(1 + i % 5))
        light_timeout = calculate_adaptive_timeout(endpoint)

        # Light load timeout should be larger (more generous)
        assert light_timeout > heavy_timeout


class TestConcurrentLoadSimulation:
    """Simulate concurrent request patterns."""

    def test_concurrent_request_recording(self):
        """Test that concurrent record_request_completion calls work correctly."""
        tracker = get_tracker()
        tracker.clear()

        endpoint = "/test"

        def record_many(start_idx, count, duration_base):
            """Record multiple completions."""
            for i in range(count):
                record_request_completion(
                    endpoint,
                    duration_base + (i % 10)
                )

        # Simulate concurrent threads recording completions
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(record_many, 0, 50, 1.0),  # Fast thread
                executor.submit(record_many, 50, 50, 5.0),  # Medium thread
                executor.submit(record_many, 100, 50, 10.0),  # Slow thread
            ]
            for future in futures:
                future.result()

        # Total: 150 observations, should have valid p95
        p95 = tracker.get_percentile(endpoint)
        assert p95 is not None
        assert 1 < p95 < 20  # Should be in the range of recorded values


class TestTimeoutBoundaries:
    """Test timeout calculation at boundary conditions."""

    def test_hard_limit_enforced(self):
        """Timeout should never exceed HARD_LIMIT_SECONDS."""
        tracker = get_tracker()
        tracker.clear()

        endpoint = "/test"

        # Record very fast observations to trigger generous multiplier
        for i in range(50):
            tracker.record_completion(endpoint, 0.1)

        timeout = calculate_adaptive_timeout(endpoint)

        # Even with generous multiplier (2x), should cap at hard limit
        assert timeout <= HARD_LIMIT_SECONDS

    def test_minimum_timeout_enforced(self):
        """Timeout should never be zero."""
        tracker = get_tracker()
        tracker.clear()

        endpoint = "/test"

        # Record some observations
        for i in range(50):
            tracker.record_completion(endpoint, 100.0)

        timeout = calculate_adaptive_timeout(endpoint)

        # Should be positive
        assert timeout > 0

    def test_insufficient_observations_falls_back(self):
        """With < 20 observations, should use base timeout."""
        tracker = get_tracker()
        tracker.clear()

        endpoint = "/test"
        base = BASE_TIMEOUTS["medium"]

        # Record only 10 observations (insufficient)
        for i in range(10):
            tracker.record_completion(endpoint, 100.0)

        timeout = calculate_adaptive_timeout(endpoint)

        # Should fall back to base timeout
        assert timeout == base


class TestLoadSustainability:
    """Test that the system maintains reasonable behavior under sustained load."""

    def test_sustained_high_load_pattern(self):
        """Test timeout behavior under sustained high load."""
        tracker = get_tracker()
        tracker.clear()

        endpoint = "/test"
        base = BASE_TIMEOUTS["medium"]

        # Simulate 5 minutes of sustained requests (300 requests at 1/sec)
        # Each request takes 10-50 seconds
        for minute in range(5):
            for second in range(60):
                duration = 10 + ((minute * 60 + second) % 40)
                tracker.record_completion(endpoint, float(duration))

        # After sustained load, timeout should be degraded
        timeout = calculate_adaptive_timeout(endpoint)

        # p95 should be around 34 (middle of 10-50), > 0.8*15 = 12
        # So should be degraded (0.7x = 10.5s)
        assert timeout < base


@pytest.fixture(autouse=True)
def cleanup_tracker_load_tests():
    """Clean tracker before each test."""
    get_tracker().clear()
    yield
    get_tracker().clear()
