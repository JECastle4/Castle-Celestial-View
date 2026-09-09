"""
Request-level HTTP response caching utilities for API endpoints.

Provides LRU cache with TTL (Time-To-Live) support for caching API responses
based on request parameters. This layer sits above service-level caching to
capture complete response caching, reducing redundant calculations for
identical requests.
"""
import time
import functools
import inspect
from typing import Any, Callable, Optional, Hashable
from collections import OrderedDict


class TTLCache:
    """
    LRU cache with per-entry time-to-live (TTL) expiration.
    
    Entries automatically expire after their TTL elapses. Expired entries are
    lazily removed on access. Cache size is limited by max_size; when full,
    least-recently-used entries are evicted.
    
    Args:
        max_size: Maximum number of entries to cache
        default_ttl: Default time-to-live for entries in seconds
    """

    def __init__(self, max_size: int = 128, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict = OrderedDict()
        self.expiry: dict = {}

    def _is_expired(self, key: Hashable) -> bool:
        """Check if an entry has expired."""
        if key not in self.expiry:
            return False
        return time.time() >= self.expiry[key]

    def get(self, key: Hashable) -> Optional[Any]:
        """
        Retrieve a value from cache if it exists and hasn't expired.
        
        Moving accessed entries to end (most recently used).
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if found and not expired, else None
        """
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
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default_ttl if None)
        """
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
        """Clear all cache entries."""
        self.cache.clear()
        self.expiry.clear()

    def __len__(self) -> int:
        """Return number of non-expired entries in cache."""
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
        
        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Extract request object (should be first positional arg after 'self' if method)
                request = args[0] if args else kwargs.get('request')
                
                if request is None:
                    # No cacheable request, proceed without caching
                    return await func(*args, **kwargs)

                # Generate cache key from request
                cache_key = _generate_cache_key(func.__name__, request)

                # Try to get from cache
                cached = _response_cache.get(cache_key)
                if cached is not None:
                    return cached

                # Execute function and cache result
                result = await func(*args, **kwargs)
                _response_cache.set(cache_key, result, ttl=ttl)
                return result

            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Extract request object (should be first positional arg after 'self' if method)
                request = args[0] if args else kwargs.get('request')
                
                if request is None:
                    # No cacheable request, proceed without caching
                    return func(*args, **kwargs)

                # Generate cache key from request
                cache_key = _generate_cache_key(func.__name__, request)

                # Try to get from cache
                cached = _response_cache.get(cache_key)
                if cached is not None:
                    return cached

                # Execute function and cache result
                result = func(*args, **kwargs)
                _response_cache.set(cache_key, result, ttl=ttl)
                return result

            return sync_wrapper

    return decorator




def _generate_cache_key(func_name: str, request: Any) -> tuple:
    """
    Generate a hashable cache key from function name, request object, and locale.
    
    Converts request to a serializable representation. For Pydantic models,
    uses dict() representation. Falls back to str() for other types.
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
    except Exception:
        request_dict = {}

    # Include current locale in cache key to ensure locale-specific responses are cached separately
    try:
        locale = get_i18n().locale
    except Exception:
        locale = 'en'  # Default to 'en' if locale context not available

    # Convert dict to sorted tuple of items for hashability
    request_tuple = tuple(sorted(request_dict.items()))
    return (func_name, locale, request_tuple)



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
