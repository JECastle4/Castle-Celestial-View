"""
Tests for timeout oscillation fix (Issue: separate timeout tracking).

Verifies that timeout samples are tracked separately from normal completions
and do not skew p95 calculation, preventing degraded→normal→degraded oscillation.

Tests the is_timeout parameter and _timeout_observations tracker.
"""

import pytest
import time
from collections import deque
from api.timeout_logic import (
    PercentileTracker,
    calculate_adaptive_timeout,
    record_request_completion,
    get_timeout_count,
    get_tracker,
)
from api.timeout_config import BASE_TIMEOUTS, TIMEOUT_MULTIPLIERS


class TestTimeoutObservationsTracking:
    """Test that timeout observations are tracked separately."""

    def test_timeout_samples_route_to_separate_tracker(self):
        """Test that is_timeout=True routes to _timeout_observations."""
        tracker = PercentileTracker()
        
        # Record normal completion
        tracker.record_completion('/test', 5.0, is_timeout=False)
        
        # Record timeout completion
        tracker.record_completion('/test', 40.0, is_timeout=True)
        
        # Normal observations should have 1 entry
        assert len(tracker._observations.get('/test', [])) == 1
        
        # Timeout observations should have 1 entry
        assert len(tracker._timeout_observations.get('/test', [])) == 1

    def test_timeout_samples_excluded_from_p95_calculation(self):
        """Test that timeout samples do not influence p95 calculation."""
        tracker = PercentileTracker()
        
        # Add 100 normal observations (values 1-100)
        for i in range(1, 101):
            tracker.record_completion('/test', float(i), is_timeout=False)
        
        p95_without_timeouts = tracker.get_percentile('/test')
        assert p95_without_timeouts is not None
        # Should be around 95 for values 1-100
        assert 93 < p95_without_timeouts < 97
        
        # Clear cache so we recalculate (cache TTL prevents immediate recalc)
        tracker._percentile_cache.clear()
        
        # Add timeout samples with very high values (would skew p95 down if included)
        # These should be excluded from calculation
        for i in range(20):
            tracker.record_completion('/test', 999.0, is_timeout=True)
        
        p95_with_timeouts = tracker.get_percentile('/test')
        assert p95_with_timeouts is not None
        
        # P95 should remain similar (timeouts excluded)
        # If timeouts were included, p95 would drop significantly
        assert abs(p95_with_timeouts - p95_without_timeouts) < 5

    def test_get_timeout_count_returns_timeout_sample_count(self):
        """Test that get_timeout_count() returns accurate timeout count."""
        tracker = PercentileTracker()
        
        # Record normal completions (should not count)
        for i in range(10):
            tracker.record_completion('/test', float(i), is_timeout=False)
        
        # Record timeout completions
        for i in range(5):
            tracker.record_completion('/test', float(i), is_timeout=True)
        
        timeout_count = tracker.get_timeout_count('/test')
        assert timeout_count == 5

    def test_get_timeout_count_for_endpoint_without_timeouts(self):
        """Test get_timeout_count returns 0 for endpoint with no timeouts."""
        tracker = PercentileTracker()
        
        # Add only normal completions
        for i in range(20):
            tracker.record_completion('/test', float(i), is_timeout=False)
        
        timeout_count = tracker.get_timeout_count('/test')
        assert timeout_count == 0

    def test_get_timeout_count_for_unknown_endpoint(self):
        """Test get_timeout_count returns 0 for unknown endpoint."""
        tracker = PercentileTracker()
        timeout_count = tracker.get_timeout_count('/unknown')
        assert timeout_count == 0


