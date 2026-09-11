"""
Tests for metrics label extraction fixes.

Tests verify that:
1. /api/v1/contact-times is preserved as separate label (not grouped)
2. In-progress requests use proper label (not hardcoded "unknown")
3. Metric cardinality is bounded (prevents explosion)
"""

import pytest
from unittest.mock import MagicMock
from fastapi import Request
from api.main import _get_pre_route_label as extract_metric_label


class TestMetricLabelExtraction:
    """Test metric label extraction for bounded cardinality."""
    
    def test_contact_times_preserves_full_path(self):
        """Test that /api/v1/contact-times is preserved, not grouped.
        
        Bug: Before fix, /api/v1/contact-times/{event_id} would be grouped as
        /api/v1/contact-times (correct by accident), but the grouping logic
        extracts first segment which would be 'contact-times'.
        
        Fix: Explicitly check for /api/v1/contact-times before generic grouping
        to ensure it's preserved as /api/v1/contact-times (not grouped with other
        astronomical-events endpoints).
        """
        # Create mock request
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/contact-times/2025-09-07T00:00:00Z"
        
        # Should return /api/v1/contact-times
        label = extract_metric_label(request)
        
        assert label == "/api/v1/contact-times", \
            "contact-times should be preserved with full path"
    
    def test_contact_times_root_endpoint(self):
        """Test /api/v1/contact-times without path parameters."""
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/contact-times"
        
        label = extract_metric_label(request)
        
        assert label == "/api/v1/contact-times"
    
    def test_astronomical_events_grouped_separately(self):
        """Test that astronomical-events are grouped but separate from contact-times."""
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/astronomical-events?param=value"
        
        label = extract_metric_label(request)
        
        assert label == "/api/v1/astronomical-events"
        assert label != "/api/v1/contact-times"
    
    def test_batch_earth_observations_full_path(self):
        """Test that batch-earth-observations is a separate endpoint."""
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/batch-earth-observations"
        
        label = extract_metric_label(request)
        
        assert label == "/api/v1/batch-earth-observations"
    
    def test_cardinality_bounded_for_unknown_paths(self):
        """Test that unknown paths return 'unknown' to prevent cardinality explosion."""
        test_paths = [
            "/unknown/path/123/456",
            "/api/v2/some-endpoint",
            "/custom/endpoint",
            "/test/1/2/3/4/5"
        ]
        
        for path in test_paths:
            request = MagicMock(spec=Request)
            request.url.path = path
            
            label = extract_metric_label(request)
            
            assert label == "unknown", \
                f"Unknown path {path} should return 'unknown' to prevent cardinality explosion"
    
    def test_health_endpoint_preserved(self):
        """Test that utility endpoints are preserved."""
        utility_paths = ["/", "/health", "/cache-stats", "/rate-limit-stats"]
        
        for path in utility_paths:
            request = MagicMock(spec=Request)
            request.url.path = path
            
            label = extract_metric_label(request)
            
            assert label == path, f"Utility endpoint {path} should be preserved"
    
    def test_metrics_endpoint_recognized(self):
        """Test that metrics endpoint is recognized."""
        request = MagicMock(spec=Request)
        request.url.path = "/metrics"
        
        label = extract_metric_label(request)
        
        assert label == "/metrics"
    
    def test_api_v1_generic_endpoint_grouped_by_first_segment(self):
        """Test that other /api/v1/ endpoints are grouped by first segment."""
        # Test various first-segment endpoints
        test_cases = [
            ("/api/v1/moon-phase", "/api/v1/moon-phase"),
            ("/api/v1/sun-position", "/api/v1/sun-position"),
            ("/api/v1/mars-position", "/api/v1/mars-position"),
        ]
        
        for path, expected_label in test_cases:
            request = MagicMock(spec=Request)
            request.url.path = path
            
            label = extract_metric_label(request)
            
            assert label == expected_label, f"Path {path} should produce label {expected_label}"
    
    def test_api_v1_sub_routes_grouped(self):
        """Test that /api/v1/endpoint/sub routes are grouped under endpoint."""
        # These should be grouped under their first segment
        test_cases = [
            ("/api/v1/astronomical-events/search", "/api/v1/astronomical-events"),
            ("/api/v1/astronomical-events/filter", "/api/v1/astronomical-events"),
        ]
        
        for path, expected_label in test_cases:
            request = MagicMock(spec=Request)
            request.url.path = path
            
            label = extract_metric_label(request)
            
            assert label == expected_label, f"Sub-route {path} should group to {expected_label}"
    
    def test_empty_first_segment_handled(self):
        """Test that /api/v1/ (no first segment) returns unknown."""
        request = MagicMock(spec=Request)
        request.url.path = "/api/v1/"
        
        label = extract_metric_label(request)
        
        # Should return unknown or bounded label
        assert label in ["unknown", "/api/v1/"], "Empty segment should be handled"
    
    def test_contact_times_with_complex_path(self):
        """Test contact-times with various path patterns."""
        paths = [
            "/api/v1/contact-times/abc123",
            "/api/v1/contact-times/2025-09-07",
            "/api/v1/contact-times/event%2F123",
        ]
        
        for path in paths:
            request = MagicMock(spec=Request)
            request.url.path = path
            
            label = extract_metric_label(request)
            
            # All should resolve to /api/v1/contact-times
            assert label == "/api/v1/contact-times", \
                f"contact-times path {path} should map to /api/v1/contact-times"


