"""
Main FastAPI application for Astronomy API
"""
import asyncio
import logging
import time
import os

from astropy.utils import iers
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from api.cache import get_cache_stats
from api.i18n import SUPPORTED_LOCALES, set_request_locale
from api.metrics import get_metrics
from api.rate_limiter import limiter
from api.routes import router
from api.routes.metrics import router as metrics_router
from api.timeout_logic import calculate_adaptive_timeout, record_request_completion

# Only import RateLimitExceeded if we're using the real rate limiter
# pylint: disable=invalid-name
RateLimitExceeded = None
rate_limit_exception_handler = None
HAS_REAL_LIMITER = False  # pylint: disable=invalid-name

if hasattr(limiter, '__class__') and limiter.__class__.__name__ == 'Limiter':
    # pylint: disable=import-outside-toplevel,invalid-name,ungrouped-imports
    from slowapi.errors import RateLimitExceeded
    from api.rate_limiter import rate_limit_exception_handler
    HAS_REAL_LIMITER = True  # pylint: disable=invalid-name

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

# Attach rate limiter to app (Phase 3.1: DDoS Protection)
app.state.limiter = limiter

# Add exception handler for rate limit exceeded (only if using real limiter)
if HAS_REAL_LIMITER:
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


@app.middleware("http")
async def request_size_limit_middleware(request: Request, call_next):
    """Limit request body size to prevent DOS attacks.

    Checks Content-Length header and rejects oversized requests.
    Limit is configurable via MAX_REQUEST_SIZE_MB environment variable (default: 5 MB).
    """
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_REQUEST_SIZE_BYTES:
        logger.warning(
            "Request rejected: Content-Length %s exceeds limit of %s bytes from %s",
            content_length,
            MAX_REQUEST_SIZE_BYTES,
            request.client.host if request.client else "unknown"
        )
        raise HTTPException(
            status_code=413,
            detail=f"Payload too large. Maximum size: {MAX_REQUEST_SIZE_BYTES // (1024*1024)} MB"
        )
    return await call_next(request)


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


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Record HTTP request metrics for Prometheus monitoring (Phase 3.2).

    Tracks request duration, count, status, and in-progress requests per endpoint.
    Uses matched route template as label (not raw URL path) to prevent cardinality
    explosion from requests to unknown paths.
    Ultra-lightweight: ~2-3 μs overhead per request.

    Ensures cleanup (record_request_end) is called even if outer middleware cancels
    the request (e.g., due to timeout), preventing leaked in-progress request counts.
    """
    # Record start time (before any processing)
    start_time = time.perf_counter()

    metrics = get_metrics()
    endpoint = None
    status_code = 500  # Default to server error

    try:
        # Call endpoint (route matching happens here)
        response = await call_next(request)
        status_code = response.status_code

        # Extract matched route label (bounded; prevents cardinality explosion)
        # This is safe to call after call_next when route matching is complete
        endpoint = _get_route_label(request)
        method = request.method

        # Record metrics (after route matching, using bounded route label)
        duration = time.perf_counter() - start_time
        metrics.record_request_start(endpoint)
        metrics.record_request(endpoint, method, status_code, duration)

        # Track 429 rate limit responses
        if status_code == 429:
            metrics.record_rate_limit_exceeded(endpoint)

        # Record completion time for adaptive timeout calculation (Phase 3.3)
        record_request_completion(endpoint, duration)

        return response

    except asyncio.CancelledError:
        # Outer timeout middleware cancelled this request
        # Ensure metrics are recorded for the timed-out request
        endpoint = _get_route_label(request)
        duration = time.perf_counter() - start_time

        metrics.record_request_start(endpoint)
        metrics.record_error(endpoint, "timeout", 503)

        # Record timeout for adaptive calculation
        record_request_completion(endpoint, duration)

        # Log and re-raise so timeout middleware can handle it
        logger.warning(
            "Request cancelled (timeout) on %s after %.2fs",
            endpoint,
            duration
        )
        raise

    except Exception as exc:  # pylint: disable=broad-exception-caught
        # Other exception during route handling
        endpoint = _get_route_label(request)
        metrics.record_error(endpoint, "exception", 500)
        raise exc

    finally:
        # Always record request completion, even on timeout or exception
        if endpoint:
            metrics.record_request_end(endpoint)


def _wrap_streaming_response_timeout(response, timeout_seconds, endpoint, start_time):
    """
    Wrap a StreamingResponse to enforce timeout during body iteration.

    The initial asyncio.wait_for() only times response creation. For StreamingResponse,
    the actual expensive work (generator iteration) happens AFTER the response is
    returned. This wrapper applies timeout to the iteration itself, providing proper
    load shedding and preventing unbounded long-running streams.

    Args:
        response: FastAPI response object
        timeout_seconds: timeout budget (in seconds)
        endpoint: endpoint label for logging
        start_time: time when request started (perf_counter)

    Returns:
        Response object (wrapped if it was StreamingResponse)
    """
    if not isinstance(response, StreamingResponse):
        return response

    original_body_iterator = response.body_iterator

    async def timeout_enforcing_generator():
        """Iterate generator with timeout enforcement on each iteration."""
        try:
            # Try to iterate the original generator
            if hasattr(original_body_iterator, '__aiter__'):
                # Async generator
                async for item in original_body_iterator:
                    elapsed = time.perf_counter() - start_time
                    if elapsed > timeout_seconds:
                        # Timeout during streaming - log and break
                        metrics = get_metrics()
                        metrics.record_timeout_exceeded(endpoint)
                        logger.warning(
                            "Streaming timeout on %s after %.2f seconds "
                            "(timeout: %.2f seconds)",
                            endpoint,
                            elapsed,
                            timeout_seconds,
                        )
                        # Yield error event for SSE clients
                        yield b"event: error\ndata: {\"error\": \"timeout\"}\n\n"
                        return
                    yield item
            else:
                # Sync generator - iterate and yield
                for item in original_body_iterator:
                    elapsed = time.perf_counter() - start_time
                    if elapsed > timeout_seconds:
                        # Timeout during streaming
                        metrics = get_metrics()
                        metrics.record_timeout_exceeded(endpoint)
                        logger.warning(
                            "Streaming timeout on %s after %.2f seconds "
                            "(timeout: %.2f seconds)",
                            endpoint,
                            elapsed,
                            timeout_seconds,
                        )
                        # Yield error event for SSE clients
                        yield b"event: error\ndata: {\"error\": \"timeout\"}\n\n"
                        return
                    yield item
        finally:
            # Cleanup: close async generator if needed
            if hasattr(original_body_iterator, 'aclose'):
                try:
                    await original_body_iterator.aclose()
                except (RuntimeError, ValueError):  # Cleanup errors (generator closed, etc)
                    # Ignore cleanup errors - don't suppress original exception
                    pass

    # Replace body iterator with wrapped version
    response.body_iterator = timeout_enforcing_generator()
    return response


@app.middleware("http")
async def timeout_middleware(request: Request, call_next):
    """Adaptive timeout middleware for graceful degradation under load (Phase 3.3).

    Calculates timeout based on observed p95 request duration. Under load, timeouts
    are reduced proportionally, allowing cheap requests to fail fast (DDoS protection)
    while preserving expensive requests when possible.

    Times both response creation AND body iteration (for StreamingResponse), ensuring
    proper load shedding even for long-running streams.

    Uses bounded route labels for timeout tracking (prevents cardinality explosion
    from tracking arbitrary unknown paths in the adaptive timeout tracker).
    """
    # Use bounded route label (returns "unknown" for unmatched routes before call_next)
    # This prevents arbitrary unknown paths from creating unbounded tracker entries
    endpoint = _get_route_label(request)

    # Calculate adaptive timeout based on system performance
    timeout_seconds = calculate_adaptive_timeout(endpoint)

    # Track start time for StreamingResponse body iteration timeout
    start_time = time.perf_counter()

    try:
        # Wrap the endpoint call with asyncio.wait_for timeout
        # This ensures response creation (including handler execution) completes in time
        response = await asyncio.wait_for(
            call_next(request),
            timeout=timeout_seconds
        )

        # Wrap StreamingResponse to enforce timeout on body iteration as well
        response = _wrap_streaming_response_timeout(
            response, timeout_seconds, endpoint, start_time
        )

        return response
    except asyncio.TimeoutError:
        # Request exceeded adaptive timeout - log and return 503
        metrics = get_metrics()
        metrics.record_timeout_exceeded(endpoint)

        logger.warning(
            "Request timeout on %s after %.2fs (load-based degradation)",
            endpoint,
            timeout_seconds
        )

        return JSONResponse(
            status_code=503,  # Service Unavailable
            content={
                'error': 'Request timeout',
                'message': (
                    f'Request exceeded {timeout_seconds:.1f}s timeout due to '
                    'system load'
                ),
                'timeout_seconds': timeout_seconds,
                'endpoint': endpoint,
            },
        )


# Include the routes
app.include_router(router, prefix="/api/v1", tags=["astronomy"])
app.include_router(metrics_router, tags=["monitoring"])


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
    - note: Information about multi-instance deployments
    """
    if not HAS_REAL_LIMITER:
        return {
            "message": "Rate limiting disabled (test mode)",
            "storage_type": "mock",
        }
    # pylint: disable=import-outside-toplevel
    from api.rate_limiter import get_cache_stats as get_rate_limit_stats
    return get_rate_limit_stats()
