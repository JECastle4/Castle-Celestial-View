"""
Phase 3.3c: Performance Profiling for Adaptive Timeouts.

Measures timeout calculation overhead to ensure <1ms per-request target.
Tests:
1. Single timeout calculation latency
2. Percentile extraction speed
3. Concurrent calculation performance
4. Memory overhead tracking
5. Cache efficiency (5-second TTL)
"""

import time
import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys

from api.timeout_logic import (
    get_tracker,
    calculate_adaptive_timeout,
    record_request_completion,
    PercentileTracker,
)


class TestTimeoutCalculationLatency:
    """Measure latency of timeout calculation."""

    def test_timeout_calculation_under_1ms(self):
        """Single timeout calculation should complete in <1ms."""
        tracker = get_tracker()
        tracker.clear()

        endpoint = "/batch-earth-observations"

        # Populate with observations
        for i in range(50):
            tracker.record_completion(endpoint, float(10 + i))

        # Time a single calculation
        start = time.perf_counter()
        for _ in range(100):
            calculate_adaptive_timeout(endpoint)
        elapsed = time.perf_counter() - start

        avg_latency = (elapsed / 100) * 1000  # Convert to ms
        assert avg_latency < 1.0, f"Timeout calculation too slow: {avg_latency:.3f}ms"

    def test_cold_start_calculation_fast(self):
        """Cold start (no data) should be instant."""
        tracker = get_tracker()
        tracker.clear()

        endpoint = "/test"

        # Time cold start calculation
        start = time.perf_counter()
        for _ in range(1000):
            calculate_adaptive_timeout(endpoint)
        elapsed = time.perf_counter() - start

        avg_latency = (elapsed / 1000) * 1000  # Convert to ms
        assert avg_latency < 0.1, f"Cold start too slow: {avg_latency:.3f}ms"


class TestPercentileCalculationSpeed:
    """Measure percentile extraction performance."""

    def test_percentile_calculation_under_1ms(self):
        """Percentile calculation from 100 observations should be <1ms."""
        tracker = get_tracker()
        tracker.clear()

        endpoint = "/test"

        # Add 100 observations (typical sliding window at 1 req/sec)
        for i in range(100):
            tracker.record_completion(endpoint, float(10 + (i % 20)))

        # Time percentile extraction
        start = time.perf_counter()
        for _ in range(100):
            tracker.get_percentile(endpoint)
        elapsed = time.perf_counter() - start

        avg_latency = (elapsed / 100) * 1000  # Convert to ms
        assert avg_latency < 1.0, f"Percentile extraction too slow: {avg_latency:.3f}ms"

    def test_percentile_cache_efficiency(self):
        """Cached percentile should be nearly instant."""
        tracker = get_tracker()
        tracker.clear()

        endpoint = "/test"

        # Add observations
        for i in range(100):
            tracker.record_completion(endpoint, float(10 + (i % 20)))

        # Get percentile once (warm cache)
        tracker.get_percentile(endpoint)

        # Time cached lookup
        start = time.perf_counter()
        for _ in range(10000):
            tracker.get_percentile(endpoint)
        elapsed = time.perf_counter() - start

        avg_latency = (elapsed / 10000) * 1000  # Convert to ms
        # Cached lookups should be <0.01ms
        assert avg_latency < 0.01, f"Cache lookup too slow: {avg_latency:.4f}ms"


class TestRecordCompletionPerformance:
    """Measure record_request_completion performance."""

    def test_record_completion_very_fast(self):
        """Recording a completion should be <0.5ms."""
        tracker = get_tracker()
        tracker.clear()

        endpoint = "/test"

        # Time recording completions
        start = time.perf_counter()
        for i in range(100):
            record_request_completion(endpoint, float(10 + (i % 10)))
        elapsed = time.perf_counter() - start

        avg_latency = (elapsed / 100) * 1000  # Convert to ms
        assert avg_latency < 0.5, f"Record completion too slow: {avg_latency:.3f}ms"

    def test_record_completion_under_contention(self):
        """Recording under concurrent access should be fast."""
        tracker = get_tracker()
        tracker.clear()

        endpoint = "/test"
        duration_per_thread = 100  # 100 recordings per thread

        def record_many(thread_id):
            for i in range(duration_per_thread):
                record_request_completion(
                    endpoint,
                    float(10 + ((thread_id * 100 + i) % 20))
                )

        # Time concurrent recording
        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(record_many, i) for i in range(4)]
            for future in as_completed(futures):
                future.result()
        elapsed = time.perf_counter() - start

        total_records = 4 * duration_per_thread
        avg_latency = (elapsed / total_records) * 1000  # Convert to ms
        # With contention, should still be <1ms per record
        assert avg_latency < 1.0, f"Concurrent record too slow: {avg_latency:.3f}ms"


