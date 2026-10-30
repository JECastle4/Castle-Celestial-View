"""
Request-level HTTP response caching utilities for API endpoints.

Provides LRU cache with TTL (Time-To-Live) support for caching API responses
based on request parameters. This layer sits above service-level caching to
capture complete response caching, reducing redundant calculations for
identical requests.

Memory-aware caching: Cache is bounded by both entry count and total memory usage.
Responses exceeding max_entry_bytes are not cached. When total memory exceeds
max_memory_bytes, least-recently-used entries are evicted to stay within limits.
The response cache observes lifecycle changes per endpoint function name.
Reported bytes estimate retained response sizes, not process RSS; expirations
are counted when removed and are distinct from capacity-driven LRU evictions.

Thread-safe implementation protects against concurrent access from
synchronous routes running in the thread pool executor.
"""
import sys
import time
import functools
import inspect
import threading
from typing import Any, Callable, Optional
from collections import OrderedDict
from collections.abc import Hashable
from pydantic import BaseModel
from api.metrics import (
    record_cache_hit_safe, record_cache_miss_safe, record_cache_lifecycle_safe,
)

from api.i18n import get_i18n


class TTLCache:  # pylint: disable=too-many-instance-attributes
    """
    Thread-safe LRU cache with per-entry time-to-live (TTL) expiration and memory limits.

    Entries automatically expire after their TTL elapses. Expired entries are
    lazily removed on access. Cache is bounded by both:
    - Entry count (max_size)
    - Total memory usage (max_memory_bytes)

    Individual responses exceeding max_entry_bytes are not cached (skip caching).
    When total memory usage exceeds max_memory_bytes, least-recently-used entries
    are evicted to stay within the memory limit.

    Thread safety: All cache operations are protected by a lock to prevent
    race conditions when multiple requests access the cache concurrently from
    the thread pool executor.

    Args:
        max_size: Maximum number of entries to cache (default: 128)
        default_ttl: Default time-to-live for entries in seconds (default: 300)
        max_memory_bytes: Maximum total memory for cache in bytes (default: 100MB)
        max_entry_bytes: Maximum size of individual response to cache in bytes (default: 10MB)
        observer: Optional callback receiving (event, endpoint, estimated bytes, entries).
            Called under the cache lock; endpoint labels must be supplied explicitly.
    """

    def __init__(self, max_size: int = 128, default_ttl: int = 300,
                 max_memory_bytes: int = 100 * 1024 * 1024,
                 max_entry_bytes: int = 10 * 1024 * 1024,
                 observer: Optional[Callable[[str, str, int, int], None]] = None):
        # Configuration limits
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.max_memory_bytes = max_memory_bytes
        self.max_entry_bytes = max_entry_bytes
        # Cache storage
        self.cache: OrderedDict = OrderedDict()
        self.expiry: dict = {}
        self.entry_sizes: dict = {}  # Track memory usage per entry
        self.total_memory_used: int = 0  # Track total memory in cache
        # Thread safety
        self._lock = threading.RLock()  # Reentrant lock for nested lock acquisition
        self._observer = observer
        self._entry_endpoints: dict = {}
        self._endpoint_usage: dict = {}

    def _estimate_size(self, obj: Any) -> int:
        """
        Estimate memory usage of an object including nested structures.

        Uses sys.getsizeof() for base estimate and recursively accounts for
        memory in containers (dicts, lists, tuples) and Pydantic BaseModel objects.
        Pydantic models are converted with model_dump() to traverse nested data.
        This provides a reasonable approximation of actual memory usage for caching
        decisions.

        Args:
            obj: Object to estimate size of

        Returns:
            Estimated memory usage in bytes
        """
        size = sys.getsizeof(obj)

        # Handle Pydantic BaseModel objects by converting to dict first
        if isinstance(obj, BaseModel):
            obj = obj.model_dump()

        if isinstance(obj, dict):
            for key, value in obj.items():
                size += sys.getsizeof(key) + self._estimate_size(value)
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                size += self._estimate_size(item)
        # For other types (strings, numbers, sets, etc.) getsizeof is sufficient

        return size

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
                self._delete(key, event="expiration")
                return None

            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]

    def purge_expired(self) -> int:
        """
        Remove all expired entries from cache.

        Proactively purges expired entries to free capacity before evicting
        live LRU entries. This prevents live entries from being evicted when
        expired entries are consuming capacity.

        Thread-safe: protected by internal lock.

        Returns:
            Number of expired entries removed
        """
        with self._lock:
            expired_keys = [key for key in self.cache if self._is_expired(key)]
            for key in expired_keys:
                self._delete(key, event="expiration")
            return len(expired_keys)

    def set(self, key: Hashable, value: Any, ttl: Optional[int] = None,
            *, endpoint: Optional[str] = None) -> bool:
        """
        Store a value in cache with TTL.

        Entries larger than max_entry_bytes are not cached (returns False).
        If cache exceeds max_memory_bytes, evicts least-recently-used entries.
        If cache exceeds max_size entries, evicts least-recently-used entries.
        Thread-safe: protected by internal lock.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default_ttl if None)
            endpoint: Trusted function-name label for the observer, never a request key.
                Generic caches without an observer do not track endpoint metadata.

        Returns:
            True if value was cached, False if it exceeded max_entry_bytes
        """
        with self._lock:
            # Estimate size of this entry
            entry_size = self._estimate_size(value)

            # Skip caching if entry exceeds max_entry_bytes threshold
            if entry_size > self.max_entry_bytes:
                return False

            if ttl is None:
                ttl = self.default_ttl

            # Remove if already exists (will re-add as most recent)
            if key in self.cache:
                self._delete(key, event="replacement")

            # Purge expired entries first to avoid evicting live LRU entries
            self.purge_expired()

            # Evict LRU entries until we have space for this entry
            # Evict if: (a) by memory limit, or (b) by entry count
            while ((self.total_memory_used + entry_size > self.max_memory_bytes or
                    len(self.cache) >= self.max_size) and len(self.cache) > 0):
                lru_key = next(iter(self.cache))
                self._delete(lru_key, event="eviction")

            # Add new entry
            self.cache[key] = value
            self.expiry[key] = time.time() + ttl
            self.entry_sizes[key] = entry_size
            self.total_memory_used += entry_size
            if self._observer is not None and endpoint is not None:
                self._entry_endpoints[key] = endpoint
                usage = self._endpoint_usage.setdefault(endpoint, [0, 0])
                usage[0] += entry_size
                usage[1] += 1
                self._notify("set", endpoint)
            return True

    def _notify(self, event: str, endpoint: str) -> None:
        """Publish retained response estimates while holding the cache lock."""
        if self._observer is not None:
            bytes_used, entry_count = self._endpoint_usage[endpoint]
            self._observer(event, endpoint, bytes_used, entry_count)

    def _delete(self, key: Hashable, event: str = "delete") -> None:
        """Remove an entry from cache and update memory tracking."""
        if key in self.cache:
            # Subtract from total memory used
            entry_size = self.entry_sizes.get(key, 0)
            self.total_memory_used -= entry_size
            self.entry_sizes.pop(key, None)
            self.cache.pop(key)
            endpoint = self._entry_endpoints.pop(key, None)
            if endpoint is not None:
                usage = self._endpoint_usage[endpoint]
                usage[0] -= entry_size
                usage[1] -= 1
                self._notify(event, endpoint)
        self.expiry.pop(key, None)

    def clear(self) -> None:
        """Clear all cache entries. Thread-safe: protected by internal lock."""
        with self._lock:
            self.cache.clear()
            self.expiry.clear()
            self.entry_sizes.clear()
            self.total_memory_used = 0
            self._entry_endpoints.clear()
            for endpoint in self._endpoint_usage:
                self._endpoint_usage[endpoint] = [0, 0]
                self._notify("clear", endpoint)

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
                    self._delete(key, event="expiration")
            return count


