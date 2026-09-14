"""
Main FastAPI application for Astronomy API
"""
import asyncio
import logging
import time
import os

from astropy.utils import iers
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from api.cache import get_cache_stats
from api.i18n import SUPPORTED_LOCALES, set_request_locale
from api.metrics import get_metrics
from api.middleware.streaming_registry import StreamingMetadata
from api.rate_limiter import limiter, rate_limit_exception_handler, get_rate_limit_stats
from api.rate_limiter import MockLimiter
from api.routes import router
from api.routes.metrics import router as metrics_router
from api.timeout_logic import calculate_adaptive_timeout, record_request_completion

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Disable astropy's automatic IERS data download.  CI runners typically have
# no outbound network access, causing every request to block for the full
# timeout before falling back to the bundled IERS-A table anyway.  The bundled
# data is accurate enough for all calculations this API performs.
# auto_max_age=None suppresses the "predictive values > 30 days old" error
# that astropy raises when auto_download is False and the bundled table ages.
iers.conf.auto_download = False
iers.conf.auto_max_age = None

# Note: API version is independent from the release version
# (pyproject.toml + frontend/package.json).
# The API version reflects breaking changes to the API contract;
# many releases may have no API changes.
app = FastAPI(
    title="Astronomy API",
    description=(
        "API for astronomical calculations including day of week, "
        "sun/moon/Venus positions, and more"
    ),
    version="0.2.0"
)

# Allowlist of known first-segment values for /api/v1/ endpoints
# Used by _get_pre_route_label() to prevent cardinality explosion in metrics
# Maps to body-position, event-detection, and batch-observation endpoints
ALLOWED_API_V1_SEGMENTS = {
    "day-of-week",
    "sun-position",
    "moon-position",
    "venus-position",
    "mercury-position",
    "mars-position",
    "jupiter-position",
    "saturn-position",
    "uranus-position",
    "neptune-position",
    "moon-phase",
    "astronomical-events",
    "astronomical-events-stream",
    "batch-earth-observations",
    "batch-earth-observations-stream",
}

# Attach rate limiter to app (Phase 3.1: DDoS Protection)
app.state.limiter = limiter

# Add exception handler for rate limit exceeded (only if using real limiter, not mock)
if not isinstance(limiter, MockLimiter):
    app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)

# Configure CORS with environment-specific settings
# For production, set ALLOWED_ORIGINS environment variable to comma-separated list of domains
# Example: ALLOWED_ORIGINS="https://yourdomain.com,https://www.yourdomain.com"
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5174,http://127.0.0.1:5174,"
        "http://localhost:4173,http://127.0.0.1:4173"  # 4173 = vite preview
    ).split(",")
    if origin.strip()  # Filter out empty strings
]

# Validate CORS origins in production
if os.getenv("ALLOWED_ORIGINS"):
    # Check for insecure HTTP origins
    http_origins = [origin for origin in allowed_origins if origin.startswith("http://")]
    if http_origins:
        logger.warning(
            "⚠️ SECURITY WARNING: CORS configured with insecure HTTP origins: %s. "
            "Use HTTPS for production deployments.",
            http_origins
        )

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,  # No authentication required
    allow_methods=["GET", "POST"],  # Only methods used by the API
    allow_headers=["Content-Type", "Accept"],
)

# Request size limit middleware to prevent DOS attacks
# Default: 5 MB (configurable via MAX_REQUEST_SIZE_MB environment variable)
MAX_REQUEST_SIZE_BYTES = int(os.getenv("MAX_REQUEST_SIZE_MB", "5")) * 1024 * 1024


