"""
Integration tests for main.py middleware and edge cases.

Covers CORS validation, locale resolution, request size limits, and timeout
scenarios in realistic HTTP request/response context. Uses shared fixtures
to reduce setup overhead.
"""

import asyncio
import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

from api.main import (
    TimeoutMiddleware,
    MetricsMiddleware,
    RequestSizeLimitMiddleware,
    _is_streaming_response_asgi,
    _resolve_accept_language,
    _parse_accept_language_tags,
)


@pytest.fixture
def base_app():
    """Create a minimal FastAPI app with test endpoints."""
    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/echo")
    async def echo(request_body: str = ""):
        return {"echo": request_body}

    @app.get("/stream")
    async def stream_endpoint():
        """Streaming endpoint that yields slowly."""
        async def generate():
            for i in range(3):
                await asyncio.sleep(0.01)
                yield f"data: chunk-{i}\n\n".encode()
        return StreamingResponse(generate(), media_type="text/event-stream")

    @app.get("/stream-slow")
    async def stream_slow_endpoint():
        """Streaming endpoint designed to timeout."""
        async def generate():
            yield b"data: starting\n\n"
            # This generator would sleep indefinitely, triggering timeout
            await asyncio.sleep(10)
            yield b"data: end\n\n"
        return StreamingResponse(generate(), media_type="text/event-stream")

    return app


@pytest.fixture
def app_with_middlewares(base_app):
    """Add all middlewares to the test app."""
    base_app.add_middleware(TimeoutMiddleware)
    base_app.add_middleware(MetricsMiddleware)
    base_app.add_middleware(RequestSizeLimitMiddleware)
    return base_app


@pytest.fixture
def client(app_with_middlewares):
    """Create a test client with all middlewares."""
    return TestClient(app_with_middlewares)


class TestLocaleResolution:
    """Tests for Accept-Language header parsing and locale resolution."""

    def test_empty_header_defaults_to_en(self):
        """Empty Accept-Language should default to 'en'."""
        result = _resolve_accept_language("")
        assert result == "en"

    def test_en_locale_supported(self):
        """'en' locale should be supported."""
        result = _resolve_accept_language("en")
        assert result == "en"

    def test_q_value_zero_skipped(self):
        """Q=0 means 'not acceptable' and should be skipped."""
        # en-US with q=0 should be skipped, falling back to default
        tags = _parse_accept_language_tags("en-US;q=0")
        # Should have no tags (q=0 excluded per RFC)
        assert len(tags) == 0

    def test_unsupported_locale_fallback_to_en(self):
        """Completely unsupported locale falls back to 'en'."""
        result = _resolve_accept_language("xyz")
        assert result == "en"

    def test_parse_accept_language_tags_multiple_tags(self):
        """Parse multiple language tags."""
        tags = _parse_accept_language_tags("en;q=0.8, fr;q=0.9")
        # Should have parsed both
        assert len(tags) == 2
        # Highest q first
        assert tags[0][0] == 0.9  # fr's q-value
        assert tags[1][0] == 0.8  # en's q-value

    def test_parse_accept_language_tags_equal_q_preserves_order(self):
        """Q-value sorting with equal values preserves original order."""
        tags = _parse_accept_language_tags("en;q=0.8, fr;q=0.8")
        # Both have 0.8
        assert len(tags) == 2
        assert tags[0][0] == 0.8 and tags[1][0] == 0.8
        # Order preserved for equal q
        assert tags[0][1] == "en" and tags[1][1] == "fr"

    def test_complex_header_parsing(self):
        """Complex real-world Accept-Language header."""
        result = _resolve_accept_language("en-US, fr;q=0.9")
        # Should resolve to a supported locale (en or en-US if supported)
        assert result in ["en", "en-US", "en-us"]


class TestCORSValidation:
    """Tests for CORS origin validation and logging."""

    def test_cors_insecure_http_warning_logged(self, caplog):
        """CORS with HTTP origins should log security warning."""
        with patch.dict(os.environ, {"ALLOWED_ORIGINS": "http://localhost:5173"}):
            # Re-import to trigger the validation code
            import importlib
            import api.main
            importlib.reload(api.main)

            # Should have logged warning about insecure HTTP
            assert any("SECURITY WARNING" in record.message for record in caplog.records)

    def test_default_cors_origins_allow_localhost(self, client):
        """Default CORS should allow localhost origins."""
        # Make request with default allowed origin
        response = client.get("/health", headers={"Origin": "http://localhost:5173"})
        # Response should succeed (CORS is allowed)
        assert response.status_code == 200


class TestRequestSizeLimit:
    """Tests for request body size enforcement."""

    def test_oversized_content_length_returns_413(self, client):
        """Request with Content-Length > limit should return 413."""
        # Set a small limit for testing
        with patch("api.main.MAX_REQUEST_SIZE_BYTES", 100):
            response = client.post(
                "/echo",
                headers={"Content-Length": "500"},
                content=b"x" * 500
            )
            # Should reject with 413
            assert response.status_code == 413

    def test_valid_request_size_allowed(self, client):
        """Request under size limit should be allowed."""
        with patch("api.main.MAX_REQUEST_SIZE_BYTES", 1000):
            response = client.post(
                "/echo",
                headers={"Content-Length": "50"},
                content=b"x" * 50
            )
            # Should succeed (or fail for other reasons, but not 413)
            assert response.status_code != 413