# Global response cache instance
# max_memory_bytes=100MB, max_entry_bytes=10MB to prevent OOM from large batch responses
_response_cache = TTLCache(max_size=256, default_ttl=300,
                           max_memory_bytes=100 * 1024 * 1024,
                           max_entry_bytes=10 * 1024 * 1024,
                           observer=record_cache_lifecycle_safe)


def cache_response(ttl: int = 300):
    """
    Decorator to cache API responses based on request parameters.

    Generates cache key from request object by converting to JSON-serializable dict.
    Caches the complete response for identical requests within TTL window.
    Handles both synchronous and asynchronous endpoint functions.

    Tracks hits/misses and retained response lifecycle metrics by function name.

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
                                'astronomical_events_request', 'contact_times_request']
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
                _response_cache.set(cache_key, result, ttl=ttl, endpoint=endpoint_name)
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
                            'astronomical_events_request', 'contact_times_request']
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
            _response_cache.set(cache_key, result, ttl=ttl, endpoint=endpoint_name)
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
        Dict with cache size, capacity, and memory usage info
    """
    with _response_cache._lock:  # pylint: disable=protected-access
        entry_count = len(_response_cache)
        mem_pct = (
            _response_cache.total_memory_used / _response_cache.max_memory_bytes * 100
        )
        return {
            "cached_entries": entry_count,
            "max_entries": _response_cache.max_size,
            "entry_utilization_percent": entry_count / _response_cache.max_size * 100,
            "memory_used_bytes": _response_cache.total_memory_used,
            "max_memory_bytes": _response_cache.max_memory_bytes,
            "memory_utilization_percent": mem_pct,
            "max_entry_bytes": _response_cache.max_entry_bytes
        }