class RequestSizeLimitMiddleware:  # pylint: disable=too-few-public-methods
    """ASGI middleware to enforce request body size limits at the stream level.

    Protects against DOS attacks from:
    - Clients with false Content-Length headers (understated)
    - Clients using chunked transfer encoding
    - Clients omitting the Content-Length header entirely

    Strategy:
    1. Validate Content-Length header upfront (if present) before invoking app
       - If oversized, send 413 immediately and return without calling app
    2. For streaming bodies without Content-Length, wrap receive() to monitor bytes
       - If size exceeded during streaming, return http.disconnect to abort body reading
       - This prevents the app from receiving more body data

    Ensures exactly one HTTP response is sent by rejecting oversized requests before
    the downstream app executes.

    In production with a reverse proxy (nginx, HAProxy, etc.), proxy-level size
    limits provide additional defense-in-depth.

    Responds with HTTP 413 (Payload Too Large) if body exceeds MAX_REQUEST_SIZE_BYTES.
    """

    def __init__(self, asgi_app):
        self.asgi_app = asgi_app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.asgi_app(scope, receive, send)
            return

        # Check Content-Length header upfront (if present)
        # This allows us to reject oversized requests BEFORE invoking the app
        headers = scope.get("headers", [])
        for header_name, header_value in headers:
            if header_name.lower() == b"content-length":
                try:
                    content_length = int(header_value.decode())
                    if content_length > MAX_REQUEST_SIZE_BYTES:
                        client_host = scope.get("client", ("unknown", 0))[0]
                        logger.warning(
                            "Request rejected: Content-Length %d bytes exceeds "
                            "limit of %d bytes from %s",
                            content_length,
                            MAX_REQUEST_SIZE_BYTES,
                            client_host
                        )
                        # Send 413 response BEFORE calling app
                        await send({
                            "type": "http.response.start",
                            "status": 413,
                            "headers": [
                                [b"content-type", b"application/json"],
                            ],
                        })
                        await send({
                            "type": "http.response.body",
                            "body": b"",
                        })
                        return  # Do not invoke app
                except (ValueError, UnicodeDecodeError):
                    pass
                break

        # For requests without Content-Length header, wrap receive() to enforce limit
        # during streaming. This catches clients using chunked transfer encoding
        # or omitting the Content-Length header.
        bytes_received = 0
        original_receive = receive

        async def size_limited_receive():
            """Intercept ASGI receive() to enforce request body size limit during streaming."""
            nonlocal bytes_received

            message = await original_receive()

            # Only count body chunks, not headers or other metadata
            if message["type"] == "http.request":
                chunk_size = len(message.get("body", b""))
                bytes_received += chunk_size

                if bytes_received > MAX_REQUEST_SIZE_BYTES:
                    # Size limit exceeded during streaming
                    # Send 413 response to the client before signaling disconnect
                    client_host = scope.get("client", ("unknown", 0))[0]
                    logger.warning(
                        "Request rejected: Body size %d bytes exceeds limit of %d bytes from %s",
                        bytes_received,
                        MAX_REQUEST_SIZE_BYTES,
                        client_host
                    )

                    # Send 413 response to the client
                    response_body = b"Payload Too Large"
                    await send({
                        "type": "http.response.start",
                        "status": 413,
                        "headers": [
                            [b"content-type", b"text/plain"],
                            [b"content-length", str(len(response_body)).encode()],
                        ],
                    })
                    await send({
                        "type": "http.response.body",
                        "body": response_body,
                        "more_body": False
                    })

                    # Return http.disconnect to abort body reading and signal connection closure
                    # The app will receive this when it tries to read the next body chunk
                    return {"type": "http.disconnect"}

            return message

        # Pass the wrapped receive to the app
        await self.asgi_app(scope, size_limited_receive, send)


# Insert the ASGI middleware at the beginning (before other middleware)
# This ensures size limits are enforced before any request processing
app.add_middleware(RequestSizeLimitMiddleware)