class TestStreamingDetection:
    """Tests for streaming response detection."""

    def test_response_without_content_length_is_streaming(self):
        """Response without Content-Length is streaming."""
        headers = [[b"content-type", b"text/event-stream"]]
        assert _is_streaming_response_asgi(headers) is True

    def test_response_with_transfer_encoding_chunked_is_streaming(self):
        """Response with Transfer-Encoding: chunked is streaming."""
        headers = [[b"transfer-encoding", b"chunked"]]
        assert _is_streaming_response_asgi(headers) is True

    def test_response_with_content_length_is_not_streaming(self):
        """Response with Content-Length is not streaming."""
        headers = [
            [b"content-type", b"application/json"],
            [b"content-length", b"42"],
        ]
        assert _is_streaming_response_asgi(headers) is False


class TestTimeoutMiddlewareScenarios:
    """Tests for timeout middleware in different scenarios."""

    def test_streaming_request_within_timeout_succeeds(self, client):
        """Streaming response within timeout should complete normally."""
        with patch("api.main.calculate_adaptive_timeout", return_value=1.0):
            response = client.get("/stream")
            assert response.status_code == 200
            # Verify streaming data received
            assert b"chunk-0" in response.content

    @pytest.mark.asyncio
    async def test_timeout_sets_scope_flag_on_timeout_error(self):
        """Timeout should set scope flag for metrics middleware."""
        async def slow_app(scope, receive, send):
            if scope["type"] != "http":
                return
            # Never sends response, just sleeps
            await asyncio.sleep(10)

        middleware = TimeoutMiddleware(slow_app)
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 8000),
        }

        sent_messages = []

        async def mock_send(message):
            sent_messages.append(message)

        async def mock_receive():
            await asyncio.sleep(1)

        with patch("api.main.calculate_adaptive_timeout", return_value=0.01):
            with patch("api.main.get_metrics"):
                with patch("api.main.logger"):
                    await middleware(scope, mock_receive, mock_send)

        # Verify scope flag was set
        assert scope.get("_timeout_middleware_generated") is True

        # Verify 503 response was sent
        response_start = next(
            (m for m in sent_messages if m.get("type") == "http.response.start"),
            None
        )
        assert response_start is not None
        assert response_start.get("status") == 503


class TestMiddlewareComposition:
    """Tests for multiple middlewares working together."""

    def test_health_endpoint_succeeds_through_all_middleware(self, client):
        """Basic request should pass through all middlewares successfully."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_streaming_response_completes_through_middleware(self, client):
        """Streaming response should work through metrics middleware."""
        response = client.get("/stream")
        assert response.status_code == 200
        # Verify streaming data
        assert b"chunk-0" in response.content

    def test_metrics_recorded_for_successful_request(self, client):
        """Metrics middleware should record successful requests."""
        with patch("api.main.get_metrics") as mock_metrics_class:
            mock_metrics = MagicMock()
            mock_metrics_class.return_value = mock_metrics

            response = client.get("/health")
            assert response.status_code == 200

            # Verify metrics were recorded
            assert mock_metrics.record_request_start.called
            assert mock_metrics.record_request.called
            assert mock_metrics.record_request_end.called


class TestMidStreamTimeoutScenario:
    """Tests specifically for timeout after response headers sent (lines 774-784)."""

    @pytest.mark.asyncio
    async def test_timeout_after_response_headers_sent_sets_flag(self):
        """When timeout occurs after headers sent, scope flag should be set.
        
        This tests the specific scenario in TimeoutMiddleware.else branch (lines 774-784)
        where asyncio.wait_for times out after response.start is sent.
        """
        # Create an ASGI app that sends headers then hangs
        async def hanging_app(scope, receive, send):
            if scope["type"] != "http":
                return
            # Send response start (streaming, no Content-Length)
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"text/event-stream"]],
            })
            # Then hang forever (simulating slow stream)
            await asyncio.sleep(100)

        middleware = TimeoutMiddleware(hanging_app)
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/test",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 8000),
        }

        sent_messages = []

        async def mock_send(message):
            sent_messages.append(message)

        async def mock_receive():
            await asyncio.sleep(1)

        with patch("api.main.calculate_adaptive_timeout", return_value=0.01):
            with patch("api.main.get_metrics"):
                with patch("api.main.logger"):
                    # Run middleware - should timeout during body transmission
                    await middleware(scope, mock_receive, mock_send)

        # Verify scope flag was set (indicates timeout-generated response)
        assert scope.get("_timeout_middleware_generated") is True

        # Verify that a response start was sent
        response_start = next(
            (m for m in sent_messages if m.get("type") == "http.response.start"),
            None
        )
        assert response_start is not None

    def test_metrics_called_on_mid_stream_timeout(self):
        """Verify metrics.record_timeout_exceeded called on mid-stream timeout."""
        with patch("api.main.get_metrics") as mock_metrics_class:
            mock_metrics = MagicMock()
            mock_metrics_class.return_value = mock_metrics

            async def run_test():
                async def hanging_app(scope, receive, send):
                    if scope["type"] != "http":
                        return
                    await send({
                        "type": "http.response.start",
                        "status": 200,
                        "headers": [[b"content-type", b"text/event-stream"]],
                    })
                    await asyncio.sleep(100)

                middleware = TimeoutMiddleware(hanging_app)
                scope = {
                    "type": "http",
                    "method": "GET",
                    "path": "/test",
                    "query_string": b"",
                    "headers": [],
                    "client": ("127.0.0.1", 8000),
                }

                sent = []

                async def mock_send(message):
                    sent.append(message)

                async def mock_receive():
                    await asyncio.sleep(1)

                with patch("api.main.calculate_adaptive_timeout", return_value=0.01):
                    with patch("api.main.logger"):
                        await middleware(scope, mock_receive, mock_send)

                # Verify timeout was recorded
                assert mock_metrics.record_timeout_exceeded.called

            asyncio.run(run_test())
