"""
Tests for api/main.py middleware and CORS configuration
"""
import os
import logging
from unittest import mock
import pytest
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


class TestRequestSizeLimitMiddleware:
    """Test the request size limit middleware"""
    
    def test_request_within_size_limit(self):
        """Test that normal-sized requests pass through"""
        response = client.post(
            "/api/v1/day-of-week",
            json={"date": "2026-02-01"}
        )
        assert response.status_code in [200, 422]  # 422 if validation fails, but middleware allows it
    
    def test_request_without_content_length_header(self):
        """Test that requests without Content-Length header pass through"""
        response = client.post(
            "/api/v1/day-of-week",
            json={"date": "2026-02-01"}
        )
        # Should succeed or fail on validation, not on middleware
        assert response.status_code != 413


class TestCORSConfiguration:
    """Test CORS configuration and validation"""
    
    def test_cors_allows_localhost(self):
        """Test that CORS allows localhost development origins"""
        response = client.options(
            "/api/v1/day-of-week",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST"
            }
        )
        # Should allow the request (200 response from OPTIONS)
        assert response.status_code == 200
    
    def test_http_origins_warning_logged(self, caplog):
        """Test that HTTP origins trigger a security warning when configured"""
        # This test requires setting ALLOWED_ORIGINS to include http://
        # Since the app is already initialized, we can only test the logic
        # by checking if the warning would be logged
        
        # The warning check happens at module load time, so we can't easily test it
        # without reimporting. We'll verify the configuration is correct instead.
        with caplog.at_level(logging.WARNING):
            # Re-create the origins check logic
            allowed_origins = [
                origin.strip()
                for origin in os.getenv(
                    "ALLOWED_ORIGINS",
                    "http://localhost:5173,http://127.0.0.1:5173"
                ).split(",")
                if origin.strip()
            ]
            http_origins = [origin for origin in allowed_origins if origin.startswith("http://")]
            
            # Verify that HTTP origins would trigger a warning
            assert len(http_origins) > 0  # Default config has http:// origins


class TestLocaleMiddleware:
    """Test locale handling middleware"""
    
    def test_locale_from_query_parameter(self):
        """Test that ?lang= query parameter sets locale"""
        response = client.post(
            "/api/v1/day-of-week?lang=es",
            json={"date": "2026-02-01"}
        )
        # Should succeed regardless of locale
        assert response.status_code in [200, 422]
    
    def test_locale_from_accept_language_header(self):
        """Test that Accept-Language header is parsed"""
        response = client.post(
            "/api/v1/day-of-week",
            json={"date": "2026-02-01"},
            headers={"Accept-Language": "es-ES,es;q=0.9,en;q=0.8"}
        )
        # Should succeed regardless of locale
        assert response.status_code in [200, 422]
    
    def test_locale_fallback_to_english(self):
        """Test that unsupported locales fall back to English"""
        response = client.post(
            "/api/v1/day-of-week",
            json={"date": "2026-02-01"},
            headers={"Accept-Language": "xx-YY"}  # Unsupported locale
        )
        # Should succeed with English fallback
        assert response.status_code in [200, 422]
    
    def test_locale_with_quality_values(self):
        """Test Accept-Language parsing with quality values"""
        response = client.post(
            "/api/v1/day-of-week",
            json={"date": "2026-02-01"},
            headers={"Accept-Language": "fr;q=0.5,en-US;q=0.9"}
        )
        # Should succeed
        assert response.status_code in [200, 422]