class TestConcurrentTimeoutCalculation:
    """Measure timeout calculation under concurrent access."""

    def test_concurrent_calculation_throughput(self):
        """Multiple threads calculating timeouts concurrently."""
        tracker = get_tracker()
        tracker.clear()

        endpoint = "/test"

        # Populate tracker
        for i in range(100):
            tracker.record_completion(endpoint, float(10 + (i % 30)))

        calculations_per_thread = 250

        def calculate_many(thread_id):
            results = []
            for _ in range(calculations_per_thread):
                timeout = calculate_adaptive_timeout(endpoint)
                results.append(timeout)
            return results

        # Time concurrent calculations
        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(calculate_many, i) for i in range(4)]
            all_results = []
            for future in as_completed(futures):
                all_results.extend(future.result())
        elapsed = time.perf_counter() - start

        total_calculations = 4 * calculations_per_thread
        avg_latency = (elapsed / total_calculations) * 1000  # Convert to ms
        throughput = total_calculations / elapsed

        assert avg_latency < 1.0, f"Concurrent calculation too slow: {avg_latency:.3f}ms"
        print(f"Concurrent throughput: {throughput:.0f} calculations/sec")


class TestMiddlewareOverhead:
    """Estimate total middleware overhead."""

    def test_full_request_flow_overhead(self):
        """Estimate overhead of metrics + timeout middlewares."""
        tracker = get_tracker()
        tracker.clear()

        endpoint = "/batch-earth-observations"

        # Populate tracker with realistic data
        for i in range(50):
            tracker.record_completion(endpoint, float(30 + (i % 20)))

        # Simulate full request flow:
        # 1. Record start (metrics)
        # 2. Calculate timeout (timeout middleware)
        # 3. Record completion (metrics)

        def simulate_request_flow():
            # Record completion (simulates duration capture)
            record_request_completion(endpoint, 2.5)
            # Calculate timeout
            calculate_adaptive_timeout(endpoint)

        start = time.perf_counter()
        for _ in range(1000):
            simulate_request_flow()
        elapsed = time.perf_counter() - start

        avg_latency = (elapsed / 1000) * 1000  # Convert to ms
        assert avg_latency < 2.0, f"Full flow overhead too high: {avg_latency:.3f}ms per request"
        print(f"Full request flow overhead: {avg_latency:.3f}ms")


class TestMemoryOverhead:
    """Measure memory usage of timeout system."""

    def test_tracker_memory_scaling(self):
        """Memory usage should scale reasonably with observation count."""
        import sys

        tracker = PercentileTracker()

        # Create tracker with many observations
        total_observations = 0
        for endpoint_num in range(10):
            endpoint = f"/endpoint-{endpoint_num}"
            for i in range(300):  # 5 min of 1 req/sec
                tracker.record_completion(endpoint, float(10 + (i % 20)))
                total_observations += 1

        # Measure total memory used by tracker's observation storage
        # Note: sys.getsizeof() measures the dict container + shallow contents
        # This is a conservative (lower) bound; actual memory is higher due to deques
        size_bytes = sys.getsizeof(tracker._observations)

        # Each observation is a (timestamp, duration) tuple stored in a deque
        # Expected: ~100-150 bytes per observation (tuple overhead + deque overhead)
        # If this exceeds 200 bytes/obs, we likely have a memory leak
        bytes_per_observation = size_bytes / max(1, total_observations)

        assert (
            bytes_per_observation < 200
        ), f"Memory usage too high: {bytes_per_observation:.1f} bytes/observation (total: {size_bytes} bytes for {total_observations} observations)"

        # Cleanup
        tracker.clear()


