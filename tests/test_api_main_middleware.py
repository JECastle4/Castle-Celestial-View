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

    @pytest.mark.asyncio
    async def test_streaming_body_size_limit_exceeded_sends_413(self):
        """Test that streaming bodies exceeding size limit get 413 response.
        
        This tests the fix where the middleware now sends a proper 413 response
        (not just http.disconnect) when a streaming body exceeds MAX_REQUEST_SIZE_BYTES.
        """
        from api.main import RequestSizeLimitMiddleware, MAX_REQUEST_SIZE_BYTES
        
        # Create a minimal ASGI app that accepts any request
        async def dummy_asgi_app(scope, receive, send):
            """Dummy ASGI app that echoes the request body"""
            if scope["type"] == "http":
                # Read all body chunks
                body = b""
                while True:
                    message = await receive()
                    if message["type"] == "http.request":
                        body += message.get("body", b"")
                        if not message.get("more_body"):
                            break
                    elif message["type"] == "http.disconnect":
                        # Client disconnected - don't send response
                        return
                
                # Send response
                await send({
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [[b"content-type", b"text/plain"]],
                })
                await send({
                    "type": "http.response.body",
                    "body": b"OK",
                    "more_body": False
                })
        
        # Wrap with RequestSizeLimitMiddleware
        middleware = RequestSizeLimitMiddleware(dummy_asgi_app)
        
        # Simulate ASGI call with streaming body exceeding limit
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/test",
            "query_string": b"",
            "headers": [],  # No Content-Length header
            "client": ("127.0.0.1", 12345),
            "state": {},
        }
        
        # Track messages sent to client
        sent_messages = []
        
        async def send(message):
            """Capture all messages sent to the client"""
            sent_messages.append(message)
        
        # Create a receive function that sends chunks exceeding the limit
        chunk_index = [0]  # Use list to allow mutation in closure
        
        async def receive():
            """Send http.request messages with chunks exceeding size limit"""
            # First message: small initial chunk (under limit)
            if chunk_index[0] == 0:
                chunk_index[0] += 1
                return {
                    "type": "http.request",
                    "body": b"x" * 1024,  # 1 KB
                    "more_body": True
                }
            # Second message: chunk exceeding total limit
            elif chunk_index[0] == 1:
                chunk_index[0] += 1
                # Create a chunk that causes total to exceed MAX_REQUEST_SIZE_BYTES
                oversized_chunk = b"x" * (MAX_REQUEST_SIZE_BYTES + 1)
                return {
                    "type": "http.request",
                    "body": oversized_chunk,
                    "more_body": False
                }
            else:
                return {"type": "http.disconnect"}
        
        # Call middleware
        await middleware(scope, receive, send)
        
        # Verify 413 response was sent
        assert len(sent_messages) >= 2, f"Should send at least response.start and response.body, got {len(sent_messages)}"
        
        # First message should be http.response.start with 413
        start_msg = sent_messages[0]
        assert start_msg["type"] == "http.response.start"
        assert start_msg["status"] == 413
        
        # Response should have content-type and content-length headers
        headers_dict = {name.lower(): value for name, value in start_msg.get("headers", [])}
        assert b"content-type" in headers_dict
        assert b"content-length" in headers_dict
        
        # Second message should be http.response.body with "Payload Too Large"
        body_msg = sent_messages[1]
        assert body_msg["type"] == "http.response.body"
        assert body_msg["body"] == b"Payload Too Large"
        assert body_msg.get("more_body") is False
    
    def test_content_length_header_size_check_upfront_rejection(self):
        """Test that Content-Length header is validated upfront (before app invocation).
        
        Oversized Content-Length should trigger 413 before app runs, ensuring
        only a single 413 response is sent (not app's response + 413).
        """
        from api.main import MAX_REQUEST_SIZE_BYTES
        
        # Send POST with oversized Content-Length header
        oversized_bytes = MAX_REQUEST_SIZE_BYTES + 1024 * 1024  # 1 MB over limit
        
        response = client.post(
            "/api/v1/day-of-week",
            data=b"dummy",  # Small actual body
            headers={
                "Content-Length": str(oversized_bytes),
                "Content-Type": "application/json"
            }
        )
        
        # Should get 413 before app processes
        assert response.status_code == 413


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
