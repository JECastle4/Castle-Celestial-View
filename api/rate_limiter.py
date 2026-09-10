"""
Rate limiting configuration for DDoS protection (Phase 3.1).

Implements tiered, endpoint-specific rate limiting based on computational cost.
Uses slowapi for per-IP request throttling with graceful 429 responses.

In test mode (pytest), rate limiting is bypassed to avoid test flakiness.

Configuration (Environment Variables):
    RATE_LIMIT_ENABLED: Enable/disable rate limiting (default: "true")
        Set to "false" to disable all rate limiting without code changes.
        Example: export RATE_LIMIT_ENABLED=false
    
    RATE_LIMIT_DEFAULT: Global per-IP limit across all endpoints (default: "200/minute")
        Format: "N/minute" where N is requests per minute.
        Example: export RATE_LIMIT_DEFAULT=300/minute
    
    LIMIT_EXPENSIVE_BATCH: batch-earth-observations endpoint (default: "20/minute")
        Expensive operation: ~40s avg CPU per request.
        Example: export LIMIT_EXPENSIVE_BATCH=30/minute
    
    LIMIT_EXPENSIVE_EVENTS: astronomical-events endpoint (default: "15/minute")
        Expensive operation: ~30s avg CPU per request.
        Example: export LIMIT_EXPENSIVE_EVENTS=20/minute
    
    LIMIT_STREAM_EVENTS: astronomical-events-stream SSE endpoint (default: "10/minute")
        Limits concurrent streaming connections per IP.
        Example: export LIMIT_STREAM_EVENTS=15/minute
    
    LIMIT_CONTACT_TIMES: contact-times endpoint (default: "30/minute")
        Lazy-loaded operation: cheaper than search.
        Example: export LIMIT_CONTACT_TIMES=50/minute
    
    LIMIT_CHEAP: position/phase endpoints (default: "100/minute")
        Fast operations: <500ms per request.
        Example: export LIMIT_CHEAP=150/minute

Typical Deployment Scenarios:
    - Reduce limits during high-load events: adjust env vars, restart container
    - Disable rate limiting for internal testing: RATE_LIMIT_ENABLED=false
    - Increase limits for enterprise deployments: adjust endpoint-specific vars
"""

import logging
import os
from typing import Callable

from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from api.i18n import get_i18n

logger = logging.getLogger(__name__)

# Internal IP addresses that bypass rate limiting (for monitoring/benchmarks)
INTERNAL_IPS = {
    "127.0.0.1",  # localhost IPv4
    "::1",  # localhost IPv6
}

# Check if running in test mode (pytest sets this environment variable during test execution)
def is_test_mode() -> bool:
    """Check if running under pytest.

    Checks for pytest in sys.modules (imported during test run) or
    PYTEST_CURRENT_TEST environment variable (set by pytest runner).
    """
    import sys  # pylint: disable=import-outside-toplevel
    return 'pytest' in sys.modules or os.getenv("PYTEST_CURRENT_TEST") is not None


# Mock limiter for testing - creates decorators that do nothing
class MockLimiter:
    """Mock rate limiter that bypasses all rate limiting for tests."""

    def limit(self, _: str) -> Callable:
        """Return a no-op decorator that doesn't apply rate limiting."""
        def decorator(func: Callable) -> Callable:
            return func
        return decorator

    def __call__(self, *args, **kwargs):
        """Allow MockLimiter to be used as a decorator directly."""
        if callable(args[0]):
            return args[0]
        return self.limit(*args, **kwargs)


# Configuration: Read rate limiting settings from environment variables
# Allows operational teams to tune throttling without code changes or redeployment

# Enable/disable rate limiting via RATE_LIMIT_ENABLED env var (default: true)
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in ("true", "1", "yes")

# Default global limit (per IP, all endpoints combined) via RATE_LIMIT_DEFAULT env var
_DEFAULT_LIMIT = os.getenv("RATE_LIMIT_DEFAULT", "200/minute")

# Endpoint-specific limits via environment variables (allow ops to adjust without code changes)
# Format: "N/minute" where N is requests per minute
LIMIT_EXPENSIVE_BATCH = os.getenv(
    "LIMIT_EXPENSIVE_BATCH",
    "20/minute"  # batch-earth-observations: 40s avg × 20 = 800s CPU
)
LIMIT_EXPENSIVE_EVENTS = os.getenv(
    "LIMIT_EXPENSIVE_EVENTS",
    "15/minute"  # astronomical-events: 30s avg × 15 = 450s CPU
)
LIMIT_STREAM_EVENTS = os.getenv(
    "LIMIT_STREAM_EVENTS",
    "10/minute"  # astronomical-events-stream: limits concurrent SSE
)
LIMIT_CONTACT_TIMES = os.getenv(
    "LIMIT_CONTACT_TIMES",
    "30/minute"  # contact-times: lazy-loaded, cheaper than search
)
LIMIT_CHEAP = os.getenv(
    "LIMIT_CHEAP",
    "100/minute"  # position/phase: <500ms each
)