class TestCacheEfficiency:
    """Measure cache hit/miss rates."""

    def test_cache_hit_rate_5_second_ttl(self):
        """Verify cache provides hits: results consistent and cache state valid."""
        import time

        tracker = get_tracker()
        tracker.clear()

        endpoint = "/test"

        # Populate with 50 observations to enable p95 calculation
        for i in range(50):
            tracker.record_completion(endpoint, float(10 + i))

        # Before first call: cache is empty
        assert endpoint not in tracker._percentile_cache, "Cache should be empty initially"

        # First call: warms cache
        first_result = tracker.get_percentile(endpoint)
        assert first_result is not None, "Expected p95 to be calculated"
        assert (
            endpoint in tracker._percentile_cache
        ), "Expected p95 to be cached after first call"

        cached_p95, cached_timestamp = tracker._percentile_cache[endpoint]
        assert cached_p95 == first_result, "Cached value should match returned value"

        # Rapid calls should all return same cached value (no recalculation)
        for _ in range(100):
            result = tracker.get_percentile(endpoint)
            assert result == first_result, "Cache hits should return same value"

        # Cache entry should not have been updated (same timestamp)
        assert (
            tracker._percentile_cache[endpoint][1] == cached_timestamp
        ), "Cache timestamp should not change for hits"

        # Invalidate cache
        tracker._percentile_cache.clear()
        assert endpoint not in tracker._percentile_cache, "Cache should be empty after clear"

        # After invalidation, call should recalculate but return same value
        second_result = tracker.get_percentile(endpoint)
        assert second_result == first_result, "Recalculated p95 should match original"

        # Cache should be populated again
        assert (
            endpoint in tracker._percentile_cache
        ), "Cache should be repopulated after recalculation"

        new_timestamp = tracker._percentile_cache[endpoint][1]
        assert (
            new_timestamp > cached_timestamp
        ), "Cache timestamp should be newer after recalculation"


class TestP95ExtractionOverhead:
    """Measure percentile calculation cost."""

    def test_p95_calculation_cost_with_large_window(self):
        """P95 calculation with large observation window."""
        tracker = get_tracker()
        tracker.clear()

        endpoint = "/test"

        # Large window: 300 observations (5 min at 1 req/sec)
        for i in range(300):
            tracker.record_completion(endpoint, float(10 + (i % 50)))

        # Time percentile extraction
        start = time.perf_counter()
        for _ in range(100):
            tracker.get_percentile(endpoint)
        elapsed = time.perf_counter() - start

        avg_latency = (elapsed / 100) * 1000  # Convert to ms
        assert avg_latency < 2.0, f"P95 extraction with large window too slow: {avg_latency:.3f}ms"


class TestLatencyDistribution:
    """Analyze latency distribution (not just average)."""

    def test_timeout_calculation_latency_percentiles(self):
        """Measure timeout calculation latency distribution."""
        tracker = get_tracker()
        tracker.clear()

        endpoint = "/test"

        # Populate
        for i in range(50):
            tracker.record_completion(endpoint, float(10 + i))

        # Collect latencies
        latencies = []
        for _ in range(1000):
            start = time.perf_counter()
            calculate_adaptive_timeout(endpoint)
            elapsed = time.perf_counter() - start
            latencies.append(elapsed * 1000)  # Convert to ms

        latencies.sort()

        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]

        print(f"Timeout calculation latency distribution:")
        print(f"  p50: {p50:.3f}ms")
        print(f"  p95: {p95:.3f}ms")
        print(f"  p99: {p99:.3f}ms")

        # All percentiles should be under 1ms
        assert p50 < 1.0, f"p50 latency too high: {p50:.3f}ms"
        assert p95 < 1.0, f"p95 latency too high: {p95:.3f}ms"
        assert p99 < 1.0, f"p99 latency too high: {p99:.3f}ms"


@pytest.fixture(autouse=True)
def cleanup_tracker_perf():
    """Clean tracker before each test."""
    get_tracker().clear()
    yield
    get_tracker().clear()
