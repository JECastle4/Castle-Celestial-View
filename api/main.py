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
from fastapi.responses import JSONResponse

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
    Ultra-lightweight: ~2-3 μs overhead per request.
    """
    # Get endpoint name from URL path (strip query params and convert to label-safe format)
    endpoint = request.url.path.split("?")[0] or "/"
    method = request.method

    # Increment in-progress gauge
    metrics = get_metrics()
    metrics.record_request_start(endpoint)

    # Record start time
    start_time = time.perf_counter()

    try:
        # Call endpoint
        response = await call_next(request)
        status_code = response.status_code
    except Exception as exc:
        # Record error and re-raise
        metrics.record_error(endpoint, "exception", 500)
        metrics.record_request_end(endpoint)
        raise exc

    # Record metrics
    duration = time.perf_counter() - start_time
    metrics.record_request(endpoint, method, status_code, duration)
    metrics.record_request_end(endpoint)

    # Track 429 rate limit responses
    if status_code == 429:
        metrics.record_rate_limit_exceeded(endpoint)

    # Record completion time for adaptive timeout calculation (Phase 3.3)
    record_request_completion(endpoint, duration)

    return response


@app.middleware("http")
async def timeout_middleware(request: Request, call_next):
    """Adaptive timeout middleware for graceful degradation under load (Phase 3.3).

    Calculates timeout based on observed p95 request duration. Under load, timeouts
    are reduced proportionally, allowing cheap requests to fail fast (DDoS protection)
    while preserving expensive requests when possible.

    Runs AFTER metrics middleware so request completion times are captured for the
    percentile calculation.
    """
    endpoint = request.url.path.split("?")[0] or "/"

    # Calculate adaptive timeout based on system performance
    timeout_seconds = calculate_adaptive_timeout(endpoint)

    try:
        # Wrap the endpoint call with asyncio.wait_for timeout
        response = await asyncio.wait_for(
            call_next(request),
            timeout=timeout_seconds
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