class TestMetricLabelForInProgressRequests:
    """Test that in-progress requests use proper labels, not hardcoded unknown."""
    
    def test_in_progress_label_extraction(self):
        """Test that extract_metric_label is used for in-progress tracking.
        
        Bug: In-progress requests were hardcoded as unknown,
        so all concurrent requests appeared under one label.
        
        Fix: Use extract_metric_label() to get proper endpoint label
        """
        # Test various endpoint types
        test_cases = [
            ("/api/v1/batch-earth-observations", "/api/v1/batch-earth-observations"),
            ("/api/v1/astronomical-events", "/api/v1/astronomical-events"),
            ("/api/v1/contact-times/123", "/api/v1/contact-times"),
            ("/health", "/health"),
        ]
        
        for path, expected_label in test_cases:
            request = MagicMock(spec=Request)
            request.url.path = path
            
            label = extract_metric_label(request)
            
            assert label == expected_label, \
                f"in-progress request to {path} should have label {expected_label}, not 'unknown'"
    
    def test_in_progress_metrics_not_all_unknown(self):
        """Test that not all in-progress requests are labeled unknown.
        
        If this fails after the fix, it means the fix works:
        - Before fix: all requests -> unknown
        - After fix: requests grouped by endpoint type
        """
        endpoints = [
            "/api/v1/batch-earth-observations",
            "/api/v1/astronomical-events",
            "/api/v1/moon-phase",
            "/api/v1/contact-times/event1",
        ]
        
        labels = set()
        for path in endpoints:
            request = MagicMock(spec=Request)
            request.url.path = path
            
            label = extract_metric_label(request)
            labels.add(label)
        
        # Should have multiple distinct labels
        # (not all unknown)
        assert len(labels) > 1, "Different endpoints should have different labels"
        assert "unknown" not in labels, \
            "Known endpoints should not all map to 'unknown'"


class TestMetricLabelCardinality:
    """Test that metrics prevent cardinality explosion."""
    
    def test_bounded_cardinality(self):
        """Test that metric labels are bounded (finite set).
        
        Without bounding, Prometheus would exhaust memory as each unique
        request path creates a new metric series.
        
        Expected bounded labels:
        - /api/v1/batch-earth-observations
        - /api/v1/astronomical-events
        - /api/v1/contact-times
        - /api/v1/moon-phase
        - /api/v1/sun-position
        - /api/v1/{celestial-body}-position
        - /health
        - /cache-stats
        - /rate-limit-stats
        - /metrics
        - unknown
        """
        # Generate many variations of paths
        variations = []
        
        # Contact-times with many variations
        for i in range(100):
            variations.append(f"/api/v1/contact-times/event{i}")
        
        # Query parameters
        for i in range(100):
            variations.append(f"/api/v1/astronomical-events?param{i}=value{i}")
        
        # Sub-paths
        for i in range(100):
            variations.append(f"/api/v1/batch-earth-observations/result/{i}")
        
        # Extract labels
        labels = set()
        for path in variations:
            request = MagicMock(spec=Request)
            request.url.path = path
            
            label = extract_metric_label(request)
            labels.add(label)
        
        # Despite 300 variations, should have only ~3-4 unique labels
        # (bounded cardinality)
        assert len(labels) <= 5, \
            f"Should have bounded cardinality, got {len(labels)} unique labels from 300 paths"
        
        # Verify the labels are reasonable
        for label in labels:
            assert "/" in label or label == "unknown", \
                f"Label {label} should be a path or 'unknown'"