class TestTimeoutOscillationPrevention:
    """Test that timeout samples don't cause degraded→normal oscillation."""

    def test_timeout_samples_dont_lower_p95_below_degraded_threshold(self):
        """Test the core oscillation scenario: timeouts shouldn't hide overload.
        
        Scenario:
        1. Add normal observations at p95 = 100s (well above degraded threshold of 96s)
        2. System times out at 0.7 × base = 84s
        3. Timeout samples at 84s should NOT lower p95 below 96s
        4. Without fix: p95 would drop, triggering normal→degraded flip
        """
        tracker = PercentileTracker()
        endpoint = '/api/v1/batch-earth-observations'
        base = BASE_TIMEOUTS['expensive']  # 120s
        degraded_threshold = base * 0.8  # 96s
        
        # Add normal observations with p95 around 100-110s (degraded)
        # Use range 50-150 to get p95 around 100+ 
        for i in range(50, 150):
            tracker.record_completion(endpoint, float(i), is_timeout=False)
        
        p95_before = tracker.get_percentile(endpoint)
        assert p95_before is not None
        assert p95_before > degraded_threshold  # Confirms degraded state
        
        # Clear cache to force recalculation
        tracker._percentile_cache.clear()
        
        # Add timeout samples at 0.7 * base = 84s (would lower p95 if included)
        timeout_at_degraded = base * 0.7  # 84s
        for i in range(20):
            tracker.record_completion(endpoint, timeout_at_degraded, is_timeout=True)
        
        p95_after = tracker.get_percentile(endpoint)
        assert p95_after is not None
        
        # P95 should remain above degraded threshold (timeouts excluded)
        assert p95_after > degraded_threshold
        
        # Verify timeout count increased
        assert tracker.get_timeout_count(endpoint) == 20

    def test_timeout_samples_don_affect_timeout_calculation(self):
        """Test that timeout samples don't trigger timeout multiplier changes."""
        get_tracker().clear()
        
        endpoint = '/api/v1/batch-earth-observations'
        base = BASE_TIMEOUTS['expensive']  # 120s
        
        # Add normal observations where p95 is in degraded range (> 96s)
        # Use range 50-150 to ensure p95 > 96
        for i in range(50, 150):
            get_tracker().record_completion(endpoint, float(i), is_timeout=False)
        
        # Calculate timeout with degraded state
        timeout_degraded = calculate_adaptive_timeout(endpoint)
        expected_degraded = base * TIMEOUT_MULTIPLIERS['degraded']
        assert timeout_degraded == expected_degraded
        
        # Add many timeout samples (would lower p95 if included)
        get_tracker()._percentile_cache.clear()
        for i in range(50):
            get_tracker().record_completion(
                endpoint, base * 0.5, is_timeout=True  # Very low timeouts
            )
        
        # Timeout should remain degraded (not flip to normal)
        timeout_after_timeouts = calculate_adaptive_timeout(endpoint)
        assert timeout_after_timeouts == expected_degraded

    def test_timeout_observations_pruned_by_sliding_window(self):
        """Test that old timeout observations are pruned like normal ones."""
        tracker = PercentileTracker()
        
        # Record timeout observations
        for i in range(5):
            tracker.record_completion('/test', 40.0, is_timeout=True)
        
        assert tracker.get_timeout_count('/test') == 5
        
        # Record normal observations too (needed for get_percentile to work)
        for i in range(1, 101):
            tracker.record_completion('/test', float(i), is_timeout=False)
        
        # Manually set old timestamps on some timeout observations
        with tracker._lock:
            if '/test' in tracker._timeout_observations:
                old_time = time.time() - 301  # 5 min + 1 sec ago
                # Replace first observation with old timestamp
                old_obs = list(tracker._timeout_observations['/test'])
                if old_obs:
                    old_obs[0] = (old_time, old_obs[0][1])
                    tracker._timeout_observations['/test'] = deque(old_obs)
        
        # Trigger pruning by calling get_percentile
        tracker.get_percentile('/test')
        
        # After pruning, old timeout observation should be removed
        # Should have 4 remaining timeout observations (1 old one removed)
        remaining = tracker.get_timeout_count('/test')
        assert remaining == 4

    def test_clear_clears_both_normal_and_timeout_observations(self):
        """Test that clear() removes both normal and timeout observations."""
        tracker = PercentileTracker()
        
        # Add normal and timeout observations
        for i in range(30):
            tracker.record_completion('/test', float(i), is_timeout=False)
            tracker.record_completion('/test', float(i + 100), is_timeout=True)
        
        assert len(tracker._observations.get('/test', [])) == 30
        assert tracker.get_timeout_count('/test') == 30
        
        tracker.clear()
        
        assert len(tracker._observations.get('/test', [])) == 0
        assert tracker.get_timeout_count('/test') == 0
        assert tracker.get_percentile('/test') is None


class TestModuleLevelTimeoutCount:
    """Test module-level get_timeout_count() wrapper function."""

    def test_module_level_get_timeout_count(self):
        """Test that module-level get_timeout_count() delegates to tracker."""
        get_tracker().clear()
        
        # Record some timeouts
        for i in range(5):
            record_request_completion('/test', 30.0, is_timeout=True)
        
        # Record some normal completions
        for i in range(10):
            record_request_completion('/test', 10.0, is_timeout=False)
        
        # get_timeout_count should return only timeout count
        timeout_count = get_timeout_count('/test')
        assert timeout_count == 5


class TestRecordRequestCompletionWithTimeout:
    """Test the module-level record_request_completion() function."""

    def test_record_request_completion_accepts_is_timeout_parameter(self):
        """Test that record_request_completion() accepts is_timeout parameter."""
        get_tracker().clear()
        
        # Should not raise an error
        record_request_completion('/test', 10.0, is_timeout=False)
        record_request_completion('/test', 40.0, is_timeout=True)
        
        # Verify tracking
        assert len(get_tracker()._observations.get('/test', [])) == 1
        assert get_timeout_count('/test') == 1

    def test_is_timeout_defaults_to_false(self):
        """Test that is_timeout defaults to False if not provided."""
        get_tracker().clear()
        
        # Call without is_timeout parameter
        record_request_completion('/test', 10.0)
        
        # Should route to normal observations
        assert len(get_tracker()._observations.get('/test', [])) == 1
        assert get_timeout_count('/test') == 0