def _parse_accept_language_tags(header: str) -> list[tuple[float, str]]:
    """Parse Accept-Language header into sorted (q-value, tag) tuples.

    Higher q values appear first; equal-q entries retain original order.
    Skips q=0 entries per RFC 9110 §12.4.2.
    """
    tags: list[tuple[float, str]] = []
    for part in header.split(","):
        segments = part.strip().split(";")
        tag = segments[0].strip().lower()
        q = 1.0
        for segment in segments[1:]:
            segment = segment.strip()
            if segment.lower().startswith("q="):
                try:
                    q = float(segment[2:])
                except ValueError:
                    q = 0.0  # invalid q — treat as "not acceptable"
                else:
                    q = max(0.0, min(1.0, q))  # clamp to [0, 1] per RFC 9110
                break
        # q=0 means "not acceptable" per RFC 9110 §12.4.2; skip these entirely.
        if tag and q > 0.0:
            tags.append((q, tag))
    # Higher q first; equal-q entries retain their original (left-to-right) order.
    tags.sort(key=lambda x: x[0], reverse=True)
    return tags


def _match_supported_locale(tag: str) -> str | None:
    """Find matching supported locale for language tag.

    Returns exact match if available, otherwise language-prefix match,
    otherwise None.
    """
    if tag in SUPPORTED_LOCALES:
        return tag
    prefix = tag.split("-")[0]
    if prefix in SUPPORTED_LOCALES:
        return prefix
    return None


def _resolve_accept_language(header: str) -> str:
    """Select the best supported locale from an Accept-Language header value.

    Parses all language-ranges (including q= weights), sorts by preference
    (highest q first, original order preserved for equal q), and returns the
    first tag that matches a supported locale — exact match first, then
    language-prefix match (e.g. 'en-US' → 'en').  Falls back to 'en' if
    nothing matches.
    """
    if not header:
        return 'en'
    tags = _parse_accept_language_tags(header)
    for _, tag in tags:
        matched = _match_supported_locale(tag)
        if matched:
            return matched
    return 'en'

def _get_route_label(request: Request) -> str:
    """Extract matched route label for Prometheus metrics (cardinality safety).

    Returns the matched route's path pattern (template) if available, which is
    bounded and consistent. Falls back to "unknown" for unmatched routes (404)
    instead of using the raw URL path.

    Using the raw URL path as a label would allow attackers to create unbounded
    cardinality in Prometheus by sending requests to arbitrary unknown paths,
    causing time-series/memory exhaustion in monitoring.

    Args:
        request: The HTTP request object (after route matching via call_next)

    Returns:
        Route path pattern (e.g. "/api/v1/bodies") or "unknown" for 404s
    """
    try:
        # After call_next, the matched route is stored in request.scope
        route = request.scope.get('route')
        if route and hasattr(route, 'path'):
            return route.path
    except (AttributeError, KeyError, TypeError):  # Best-effort route extraction
        # Ignore errors accessing request.scope or route attributes
        pass

    # Fallback for unmatched routes (404) or any access errors
    # "unknown" is a bounded label that prevents cardinality explosion
    return "unknown"

def _get_pre_route_label(request: Request) -> str:
    """Derive a bounded endpoint label from the raw request path.

    Used before route matching (call_next) for adaptive timeout classification.
    Extracts route-like labels from known API prefixes to prevent cardinality
    explosion while enabling per-endpoint timeout tracking.

    Only returns labels from an explicit allowlist; maps all other first segments
    to 'unknown' to prevent cardinality explosion from arbitrary paths.

    Returns a bounded label based on the request path structure:
    - "/api/v1/astronomical-events" → "/api/v1/astronomical-events"
    - "/api/v1/astronomical-events/contact-times" (separate endpoint)
    - "/api/v1/batch-earth-observations" → "/api/v1/batch-earth-observations"
    - "/api/v1/random-nonce" → "unknown" (not in allowlist)
    - "/api/metrics" → "/api/metrics"
    - "/unknown/path" → "unknown" (bounded)

    Args:
        request: HTTP request (before route matching)

    Returns:
        Bounded endpoint label (e.g., "/api/v1/astronomical-events") or "unknown"
    """
    path = request.url.path

    # Strip query parameters if present (defensive; shouldn't be in request.url.path)
    if "?" in path:
        path = path.split("?")[0]

    # Known full-path endpoints (preserve as-is before generic grouping)
    # astronomical-events/contact-times is a per-endpoint route with separate timeout config
    if path.startswith("/api/v1/astronomical-events/contact-times"):
        return "/api/v1/astronomical-events/contact-times"

    # API v1 endpoints: extract and validate the first path segment
    # Only return labels for allowlisted segments; map others to "unknown"
    if path.startswith("/api/v1/"):
        relative = path[8:]  # Remove "/api/v1/" prefix
        first_segment = relative.split("/")[0]
        if first_segment in ALLOWED_API_V1_SEGMENTS:
            return f"/api/v1/{first_segment}"
        # Unknown or malicious first segment - return bounded label
        return "unknown"

    # Known utility endpoints
    if path in ("/", "/health", "/cache-stats", "/rate-limit-stats"):
        return path

    # Metrics endpoint (mounted with /api prefix)
    if path.startswith("/api/metrics"):
        return "/api/metrics"

    # Unbounded/unknown path - return bounded label to prevent cardinality explosion
    return "unknown"