def should_bypass_rate_limit(request: Request) -> bool:
    """Check if request should bypass rate limiting (internal IPs).
    
    Returns True if the request comes from an internal IP (localhost),
    allowing monitoring/benchmark traffic to bypass rate limiting.
    """
    client_host = request.client.host if request.client else None
    return client_host in INTERNAL_IPS


def _rate_limit_key_func(request: Request) -> str | None:
    """
    Custom key function for rate limiting that respects INTERNAL_IPS.
    
    Returns:
        None for internal IPs (skips rate limiting for monitoring/benchmarks)
        IP address string for all other requests (applies rate limiting)
    
    Usage: passed to Limiter(key_func=_rate_limit_key_func)
    
    When this function returns None, slowapi skips rate limiting for that request.
    This allows localhost/internal monitoring traffic to bypass the limiter.
    """
    if should_bypass_rate_limit(request):
        return None  # Skip rate limiting for internal IPs
    return get_remote_address(request)  # Apply rate limiting for all other IPs


# Create appropriate limiter based on environment
if is_test_mode():
    # Use mock limiter in test mode to avoid rate limit conflicts in tests
    limiter = MockLimiter()  # type: ignore
elif RATE_LIMIT_ENABLED:
    # Use real limiter in production/development (if not disabled)
    limiter = Limiter(
        key_func=_rate_limit_key_func,  # Extract client IP (None for internal)
        default_limits=[_DEFAULT_LIMIT],  # Global per-IP limit
        storage_uri="memory://",  # Single instance in-memory storage
        strategy="fixed-window",  # Fixed window strategy (simpler, faster)
    )
else:
    # Rate limiting disabled via RATE_LIMIT_ENABLED=false
    limiter = MockLimiter()  # type: ignore
    logger.info("Rate limiting is disabled (RATE_LIMIT_ENABLED=false)")


async def rate_limit_exception_handler(request: Request, _: RateLimitExceeded) -> JSONResponse:
    """
    Handle rate limit exceeded errors with informative 429 response.

    Returns:
        JSONResponse with 429 status, Retry-After header, and localized message

    Logs rate-limit violations for attack detection.
    Uses i18n to provide localized error messages.
    """
    client_ip = request.client.host if request.client else "unknown"
    endpoint = request.url.path
    retry_after = 60

    # Log rate-limit violation for monitoring
    logger.warning(
        "Rate limit exceeded for %s on %s",
        client_ip,
        endpoint
    )

    # Get localized error message using i18n
    i18n = get_i18n()
    message = i18n.get(
        "errors.tooManyRequests",
        default="Too many requests. Please retry after {retry_after} seconds.",
        retry_after=retry_after
    )

    return JSONResponse(
        status_code=429,
        headers={"Retry-After": str(retry_after)},
        content={
            "error": "rate_limit_exceeded",
            "message": message,
            "retry_after": retry_after,
            "endpoint": endpoint,
        }
    )


def get_cache_stats() -> dict:
    """
    Get rate limiting cache statistics.
    
    Returns:
        Dictionary with cache size and utilization metrics
    """
    if hasattr(limiter.storage, "storage"):
        storage = limiter.storage.storage
        if hasattr(storage, "keys"):
            cache_size = len(storage)
        else:
            cache_size = len(list(storage.keys())) if hasattr(storage, "keys") else 0
    else:
        cache_size = 0

    return {
        "cached_entries": cache_size,
        "storage_type": "memory",
        "note": "Use Redis storage for multi-instance deployments"
    }


# Decorator functions for route-level rate limiting
# Usage: @limiter.limit(LIMIT_EXPENSIVE_BATCH) on route handlers


__all__ = [
    "limiter",
    "rate_limit_exception_handler",
    "should_bypass_rate_limit",
    "get_cache_stats",
    "LIMIT_EXPENSIVE_BATCH",
    "LIMIT_EXPENSIVE_EVENTS",
    "LIMIT_STREAM_EVENTS",
    "LIMIT_CONTACT_TIMES",
    "LIMIT_CHEAP",
]
