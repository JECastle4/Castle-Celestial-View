"""
Rate limiting configuration for DDoS protection (Phase 3.1).

Implements tiered, endpoint-specific rate limiting based on computational cost.
Uses slowapi for per-IP request throttling with graceful 429 responses.

In test mode (pytest), rate limiting is bypassed to avoid test flakiness.

CRITICAL SECURITY NOTE - Reverse Proxy Deployments:
When deployed behind a reverse proxy, you MUST configure trusted proxies to enable
per-client rate limiting. The limiter extracts the real client IP from X-Forwarded-For
headers, but ONLY if the immediate request peer (socket IP) is in the TRUSTED_PROXIES list.

If not configured correctly:
  - All external clients appear to come from the proxy's IP (e.g., 127.0.0.1)
  - All clients share one rate limit key
  - One attacker can exhaust the limit for all other users
  
To fix this:
  1. Set TRUSTED_PROXIES env var to the proxy's IP (comma-separated if multiple)
  2. Ensure your proxy sends X-Forwarded-For headers with real client IP
  3. Example: export TRUSTED_PROXIES=127.0.0.1,192.168.1.1

Configuration (Environment Variables):
    RATE_LIMIT_ENABLED: Enable/disable rate limiting (default: "true")
        Set to "false" to disable all rate limiting without code changes.
        Example: export RATE_LIMIT_ENABLED=false
    
    RATE_LIMIT_REQUESTS_PER_MINUTE: Global per-IP limit across all endpoints (default: 200)
        Specifies the number of requests allowed per minute per IP.
        Format: integer (plain number, without "/minute" suffix).
        Example: export RATE_LIMIT_REQUESTS_PER_MINUTE=300
        Backwards compatibility: RATE_LIMIT_DEFAULT env var supported if not set.
    
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
    
    TRUSTED_PROXIES: Comma-separated list of proxy IPs to trust for X-Forwarded-For
        When behind a reverse proxy, set this to the proxy's IP address.
        CRITICAL: Only X-Forwarded-For from these IPs will be trusted for rate limiting.
        Example: export TRUSTED_PROXIES=127.0.0.1,192.168.1.1
        If not set, rate limiting uses direct socket peer IP (only works for direct clients).

Typical Deployment Scenarios:
    - Direct deployment (no proxy):
        No configuration needed; limiter uses socket peer IP
    
    - Behind reverse proxy (nginx, Caddy, etc.):
        1. Set TRUSTED_PROXIES to proxy IP
        2. Ensure proxy sends X-Forwarded-For header
        3. Test by checking if different clients get independent rate limits
        Example: export TRUSTED_PROXIES=127.0.0.1
    
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
from starlette.responses import JSONResponse

from api.i18n import get_i18n

logger = logging.getLogger(__name__)

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

# Default global limit (per IP, all endpoints combined)
# Supports both RATE_LIMIT_REQUESTS_PER_MINUTE (documented name) and RATE_LIMIT_DEFAULT (legacy)
# Format: integer (requests per minute) or "N/minute" string
_requests_per_minute = os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE")
if _requests_per_minute:
    # Documented configuration variable - convert plain number to "N/minute" format
    _DEFAULT_LIMIT = f"{_requests_per_minute}/minute"
else:
    # Fallback to legacy variable name for backwards compatibility
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

# Parse trusted proxies from environment variable
# Only X-Forwarded-For headers from these IPs will be trusted
_TRUSTED_PROXIES_STR = os.getenv("TRUSTED_PROXIES", "")
TRUSTED_PROXIES = set(
    ip.strip() for ip in _TRUSTED_PROXIES_STR.split(",") if ip.strip()
) if _TRUSTED_PROXIES_STR else set()

def _rate_limit_key_func(request: Request) -> str | None:
    """
    Custom key function for rate limiting that respects X-Forwarded-For headers.
    
    Extracts the real client IP by:
    1. Checking if the direct peer (socket IP) is in TRUSTED_PROXIES
    2. If yes, extracting the leftmost IP from X-Forwarded-For header
    3. If no, using the direct peer IP
    
    Returns:
        IP address string for rate limiting key (client's real IP)
    
    SECURITY: Only trusts X-Forwarded-For from explicitly configured trusted proxies.
    Behind reverse proxies, you MUST set TRUSTED_PROXIES environment variable.
    
    Examples:
        Direct client (no proxy):
            request.client.host = "203.0.113.45"
            TRUSTED_PROXIES = {} (empty)
            Returns: "203.0.113.45" (use direct peer)
        
        Behind nginx proxy:
            request.client.host = "127.0.0.1" (proxy IP)
            TRUSTED_PROXIES = {"127.0.0.1"}
            X-Forwarded-For = "203.0.113.45, 10.0.0.1"
            Returns: "203.0.113.45" (leftmost from header)
        
        Proxy not in TRUSTED_PROXIES (spoofing attempt):
            request.client.host = "203.0.113.99" (untrusted)
            TRUSTED_PROXIES = {"127.0.0.1"}
            X-Forwarded-For = "203.0.113.45" (ignored - peer not trusted)
            Returns: "203.0.113.99" (use direct peer)
    """
    if not request.client:
        return None

    peer_ip = request.client.host

    # If peer is a trusted proxy, extract real client IP from X-Forwarded-For
    if TRUSTED_PROXIES and peer_ip in TRUSTED_PROXIES:
        # Get X-Forwarded-For header (may contain multiple IPs)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the leftmost IP (original client, before any proxy chain)
            client_ip = forwarded_for.split(",")[0].strip()
            if client_ip:
                return client_ip

    # Use direct peer IP (either not behind proxy, or peer not trusted)
    return peer_ip


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
    "get_cache_stats",
    "LIMIT_EXPENSIVE_BATCH",
    "LIMIT_EXPENSIVE_EVENTS",
    "LIMIT_STREAM_EVENTS",
    "LIMIT_CONTACT_TIMES",
    "LIMIT_CHEAP",
    "TRUSTED_PROXIES",
]
