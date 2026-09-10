"""
Prometheus metrics collection for API monitoring.

Provides MetricsCollector singleton that tracks:
- HTTP request latency/throughput (via middleware)
- Cache performance (hits, misses, memory, evictions)
- Rate limiting statistics
- Astropy computation metrics
- Error tracking

Ultra-lightweight (~2-3 μs per request overhead).
"""

from typing import Optional
from prometheus_client import (
    Counter, Histogram, Gauge, REGISTRY, generate_latest
)


class MetricsCollector:
    """
    Singleton metrics collector using prometheus_client.

    Tracks request-level HTTP metrics via middleware, cache performance from the
    response cache decorator, rate limiting hits, and computation metrics from
    service functions.
    """

    _instance: Optional['MetricsCollector'] = None
    _initialized: bool = False

    def __new__(cls) -> 'MetricsCollector':
        """Singleton pattern - return existing instance or create new one."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize metrics (only once per singleton)."""
        if MetricsCollector._initialized:
            return
        MetricsCollector._initialized = True

        # Request-level metrics (HTTP middleware)
        self.http_request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            labelnames=['endpoint', 'method', 'status'],
            buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60),
        )

        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            labelnames=['endpoint', 'method', 'status'],
        )

        self.http_requests_in_progress = Gauge(
            'http_requests_in_progress',
            'HTTP requests currently in progress',
            labelnames=['endpoint'],
        )

        # Cache metrics (instrumented via cache decorator)
        self.cache_hits_total = Counter(
            'cache_hits_total',
            'Total cache hits',
            labelnames=['endpoint'],
        )

        self.cache_misses_total = Counter(
            'cache_misses_total',
            'Total cache misses',
            labelnames=['endpoint'],
        )

        self.cache_memory_bytes = Gauge(
            'cache_memory_bytes',
            'Cache memory usage in bytes',
            labelnames=['endpoint'],
        )

        self.cache_entry_count = Gauge(
            'cache_entry_count',
            'Number of entries in cache',
            labelnames=['endpoint'],
        )

        self.cache_evictions_total = Counter(
            'cache_evictions_total',
            'Total cache evictions (LRU)',
            labelnames=['endpoint'],
        )

        # Rate limiting metrics
        self.rate_limit_exceeded_total = Counter(
            'rate_limit_exceeded_total',
            'Total rate limit exceeded responses (429)',
            labelnames=['endpoint'],
        )

        # Astropy computation metrics
        self.astropy_calls_total = Counter(
            'astropy_calls_total',
            'Total astropy function calls',
            labelnames=['endpoint', 'operation'],
        )

        # Event processing metrics (for streaming/batch endpoints)
        self.events_processed_total = Counter(
            'events_processed_total',
            'Total events processed',
            labelnames=['endpoint', 'event_type'],
        )

        # Error metrics
        self.errors_total = Counter(
            'errors_total',
            'Total errors by type',
            labelnames=['endpoint', 'error_type', 'status'],
        )

    def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        """Record HTTP request metrics."""
        status = str(status_code)
        self.http_request_duration.labels(
            endpoint=endpoint, method=method, status=status
        ).observe(duration_seconds)
        self.http_requests_total.labels(
            endpoint=endpoint, method=method, status=status
        ).inc()

    def record_request_start(self, endpoint: str) -> None:
        """Increment in-progress request counter."""
        self.http_requests_in_progress.labels(endpoint=endpoint).inc()

    def record_request_end(self, endpoint: str) -> None:
        """Decrement in-progress request counter."""
        self.http_requests_in_progress.labels(endpoint=endpoint).dec()

    def record_cache_hit(self, endpoint: str) -> None:
        """Record cache hit."""
        self.cache_hits_total.labels(endpoint=endpoint).inc()

    def record_cache_miss(self, endpoint: str) -> None:
        """Record cache miss."""
        self.cache_misses_total.labels(endpoint=endpoint).inc()

    def record_cache_memory(self, endpoint: str, bytes_used: int, entry_count: int) -> None:
        """Update cache memory and entry count gauges."""
        self.cache_memory_bytes.labels(endpoint=endpoint).set(bytes_used)
        self.cache_entry_count.labels(endpoint=endpoint).set(entry_count)

    def record_cache_eviction(self, endpoint: str) -> None:
        """Record cache eviction event."""
        self.cache_evictions_total.labels(endpoint=endpoint).inc()

    def record_rate_limit_exceeded(self, endpoint: str) -> None:
        """Record rate limit exceeded (429 response)."""
        self.rate_limit_exceeded_total.labels(endpoint=endpoint).inc()

    def record_astropy_call(self, endpoint: str, operation: str, count: int = 1) -> None:
        """Record astropy function call."""
        self.astropy_calls_total.labels(endpoint=endpoint, operation=operation).inc(count)

    def record_event_processed(self, endpoint: str, event_type: str, count: int = 1) -> None:
        """Record event processing."""
        self.events_processed_total.labels(endpoint=endpoint, event_type=event_type).inc(count)

    def record_error(
        self,
        endpoint: str,
        error_type: str,
        status_code: int = 500,
    ) -> None:
        """Record error occurrence."""
        status = str(status_code)
        self.errors_total.labels(
            endpoint=endpoint, error_type=error_type, status=status
        ).inc()

    def get_metrics_text(self) -> bytes:
        """Return metrics in Prometheus text format."""
        return generate_latest(REGISTRY)


# Singleton instance
_METRICS_INSTANCE = None


def get_metrics() -> MetricsCollector:
    """Get or create the metrics collector singleton."""
    global _METRICS_INSTANCE  # pylint: disable=global-statement
    if _METRICS_INSTANCE is None:
        _METRICS_INSTANCE = MetricsCollector()
    return _METRICS_INSTANCE


# Helper for test mode detection (consistent with rate_limiter.py)
def _is_test_mode() -> bool:
    """Check if running in test mode."""
    import sys  # pylint: disable=import-outside-toplevel
    return 'pytest' in sys.modules or 'unittest' in sys.modules
