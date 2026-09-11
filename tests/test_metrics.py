"""
Tests for Prometheus metrics collection (Phase 3.2).

Validates:
- HTTP request tracking (duration, count, status)
- Cache performance metrics (hits, misses, memory)
- Rate limiting statistics
- Astropy computation tracking
- Error tracking
- Prometheus text format output
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.metrics import get_metrics, MetricsCollector


class TestMetricsCollector:
    """Test MetricsCollector singleton and metric recording."""

    def test_metrics_collector_singleton(self):
        """Test that MetricsCollector returns same instance."""
        metrics1 = get_metrics()
        metrics2 = get_metrics()
        assert metrics1 is metrics2

    def test_record_request(self):
        """Test recording HTTP request metrics."""
        metrics = get_metrics()
        # Should not raise
        metrics.record_request('/api/test', 'GET', 200, 0.5)
        metrics.record_request('/api/test', 'GET', 429, 0.1)

    def test_record_cache_hit(self):
        """Test recording cache hit."""
        metrics = get_metrics()
        # Should not raise
        metrics.record_cache_hit('/api/test')

    def test_record_cache_miss(self):
        """Test recording cache miss."""
        metrics = get_metrics()
        # Should not raise
        metrics.record_cache_miss('/api/test')

    def test_record_cache_memory(self):
        """Test recording cache memory metrics."""
        metrics = get_metrics()
        # Should not raise
        metrics.record_cache_memory('/api/test', 1024000, 100)

    def test_record_cache_eviction(self):
        """Test recording cache eviction."""
        metrics = get_metrics()
        # Should not raise
        metrics.record_cache_eviction('/api/test')

    def test_record_rate_limit_exceeded(self):
        """Test recording rate limit exceeded."""
        metrics = get_metrics()
        # Should not raise
        metrics.record_rate_limit_exceeded('/api/test')

    def test_record_astropy_call(self):
        """Test recording astropy function call."""
        metrics = get_metrics()
        # Should not raise
        metrics.record_astropy_call('/api/test', 'get_sun', 1)
        metrics.record_astropy_call('/api/test', 'get_body', 5)

    def test_record_event_processed(self):
        """Test recording event processing."""
        metrics = get_metrics()
        # Should not raise
        metrics.record_event_processed('/api/test', 'lunar', 1)
        metrics.record_event_processed('/api/test', 'solar', 3)

    def test_record_error(self):
        """Test recording error metric."""
        metrics = get_metrics()
        # Should not raise
        metrics.record_error('/api/test', 'validation_error', 400)
        metrics.record_error('/api/test', 'computation_error', 500)


class TestMetricsMiddleware:
    """Test Prometheus middleware integration."""

    def test_metrics_endpoint_exists(self):
        """Test that /metrics endpoint is registered."""
        client = TestClient(app)
        response = client.get('/metrics')
        assert response.status_code == 200
        assert response.headers['content-type'] == 'text/plain; version=0.0.4; charset=utf-8'

    def test_metrics_endpoint_returns_prometheus_text(self):
        """Test that /metrics returns valid Prometheus text format."""
        client = TestClient(app)
        response = client.get('/metrics')
        assert response.status_code == 200
        text = response.text

        # Should contain help and type declarations
        assert '# HELP' in text
        assert '# TYPE' in text
        
        # Should contain histogram metrics
        assert 'http_request_duration_seconds' in text

    def test_metrics_request_recording(self):
        """Test that HTTP requests are recorded by middleware."""
        client = TestClient(app)
        
        # Make a request to health endpoint
        response = client.get('/health')
        assert response.status_code == 200
        
        # Check metrics were recorded
        metrics_response = client.get('/metrics')
        text = metrics_response.text
        
        # Should have recorded request to /health
        assert 'http_requests_total' in text
        assert 'endpoint="/' in text or '/health' in text

    def test_metrics_root_endpoint(self):
        """Test that root endpoint is tracked in metrics."""
        client = TestClient(app)
        response = client.get('/')
        assert response.status_code == 200
        
        # Check metrics
        metrics_response = client.get('/metrics')
        assert metrics_response.status_code == 200
        assert 'http_requests_total' in metrics_response.text

    def test_metrics_cache_stats_endpoint(self):
        """Test that cache-stats endpoint is tracked."""
        client = TestClient(app)
        response = client.get('/cache-stats')
        assert response.status_code == 200
        
        # Check metrics
        metrics_response = client.get('/metrics')
        assert metrics_response.status_code == 200


class TestMetricsFormat:
    """Test Prometheus text format output."""

    def test_metrics_text_format_valid(self):
        """Test that metrics output is valid Prometheus text format."""
        metrics = get_metrics()
        text = metrics.get_metrics_text()
        
        assert isinstance(text, bytes)
        text_str = text.decode('utf-8')
        
        # Should contain HELP lines
        assert '# HELP' in text_str
        # Should contain TYPE lines
        assert '# TYPE' in text_str

    def test_metrics_contains_required_metrics(self):
        """Test that all required metrics are present."""
        metrics = get_metrics()
        text = metrics.get_metrics_text().decode('utf-8')
        
        required_metrics = [
            'http_request_duration_seconds',
            'http_requests_total',
            'http_requests_in_progress',
            'cache_hits_total',
            'cache_misses_total',
            'cache_memory_bytes',
            'cache_entry_count',
            'cache_evictions_total',
            'rate_limit_exceeded_total',
            'astropy_calls_total',
            'events_processed_total',
            'errors_total',
        ]
        
        for metric_name in required_metrics:
            assert metric_name in text, f"Missing metric: {metric_name}"

    def test_metrics_histogram_buckets(self):
        """Test that histogram has correct buckets."""
        metrics = get_metrics()
        text = metrics.get_metrics_text().decode('utf-8')
        
        # HTTP request duration histogram should have defined buckets
        assert 'http_request_duration_seconds_bucket' in text

    def test_metrics_labels_format(self):
        """Test that metrics have proper label format."""
        metrics = get_metrics()
        
        # Record some metrics
        metrics.record_request('/api/test', 'GET', 200, 0.5)
        metrics.record_cache_hit('/cache/endpoint')
        
        text = metrics.get_metrics_text().decode('utf-8')
        
        # Should have labels in braces
        assert 'endpoint=' in text
        assert 'method=' in text or 'cache_hits_total' in text


class TestCacheMetrics:
    """Test cache-related metrics tracking."""

    def test_cache_hit_counter(self):
        """Test that cache hits are counted."""
        metrics = MetricsCollector()
        
        # Record cache hits
        metrics.record_cache_hit('/api/events')
        metrics.record_cache_hit('/api/events')
        
        text = metrics.get_metrics_text().decode('utf-8')
        
        # Should show cache_hits_total
        assert 'cache_hits_total' in text

    def test_cache_miss_counter(self):
        """Test that cache misses are counted."""
        metrics = MetricsCollector()
        
        # Record cache misses
        metrics.record_cache_miss('/api/events')
        
        text = metrics.get_metrics_text().decode('utf-8')
        
        # Should show cache_misses_total
        assert 'cache_misses_total' in text

    def test_cache_memory_gauge(self):
        """Test cache memory usage gauge."""
        metrics = MetricsCollector()
        
        # Record cache memory
        metrics.record_cache_memory('/api/events', 1024000, 50)
        
        text = metrics.get_metrics_text().decode('utf-8')
        
        # Should show cache_memory_bytes gauge
        assert 'cache_memory_bytes' in text

    def test_cache_eviction_counter(self):
        """Test cache eviction tracking."""
        metrics = MetricsCollector()
        
        # Record evictions
        metrics.record_cache_eviction('/api/events')
        metrics.record_cache_eviction('/api/events')
        
        text = metrics.get_metrics_text().decode('utf-8')
        
        # Should show cache_evictions_total
        assert 'cache_evictions_total' in text


class TestAstropyMetrics:
    """Test astropy computation metrics."""

    def test_astropy_call_tracking(self):
        """Test tracking of astropy function calls."""
        metrics = MetricsCollector()
        
        # Record astropy calls
        metrics.record_astropy_call('/api/events', 'get_sun', 1)
        metrics.record_astropy_call('/api/events', 'get_body', 1)
        metrics.record_astropy_call('/api/events', 'get_moon_ecliptic_coords', 5)
        
        text = metrics.get_metrics_text().decode('utf-8')
        
        # Should show astropy_calls_total
        assert 'astropy_calls_total' in text

    def test_astropy_operation_labels(self):
        """Test that astropy operations are labeled correctly."""
        metrics = MetricsCollector()
        
        metrics.record_astropy_call('/api/events', 'get_sun', 1)
        metrics.record_astropy_call('/api/events', 'get_body', 3)
        
        text = metrics.get_metrics_text().decode('utf-8')
        
        # Should have operation labels
        assert 'operation=' in text


class TestEventProcessingMetrics:
    """Test event processing metrics."""

    def test_event_processing_tracking(self):
        """Test tracking of event processing."""
        metrics = MetricsCollector()
        
        # Record events processed
        metrics.record_event_processed('/api/events', 'lunar', 1)
        metrics.record_event_processed('/api/events', 'solar', 2)
        
        text = metrics.get_metrics_text().decode('utf-8')
        
        # Should show events_processed_total
        assert 'events_processed_total' in text

    def test_event_type_labels(self):
        """Test event type labeling."""
        metrics = MetricsCollector()
        
        metrics.record_event_processed('/api/events', 'lunar', 5)
        metrics.record_event_processed('/api/events', 'solar', 3)
        
        text = metrics.get_metrics_text().decode('utf-8')
        
        # Should have event_type labels
        assert 'event_type=' in text


class TestErrorMetrics:
    """Test error tracking metrics."""

    def test_error_recording(self):
        """Test recording errors by type."""
        metrics = MetricsCollector()
        
        # Record different error types
        metrics.record_error('/api/events', 'validation_error', 400)
        metrics.record_error('/api/events', 'computation_error', 500)
        metrics.record_error('/api/batch', 'timeout_error', 504)


class TestMetricsExceptionHandling:
    """Test metrics recording in exception and error paths."""

    def test_record_request_with_timeout_status(self):
        """Test recording timeout responses (504) as metrics."""
        metrics = get_metrics()
        # Should record timeout responses
        metrics.record_request('/api/test', 'GET', 504, 0.5)
        
        # Verify no exception is raised
        text = metrics.get_metrics_text().decode('utf-8')
        assert 'http_requests_total' in text

    def test_record_request_with_error_status(self):
        """Test recording error responses (500, 503) as metrics."""
        metrics = get_metrics()
        # Should record error responses
        metrics.record_request('/api/test', 'GET', 500, 0.1)
        metrics.record_request('/api/test', 'POST', 503, 0.2)
        
        # Verify no exception is raised
        text = metrics.get_metrics_text().decode('utf-8')
        assert 'http_requests_total' in text

    def test_record_multiple_error_codes(self):
        """Test recording various error status codes."""
        metrics = get_metrics()
        error_codes = [400, 401, 403, 404, 422, 429, 500, 502, 503, 504]
        
        for code in error_codes:
            metrics.record_request('/api/test', 'GET', code, 0.1)
        
        # Verify metrics include all status codes
        text = metrics.get_metrics_text().decode('utf-8')
        assert 'http_requests_total' in text
        # All codes should appear in metrics (they won't necessarily all appear
        # in text representation, but recording should not crash)

    def test_metrics_recorded_for_all_status_classes(self):
        """Test that metrics are recorded for 1xx through 5xx responses."""
        metrics = get_metrics()
        
        # Record representative status codes from each class
        status_codes = [200, 201, 301, 400, 401, 500, 502, 503]
        
        for status in status_codes:
            metrics.record_request('/api/test', 'GET', status, 0.1)
        
        text = metrics.get_metrics_text().decode('utf-8')
        assert 'http_requests_total' in text
        # Should have metrics for successful and error responses
        assert b'http_requests_total' in metrics.get_metrics_text()
        
        text = metrics.get_metrics_text().decode('utf-8')
        
        # Should show errors_total
        assert 'errors_total' in text

    def test_error_type_labels(self):
        """Test error type labeling."""
        metrics = MetricsCollector()
        
        metrics.record_error('/api/test', 'validation_error', 400)
        
        text = metrics.get_metrics_text().decode('utf-8')
        
        # Should have error_type and status labels
        assert 'error_type=' in text
        assert 'status=' in text


class TestRateLimitingMetrics:
    """Test rate limiting metrics."""

    def test_rate_limit_exceeded_tracking(self):
        """Test tracking of rate limit exceeded responses."""
        metrics = MetricsCollector()
        
        # Record rate limits
        metrics.record_rate_limit_exceeded('/api/events')
        metrics.record_rate_limit_exceeded('/api/batch')
        metrics.record_rate_limit_exceeded('/api/events')
        
        text = metrics.get_metrics_text().decode('utf-8')
        
        # Should show rate_limit_exceeded_total
        assert 'rate_limit_exceeded_total' in text


class TestRequestLevelMetrics:
    """Test request-level HTTP metrics."""

    def test_request_start_end_tracking(self):
        """Test in-progress request tracking."""
        metrics = MetricsCollector()
        
        # Record requests in progress
        metrics.record_request_start('/api/events')
        metrics.record_request_start('/api/events')
        metrics.record_request_end('/api/events')
        
        text = metrics.get_metrics_text().decode('utf-8')
        
        # Should show http_requests_in_progress gauge
        assert 'http_requests_in_progress' in text