@app.middleware("http")
async def locale_middleware(request: Request, call_next):
    """Read locale from the request and set the request-scoped locale.

    Priority:
    1. ?lang= query parameter (explicit per-request override; used by SSE/EventSource
       which cannot set custom headers)
    2. Accept-Language header — all language-ranges are parsed in q-value order,
       with exact and prefix matching against SUPPORTED_LOCALES
    3. 'en' default

    Falls back to 'en' for any unsupported locale.
    """
    lang_param = request.query_params.get("lang", "")
    if lang_param:
        # ?lang= is an explicit per-request override used by SSE
        # (EventSource cannot set custom headers, so the frontend appends ?lang=).
        tag = lang_param.strip().lower()
        if tag in SUPPORTED_LOCALES:
            locale = tag
        else:
            prefix = tag.split("-")[0]
            locale = prefix if prefix in SUPPORTED_LOCALES else 'en'
    else:
        # Parse the full Accept-Language header respecting q-values.
        locale = _resolve_accept_language(request.headers.get("accept-language", ""))
    set_request_locale(locale)
    return await call_next(request)


def _is_streaming_response_asgi(headers: list[tuple[bytes, bytes]]) -> bool:
    """Detect if ASGI response will be streamed based on response headers.

    A response is considered streaming if:
    1. No Content-Length header (response size unknown)
    2. Transfer-Encoding: chunked
    3. Content-Type indicates streaming (text/event-stream, etc.)

    Args:
        headers: ASGI response headers (list of 2-tuples of byte strings)

    Returns:
        True if response appears to be streaming; False for regular responses
    """
    has_content_length = False
    for header_name, header_value in headers:
        name_lower = header_name.lower()
        if name_lower == b"content-length":
            has_content_length = True
            break
        if name_lower == b"transfer-encoding":
            if b"chunked" in header_value.lower():
                return True
        if name_lower == b"content-type":
            if b"event-stream" in header_value.lower():
                return True
    # No Content-Length = streaming (unknown size, sent incrementally)
    return not has_content_length


