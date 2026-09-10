"""
Request-level HTTP response caching utilities for API endpoints.

Provides LRU cache with TTL (Time-To-Live) support for caching API responses
based on request parameters. This layer sits above service-level caching to
capture complete response caching, reducing redundant calculations for
identical requests.

Thread-safe implementation protects against concurrent access from
synchronous routes running in the thread pool executor.
"""
import time
import functools
import inspect
import threading
from typing import Any, Callable, Optional, Hashable
from collections import OrderedDict
from api.metrics import record_cache_hit_safe, record_cache_miss_safe

from api.i18n import get_i18n


class TTLCache:
    """
    Thread-safe LRU cache with per-entry time-to-live (TTL) expiration.

    Entries automatically expire after their TTL elapses. Expired entries are
    lazily removed on access. Cache size is limited by max_size; when full,
    least-recently-used entries are evicted.

    Thread safety: All cache operations are protected by a lock to prevent
    race conditions when multiple requests access the cache concurrently from
    the thread pool executor.

    Args:
        max_size: Maximum number of entries to cache
        default_ttl: Default time-to-live for entries in seconds
    """

    def __init__(self, max_size: int = 128, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict = OrderedDict()
        self.expiry: dict = {}
        self._lock = threading.RLock()  # Reentrant lock for nested lock acquisition

    def _is_expired(self, key: Hashable) -> bool:
        """Check if an entry has expired."""
        if key not in self.expiry:
            return False
        return time.time() >= self.expiry[key]

    def get(self, key: Hashable) -> Optional[Any]:
        """
        Retrieve a value from cache if it exists and hasn't expired.

        Moving accessed entries to end (most recently used).
        Thread-safe: protected by internal lock.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, else None
        """
        with self._lock:
            if key not in self.cache:
                return None

            if self._is_expired(key):
                self._delete(key)
                return None

            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]

    def set(self, key: Hashable, value: Any, ttl: Optional[int] = None) -> None:
        """
        Store a value in cache with TTL.

        If cache is full, evicts least-recently-used entry.
        Thread-safe: protected by internal lock.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default_ttl if None)
        """
        with self._lock:
            if ttl is None:
                ttl = self.default_ttl

            # Remove if already exists (will re-add as most recent)
            if key in self.cache:
                self.cache.pop(key)
                self.expiry.pop(key, None)

            # Evict LRU if at capacity
            if len(self.cache) >= self.max_size:
                lru_key = next(iter(self.cache))
                self._delete(lru_key)

            # Add new entry
            self.cache[key] = value
            self.expiry[key] = time.time() + ttl

    def _delete(self, key: Hashable) -> None:
        """Remove an entry from cache."""
        self.cache.pop(key, None)
        self.expiry.pop(key, None)

    def clear(self) -> None:
        """Clear all cache entries. Thread-safe: protected by internal lock."""
        with self._lock:
            self.cache.clear()
            self.expiry.clear()

    def __len__(self) -> int:
        """
        Return number of non-expired entries in cache.
        Thread-safe: protected by internal lock.
        """
        with self._lock:
            # Count non-expired entries
            count = 0
            for key in list(self.cache.keys()):
                if not self._is_expired(key):
                    count += 1
                else:
                    self._delete(key)
            return count


# Global response cache instance
_response_cache = TTLCache(max_size=256, default_ttl=300)


