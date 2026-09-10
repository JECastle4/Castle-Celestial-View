"""
Adaptive timeout calculation based on observed system performance.

Maintains a sliding window of recent request completion times to calculate
the p95 (95th percentile). Timeouts adjust dynamically based on whether
the system is fast, healthy, or degraded under load.

Uses in-memory percentile tracking (Option C) for clean, performant calculation.
"""

import time
from collections import deque
from threading import Lock
from typing import Optional

from api.timeout_config import (
    get_endpoint_cost,
    get_base_timeout,
    HARD_LIMIT_SECONDS,
    PERCENTILE_TO_TRACK,
    PERCENTILE_CACHE_TTL_SECONDS,
    SLIDING_WINDOW_SECONDS,
    TIMEOUT_MULTIPLIERS,
)


class PercentileTracker:
    """
    Thread-safe in-memory tracker for request completion times.

    Maintains a sliding window of recent completion times per endpoint.
    Calculates p95 (95th percentile) efficiently.
    """

    def __init__(self):
        """Initialize percentile tracker."""
        # {endpoint: deque of (timestamp, completion_time) tuples}
        self._observations = {}
        self._lock = Lock()
        # {endpoint: (p95_value, timestamp_calculated)}
        self._percentile_cache = {}

    def record_completion(self, endpoint: str, duration_seconds: float) -> None:
        """
        Record a request completion time.

        Args:
            endpoint: Request path (e.g., '/batch-earth-observations')
            duration_seconds: How long the request took
        """
        if duration_seconds < 0:
            return  # Ignore invalid observations

        now = time.time()

        with self._lock:
            if endpoint not in self._observations:
                self._observations[endpoint] = deque()

            # Add observation with timestamp
            self._observations[endpoint].append((now, duration_seconds))

            # Remove old observations outside sliding window
            cutoff = now - SLIDING_WINDOW_SECONDS
            while (
                self._observations[endpoint]
                and self._observations[endpoint][0][0] < cutoff
            ):
                self._observations[endpoint].popleft()

    def get_percentile(self, endpoint: str) -> Optional[float]:
        """
        Get p95 (95th percentile) completion time for endpoint.

        Uses cached value if calculated within last 5 seconds,
        otherwise recalculates from observations.

        Args:
            endpoint: Request path

        Returns:
            p95 completion time in seconds, or None if insufficient data
        """
        now = time.time()

        with self._lock:
            # Check cache
            if endpoint in self._percentile_cache:
                cached_p95, cached_time = self._percentile_cache[endpoint]
                if now - cached_time < PERCENTILE_CACHE_TTL_SECONDS:
                    return cached_p95  # Cache hit

            # Not cached or cache expired - recalculate
            if (
                endpoint not in self._observations
                or len(self._observations[endpoint]) < 10
            ):
                # Insufficient data (need at least 10 observations for meaningful p95)
                return None

            # Extract durations only (discard timestamps)
            durations = [
                duration for _, duration in self._observations[endpoint]
            ]
            durations.sort()

            # Calculate p95 index
            # For p95: need at least 20 samples for 1 sample at top 5%
            # Use linear interpolation for fractional indices
            n = len(durations)
            if n < 20:
                # Insufficient data, return None (cold start)
                return None

            p95_index = PERCENTILE_TO_TRACK * (n - 1)
            lower_idx = int(p95_index)
            upper_idx = min(lower_idx + 1, n - 1)
            fraction = p95_index - lower_idx

            # Linear interpolation between adjacent values
            p95 = (
                durations[lower_idx] * (1 - fraction)
                + durations[upper_idx] * fraction
            )

            # Cache result
            self._percentile_cache[endpoint] = (p95, now)

            return p95

    def clear(self) -> None:
        """Clear all observations and cache (for testing/memory management)."""
        with self._lock:
            self._observations.clear()
            self._percentile_cache.clear()


# Global singleton instance
_percentile_tracker = PercentileTracker()


def record_request_completion(endpoint: str, duration_seconds: float) -> None:
    """
    Record a request completion time for timeout calculation.

    Called by the timeout middleware after a request completes.

    Args:
        endpoint: Request path
        duration_seconds: Request duration in seconds
    """
    _percentile_tracker.record_completion(endpoint, duration_seconds)


def calculate_adaptive_timeout(endpoint: str) -> float:
    """
    Calculate adaptive timeout based on observed system performance.

    Strategy:
    1. Get p95 (95th percentile) completion time from sliding window
    2. Compare p95 to base timeout for this endpoint tier
    3. Scale timeout up (generous) or down (degraded) accordingly
    4. Apply hard ceiling to prevent runaway requests

    Args:
        endpoint: Request path

    Returns:
        Timeout in seconds (always > 0, never exceeds HARD_LIMIT_SECONDS)
    """
    cost = get_endpoint_cost(endpoint)
    base_timeout = get_base_timeout(cost)

    # Get observed p95 completion time
    p95 = _percentile_tracker.get_percentile(endpoint)

    if p95 is None:
        # Cold start: no sufficient data yet, use base timeout
        return float(base_timeout)

    # Determine scaling factor based on p95 vs base
    if p95 < base_timeout * 0.5:
        # System is fast, be generous
        multiplier = TIMEOUT_MULTIPLIERS["generous"]
    elif p95 < base_timeout * 0.8:
        # System is healthy, use base
        multiplier = TIMEOUT_MULTIPLIERS["normal"]
    else:
        # System is degraded, tighten
        multiplier = TIMEOUT_MULTIPLIERS["degraded"]

    # Calculate timeout
    calculated_timeout = base_timeout * multiplier

    # Apply hard ceiling
    final_timeout = min(calculated_timeout, HARD_LIMIT_SECONDS)

    # Ensure timeout is always positive
    return max(final_timeout, 0.1)


def get_tracker() -> PercentileTracker:
    """Get the global percentile tracker (mainly for testing)."""
    return _percentile_tracker