class MetricsMiddleware:  # pylint: disable=too-few-public-methods
    """Pure ASGI middleware for recording HTTP request metrics (Phase 3.2).

    Tracks request duration, count, status, and in-progress requests per endpoint.
    Uses matched route template as label (not raw URL path) to prevent cardinality
    explosion from requests to unknown paths.
    Ultra-lightweight: ~2-3 μs overhead per request.

    Ensures cleanup (record_request_end) is called even if outer middleware cancels
    the request (e.g., due to timeout), preventing leaked in-progress request counts.

    Implemented as pure ASGI middleware (not BaseHTTPMiddleware) to properly detect
    streaming responses: checks response headers instead of isinstance(), avoiding
    the issue where BaseHTTPMiddleware returns internal _StreamingResponse objects
    that don't match public StreamingResponse type checks.
    """

    def __init__(self, asgi_app):
        self.asgi_app = asgi_app

    async def __call__(self, scope, receive, send):  # pylint: disable=too-many-statements
        if scope["type"] != "http":
            await self.asgi_app(scope, receive, send)
            return

        start_time = time.perf_counter()
        metrics = get_metrics()

        # Extract request info for metrics
        method = scope.get("method", "GET")

        # Use bounded pre-route label for in-progress tracking
        request_obj = Request(scope)
        pre_route_endpoint = _get_pre_route_label(request_obj)
        metrics.record_request_start(pre_route_endpoint)

        status_code = 500
        is_streaming = False
        response_headers = []
        endpoint = None
        request_state_metadata = None

        async def send_with_metrics(message):
            """Wrap send to track status and detect streaming responses."""
            nonlocal status_code, is_streaming, response_headers, endpoint, request_state_metadata

            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
                response_headers = message.get("headers", [])
                is_streaming = _is_streaming_response_asgi(response_headers)

                # Extract matched route label after response headers are available
                # For most cases, request.scope["route"] should be set by now
                try:
                    route = scope.get("route")
                    if route and hasattr(route, "path"):
                        endpoint = route.path
                    else:
                        endpoint = "unknown"
                except (AttributeError, KeyError, TypeError):
                    endpoint = "unknown"

                # For streaming responses, prepare deferred metrics recording
                if is_streaming:
                    request_state_metadata = StreamingMetadata(
                        endpoint=endpoint,
                        method=method,
                        status_code=status_code,
                        deferred=True,
                        pre_route_endpoint=pre_route_endpoint,
                        start_time=start_time
                    )
                    # Store on scope for iterator wrapper to retrieve
                    if "state" not in scope:
                        scope["state"] = {}
                    scope["state"]["streaming_metadata"] = request_state_metadata
                else:
                    # Non-streaming: record metrics immediately
                    duration = time.perf_counter() - start_time
                    metrics.record_request(endpoint, method, status_code, duration)
                    # Check if this is a timeout-generated response to record with is_timeout=True
                    is_timeout_generated = scope.get("_timeout_middleware_generated", False)
                    record_request_completion(endpoint, duration, is_timeout=is_timeout_generated)

                # Track 429 rate limit responses
                if status_code == 429:
                    metrics.record_rate_limit_exceeded(endpoint)

            elif message["type"] == "http.response.body":
                # For streaming responses, finalize metrics when the final body chunk is sent
                if is_streaming and not message.get("more_body", False):
                    # Last chunk of streaming response - finalize metrics
                    if request_state_metadata:
                        duration = time.perf_counter() - start_time
                        # Check if this streaming response was generated by a timeout (503)
                        is_timeout_generated = (
                            scope.get("_timeout_middleware_generated", False) or
                            status_code == 503
                        )
                        metrics.record_request(
                            request_state_metadata.endpoint,
                            request_state_metadata.method,
                            status_code,
                            duration
                        )
                        record_request_completion(
                            endpoint,
                            duration,
                            is_timeout=is_timeout_generated
                        )
                        metrics.record_request_end(pre_route_endpoint)

            # Pass through to outer send
            await send(message)

        try:
            await self.asgi_app(scope, receive, send_with_metrics)
        finally:
            # For non-streaming: always record request completion
            # For streaming: metrics are finalized in send_with_metrics
            # when final body chunk (more_body=False) is sent
            if not is_streaming:
                metrics.record_request_end(pre_route_endpoint)


def _record_streaming_timeout_metrics(
    metadata: StreamingMetadata | None,
    endpoint: str,
    elapsed: float,
    timeout_seconds: float
) -> None:
    """Record metrics for streaming response timeout.

    Args:
        metadata: Streaming metadata from registry, or None if not available
        endpoint: Endpoint label for logging/metrics
        elapsed: Elapsed time in seconds
        timeout_seconds: Timeout budget in seconds
    """
    # Record timeout duration for adaptive timeout tracker (p95 calculation)
    # Mark as timeout so timeout samples don't skew p95 and cause oscillation
    record_request_completion(endpoint, elapsed, is_timeout=True)

    metrics = get_metrics()
    metrics.record_timeout_exceeded(endpoint)
    logger.warning(
        "Streaming timeout on %s after %.2f seconds (timeout: %.2f seconds)",
        endpoint,
        elapsed,
        timeout_seconds,
    )
    if metadata:
        metrics.record_request(metadata.endpoint, metadata.method, 503, elapsed)
        metrics.record_request_end(metadata.pre_route_endpoint)