def cache_response(ttl: int = 300):
    """
    Decorator to cache API responses based on request parameters.

    Generates cache key from request object by converting to JSON-serializable dict.
    Caches the complete response for identical requests within TTL window.
    Handles both synchronous and asynchronous endpoint functions.

    Tracks cache hits/misses to Prometheus metrics (Phase 3.2).

    Usage:
        @cache_response(ttl=300)
        async def get_batch_earth_observations(request: BatchEarthObservationsRequest):
            ...

        @cache_response(ttl=300)
        def get_astronomical_events_route(request: AstronomicalEventsRequest, ...):
            ...

    Args:
        ttl: Time-to-live for cached responses in seconds (default: 300s / 5 min)
    """

    def decorator(func: Callable) -> Callable:
        is_async = inspect.iscoroutinefunction(func)
        # Get endpoint name for metrics labeling
        endpoint_name = func.__name__

        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Extract Pydantic request model for caching.
                # Skip Starlette Request objects (used for SlowAPI rate limiting).
                request = None

                # Try positional args first, skipping Starlette Request
                for arg in args:
                    # Skip Starlette Request and other non-Pydantic types
                    if hasattr(arg, '__pydantic_complete__') or (
                        hasattr(arg, 'model_dump') or hasattr(arg, 'dict')
                    ):
                        request = arg
                        break

                # If not found in positional args, check kwargs for common request names
                if request is None:
                    req_keys = ['request', 'batch_request', 'events_request',
                                'astronomical_events_request']
                    for key in req_keys:
                        if key in kwargs and (
                            hasattr(kwargs[key], 'model_dump') or hasattr(kwargs[key], 'dict')
                        ):
                            request = kwargs[key]
                            break

                if request is None:
                    # No cacheable Pydantic model found, proceed without caching
                    return await func(*args, **kwargs)

                # Generate cache key from request
                cache_key = _generate_cache_key(func.__name__, request)

                # Try to get from cache
                cached = _response_cache.get(cache_key)
                if cached is not None:
                    # Cache hit - record metric
                    record_cache_hit_safe(endpoint_name)
                    return cached

                # Cache miss
                record_cache_miss_safe(endpoint_name)

                # Execute function and cache result
                result = await func(*args, **kwargs)
                _response_cache.set(cache_key, result, ttl=ttl)
                return result

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Extract Pydantic request model for caching.
            # Skip Starlette Request objects (used for SlowAPI rate limiting).
            request = None

            # Try positional args first, skipping Starlette Request
            for arg in args:
                # Skip Starlette Request and other non-Pydantic types
                if hasattr(arg, '__pydantic_complete__') or (
                    hasattr(arg, 'model_dump') or hasattr(arg, 'dict')
                ):
                    request = arg
                    break

            # If not found in positional args, check kwargs for common request names
            if request is None:
                req_keys = ['request', 'batch_request', 'events_request',
                            'astronomical_events_request']
                for key in req_keys:
                    if key in kwargs and (
                        hasattr(kwargs[key], 'model_dump') or hasattr(kwargs[key], 'dict')
                    ):
                        request = kwargs[key]
                        break

            if request is None:
                # No cacheable Pydantic model found, proceed without caching
                return func(*args, **kwargs)

            # Generate cache key from request
            cache_key = _generate_cache_key(func.__name__, request)

            # Try to get from cache
            cached = _response_cache.get(cache_key)
            if cached is not None:
                # Cache hit - record metric
                record_cache_hit_safe(endpoint_name)
                return cached

            # Cache miss
            record_cache_miss_safe(endpoint_name)

            # Execute function and cache result
            result = func(*args, **kwargs)
            _response_cache.set(cache_key, result, ttl=ttl)
            return result

        return sync_wrapper

    return decorator


def _normalize_to_hashable(value: Any) -> Any:
    """
    Recursively convert unhashable types to hashable equivalents.

    Transforms nested structures so they can be used in tuple cache keys:
    - list -> tuple
    - dict -> frozenset of items
    - tuple/frozenset -> recursively normalize contents
    - primitive types -> unchanged

    Args:
        value: Value to normalize

    Returns:
        Hashable equivalent of value
    """
    if isinstance(value, dict):
        # Convert dict to frozenset of normalized items
        return frozenset((k, _normalize_to_hashable(v)) for k, v in value.items())
    if isinstance(value, list):
        # Convert list to tuple of normalized items
        return tuple(_normalize_to_hashable(item) for item in value)
    if isinstance(value, tuple):
        # Recursively normalize tuple contents
        return tuple(_normalize_to_hashable(item) for item in value)
    if isinstance(value, frozenset):
        # Frozenset is already hashable, but normalize contents just in case
        return frozenset(_normalize_to_hashable(item) for item in value)
    # Primitives (int, str, bool, None, etc.) are already hashable
    return value


def _generate_cache_key(func_name: str, request: Any) -> tuple:
    """
    Generate a hashable cache key from function name, request object, and locale.

    Converts request to a serializable representation. For Pydantic models,
    uses dict() representation. Normalizes nested unhashable types (lists, dicts)
    to hashable equivalents (tuples, frozensets) to ensure cache key is always
    hashable and can be used as dictionary key.

    Includes current locale in cache key to prevent cross-locale response mixing.

    Args:
        func_name: Name of the endpoint function
        request: Request object (typically Pydantic model)

    Returns:
        Hashable tuple suitable as cache key
    """
    try:
        # For Pydantic models
        if hasattr(request, 'model_dump'):
            request_dict = request.model_dump()
        elif hasattr(request, 'dict'):
            request_dict = request.dict()
        else:
            request_dict = vars(request) if hasattr(request, '__dict__') else {}
    except Exception:  # pylint: disable=broad-exception-caught
        request_dict = {}

    # Include current locale in cache key to ensure locale-specific responses are cached separately
    try:
        locale = get_i18n().locale
    except Exception:  # pylint: disable=broad-exception-caught
        locale = 'en'  # Default to 'en' if locale context not available

    # Normalize dict items to hashable types (convert lists to tuples, dicts to frozensets, etc.)
    normalized_items = tuple(
        (k, _normalize_to_hashable(v)) for k, v in sorted(request_dict.items())
    )
    return (func_name, locale, normalized_items)



def clear_response_cache() -> None:
    """Clear all cached responses. Useful for testing or cache invalidation."""
    _response_cache.clear()


def get_cache_stats() -> dict:
    """
    Get cache statistics for monitoring and debugging.

    Returns:
        Dict with cache size and capacity info
    """
    return {
        "cached_entries": len(_response_cache),
        "max_size": _response_cache.max_size,
        "utilization": len(_response_cache) / _response_cache.max_size * 100
    }