def _record_streaming_completion_metrics(
    metadata: StreamingMetadata | None,
    endpoint: str,
    elapsed: float
) -> None:
    """Record metrics for successfully completed streaming response.

    Args:
        metadata: Streaming metadata from registry
        endpoint: Endpoint label for metrics
        elapsed: Total elapsed time in seconds
    """
    record_request_completion(endpoint, elapsed)
    if metadata:
        metrics = get_metrics()
        metrics.record_request(metadata.endpoint, metadata.method, metadata.status_code, elapsed)
        metrics.record_request_end(metadata.pre_route_endpoint)


class TimeoutMiddleware:  # pylint: disable=too-few-public-methods
    """Pure ASGI middleware for adaptive request timeouts (Phase 3.3).

    Calculates timeout based on observed p95 request duration. Under load, timeouts
    are reduced proportionally, allowing cheap requests to fail fast (DDoS protection)
    while preserving expensive requests when possible.

    Times both response creation AND body iteration (for streaming responses), ensuring
    proper load shedding even for long-running streams.

    Implemented as pure ASGI middleware (not BaseHTTPMiddleware) to properly wrap
    streaming response body iteration. Detects streaming from response headers
    (absence of Content-Length) and wraps the send callable to enforce timeout on
    each body chunk, not just response creation.

    LIMITATION (Phase 4 - Load Balancing):
    The current asyncio.wait_for() timeout does not interrupt CPU-bound Astropy
    calculations in worker threads. Additionally, fixed-window rate limiting
    ("N per minute") does NOT space requests evenly—all N can arrive in a burst.
    
    Combined effect under attack:
    - Batch requests (40s CPU each): 5/min limit = 200s CPU work if all arrive at once
    - 4 CPU cores need 50s to complete (all saturated)
    - Requests timeout after ~60s but work continues in background
    - Queue grows faster than it drains despite all requests timing out
    
    Conservative Phase 3 limits (5-8 req/min, frontend queue at 120 req/min) help
    but do NOT guarantee protection. True load shedding requires:
    - Admission control: Reject requests when in-flight work >= capacity threshold
    - Cancellable work: ProcessPoolExecutor with SIGTERM for genuine interruption
    - Per-endpoint tracking: Separate admission budgets for different CPU costs
    
    This approach is acceptable for single-instance if production load stays below
    capacity. Multi-instance deployments MUST implement Phase 4 admission control
    (reject before accepting) + cancellable work (interrupt via SIGTERM).

    See LOAD_BALANCING_STRATEGY.md for Phase 4.1 (Admission Control) and Phase 4.2
    (Cancellable Work) design and dependencies.
    """

    def __init__(self, asgi_app):
        self.asgi_app = asgi_app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.asgi_app(scope, receive, send)
            return

        # Derive bounded label from raw path BEFORE route matching
        request_obj = Request(scope)
        endpoint = _get_pre_route_label(request_obj)

        # Calculate adaptive timeout based on system performance
        timeout_seconds = calculate_adaptive_timeout(endpoint)

        # Track start time for timeout enforcement
        start_time = time.perf_counter()
        is_streaming = False
        response_started = False
        timeout_occurred = False

        async def send_with_timeout(message):
            """Wrap send to enforce timeout on response and body chunks."""
            nonlocal is_streaming, response_started, timeout_occurred

            if message["type"] == "http.response.start":
                response_started = True
                headers = message.get("headers", [])
                is_streaming = _is_streaming_response_asgi(headers)
                await send(message)

            elif message["type"] == "http.response.body":
                elapsed = time.perf_counter() - start_time
                if elapsed > timeout_seconds:
                    # Timeout exceeded during body transmission
                    if not timeout_occurred:
                        timeout_occurred = True
                        metrics = get_metrics()
                        metrics.record_timeout_exceeded(endpoint)
                        logger.warning(
                            "Request timeout on %s after %.2fs (load-based degradation)",
                            endpoint,
                            elapsed
                        )
                        # Send error message if streaming, otherwise just close connection
                        if is_streaming:
                            await send({
                                "type": "http.response.body",
                                "body": b"event: error\ndata: {\"error\": \"timeout\"}\n\n",
                                "more_body": False
                            })
                        else:
                            # Non-streaming: just close without sending incomplete body
                            await send({
                                "type": "http.response.body",
                                "body": b"",
                                "more_body": False
                            })
                else:
                    # Within timeout: send body chunk
                    await send(message)
            else:
                await send(message)

        try:
            # Wrap the app call with timeout for response creation
            await asyncio.wait_for(
                self.asgi_app(scope, receive, send_with_timeout),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            # Timeout during app execution (before response.start)
            if not response_started:
                # Mark scope to indicate this 503 was generated by timeout
                # Allows downstream metrics middleware to record with is_timeout=True
                scope["_timeout_middleware_generated"] = True

                # Response hasn't started yet; we can send a proper 503
                metrics = get_metrics()
                metrics.record_timeout_exceeded(endpoint)
                logger.warning(
                    "Request timeout on %s after %.2fs (load-based degradation)",
                    endpoint,
                    timeout_seconds
                )
                await send({
                    "type": "http.response.start",
                    "status": 503,
                    "headers": [
                        [b"content-type", b"application/json"],
                        [b"content-length", str(len(
                            b'{"error":"Request timeout","message":"Request exceeded '
                            b'%.1fs timeout due to system load","timeout_seconds":%.1f,'
                            b'"endpoint":"%s"}' % (
                                timeout_seconds,
                                timeout_seconds,
                                endpoint.encode()
                            )
                        )).encode()],
                    ],
                })
                timeout_msg = (
                    f'{{"error":"Request timeout",'
                    f'"message":"Request exceeded {timeout_seconds:.1f}s timeout due to '
                    f'system load","timeout_seconds":{timeout_seconds},'
                    f'"endpoint":"{endpoint}"}}'
                ).encode()
                await send({
                    "type": "http.response.body",
                    "body": timeout_msg,
                    "more_body": False
                })
            else:
                # Response already started; can't send headers, just close body
                scope["_timeout_middleware_generated"] = True
                metrics = get_metrics()
                metrics.record_timeout_exceeded(endpoint)
                elapsed = time.perf_counter() - start_time
                logger.warning(
                    "Request timeout on %s after %.2fs (response started, stream cut off)",
                    endpoint,
                    elapsed
                )
                await send({
                    "type": "http.response.body",
                    "body": b"",
                    "more_body": False
                })


# Register pure ASGI middleware for metrics and timeout (after class definitions)
# These must be registered BEFORE the decorator-based @app.middleware middleware
# so they wrap the inner handlers first (LIFO: last-registered wraps innermost)
# Pure ASGI implementation properly detects streaming responses by checking headers,
# not relying on isinstance() which fails for BaseHTTPMiddleware's internal _StreamingResponse
app.add_middleware(TimeoutMiddleware)
app.add_middleware(MetricsMiddleware)


# Include the routes
app.include_router(router, prefix="/api/v1", tags=["astronomy"])
app.include_router(metrics_router, prefix="/api", tags=["monitoring"])


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Astronomy API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "ok"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/cache-stats")
async def cache_statistics():
    """Cache statistics endpoint for monitoring response cache performance.

    Returns:
    - cached_entries: Number of active cache entries
    - max_size: Maximum cache capacity
    - utilization: Cache utilization percentage
    """
    return get_cache_stats()


@app.get("/rate-limit-stats")
async def rate_limit_statistics():
    """Rate limiting statistics endpoint for monitoring DDoS protection.

    Returns:
    - cached_entries: Number of active rate limit entries
    - storage_type: Storage backend used (memory for single instance)
    - enabled: Whether rate limiting is active
    - note: Information about multi-instance deployments
    """
    return get_rate_limit_stats()
