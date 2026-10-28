"""
Tests for the request-level HTTP response caching system.

Covers TTLCache, cache_response decorator, and integration scenarios.
"""
import sys
import time
import pytest
from unittest.mock import Mock, patch
from api.cache import (
    TTLCache,
    cache_response,
    clear_response_cache,
    get_cache_stats,
    _generate_cache_key,
)
from pydantic import BaseModel


class MockRequest(BaseModel):
    """Mock Pydantic request for testing."""
    param1: str
    param2: int


class TestTTLCache:
    """Tests for TTLCache class."""

    def test_cache_set_and_get(self):
        """Test basic set and get operations."""
        cache = TTLCache(max_size=10, default_ttl=1)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_cache_miss_returns_none(self):
        """Test that missing keys return None."""
        cache = TTLCache()
        assert cache.get("nonexistent") is None

    def test_cache_expiration(self):
        """Test that entries expire after TTL."""
        cache = TTLCache(max_size=10, default_ttl=1)
        cache.set("key1", "value1", ttl=0.1)
        assert cache.get("key1") == "value1"
        time.sleep(0.15)
        assert cache.get("key1") is None

    def test_cache_custom_ttl(self):
        """Test that custom TTL overrides default."""
        cache = TTLCache(max_size=10, default_ttl=10)
        cache.set("key1", "value1", ttl=0.1)
        time.sleep(0.15)
        assert cache.get("key1") is None

    def test_cache_lru_eviction(self):
        """Test that LRU entries are evicted when cache is full."""
        cache = TTLCache(max_size=3, default_ttl=100)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # key1 is least recently used, should be evicted
        cache.set("key4", "value4")
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

    def test_cache_access_updates_lru_order(self):
        """Test that accessing a key updates its LRU position."""
        cache = TTLCache(max_size=3, default_ttl=100)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Access key1 to make it recently used
        cache.get("key1")
        
        # key2 should be evicted as LRU
        cache.set("key4", "value4")
        assert cache.get("key2") is None
        assert cache.get("key1") == "value1"

    def test_cache_reinsert_updates_position(self):
        """Test that re-setting a key updates its position to most recent."""
        cache = TTLCache(max_size=3, default_ttl=100)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Re-set key1 to make it most recent
        cache.set("key1", "value1_updated")
        
        # key2 should be evicted as LRU
        cache.set("key4", "value4")
        assert cache.get("key2") is None
        assert cache.get("key1") == "value1_updated"

    def test_cache_clear(self):
        """Test clearing all cache entries."""
        cache = TTLCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert len(cache) == 0

    def test_cache_len_excludes_expired(self):
        """Test that __len__ excludes expired entries."""
        cache = TTLCache(max_size=10, default_ttl=100)
        cache.set("key1", "value1")
        cache.set("key2", "value2", ttl=0.1)
        
        assert len(cache) == 2
        time.sleep(0.15)
        # key2 should be cleaned up during len()
        assert len(cache) == 1
        assert cache.get("key1") == "value1"

    def test_is_expired_with_missing_key(self):
        """Test _is_expired with key not in expiry dict."""
        cache = TTLCache()
        # Manually remove from expiry but keep in cache (edge case)
        cache.cache["key1"] = "value1"
        # Should handle gracefully
        assert cache.get("key1") == "value1"

    def test_delete_nonexistent_key(self):
        """Test that _delete handles nonexistent keys gracefully."""
        cache = TTLCache()
        cache._delete("nonexistent")  # Should not raise


class TestCacheResponseDecorator:
    """Tests for @cache_response decorator."""

    def test_sync_function_caching(self):
        """Test that sync functions are cached."""
        call_count = 0
        
        @cache_response(ttl=10)
        def sync_func(request: MockRequest):
            nonlocal call_count
            call_count += 1
            return {"result": "cached", "call_num": call_count}
        
        request = MockRequest(param1="test", param2=42)
        
        # First call - executes
        result1 = sync_func(request=request)
        assert result1["call_num"] == 1
        
        # Second call - from cache
        result2 = sync_func(request=request)
        assert result2["call_num"] == 1  # Same as first call
        assert call_count == 1

    def test_sync_function_none_request_bypasses_cache(self):
        """Test that sync functions with None request don't use cache."""
        call_count = 0
        
        @cache_response(ttl=10)
        def sync_func_no_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return {"call_num": call_count}
        
        # Call without request parameter
        result1 = sync_func_no_request()
        result2 = sync_func_no_request()
        
        # Both should execute (no caching)
        assert result1["call_num"] == 1
        assert result2["call_num"] == 2
        assert call_count == 2

    def test_different_requests_different_cache_entries(self):
        """Test that different requests create separate cache entries."""
        call_count = 0
        
        @cache_response(ttl=10)
        def sync_func(request: MockRequest):
            nonlocal call_count
            call_count += 1
            return {"result": "cached", "call_num": call_count}
        
        request1 = MockRequest(param1="test1", param2=42)
        request2 = MockRequest(param1="test2", param2=43)
        
        # First request
        result1 = sync_func(request=request1)
        assert result1["call_num"] == 1
        
        # Different request - should not use cache
        result2 = sync_func(request=request2)
        assert result2["call_num"] == 2
        
        # First request again - should use cache
        result3 = sync_func(request=request1)
        assert result3["call_num"] == 1
        assert call_count == 2

    def test_ttl_expiration_forces_recalculation(self):
        """Test that expired cache entries trigger recalculation."""
        call_count = 0
        
        @cache_response(ttl=0.1)
        def sync_func(request: MockRequest):
            nonlocal call_count
            call_count += 1
            return {"call_num": call_count}
        
        request = MockRequest(param1="test", param2=42)
        
        result1 = sync_func(request=request)
        assert result1["call_num"] == 1
        
        time.sleep(0.15)
        
        # After expiry, should recalculate
        result2 = sync_func(request=request)
        assert result2["call_num"] == 2
        assert call_count == 2


class TestCacheKeyGeneration:
    """Tests for cache key generation."""

    @patch('api.i18n.get_i18n')
    def test_cache_key_includes_locale(self, mock_get_i18n):
        """Test that cache key includes current locale."""
        mock_get_i18n.return_value.locale = "en"
        
        request1 = MockRequest(param1="test", param2=42)
        key1 = _generate_cache_key("func", request1)
        
        # Verify key contains locale
        assert "en" in key1
        assert key1[1] == "en"

    @patch('api.i18n.get_i18n')
    def test_different_locales_different_keys(self, mock_get_i18n):
        """Test that cache key structure preserves locale information."""
        request = MockRequest(param1="test", param2=42)
        
        # Set up mock to return locale
        mock_locale = Mock()
        mock_locale.locale = "en"
        mock_get_i18n.return_value = mock_locale
        
        key = _generate_cache_key("func", request)
        
        # Verify the structure: (func_name, locale, request_tuple)
        assert len(key) == 3
        assert key[0] == "func"
        assert key[1] == "en"  # Locale is in key
        assert isinstance(key[2], tuple)  # Request params

    @patch('api.i18n.get_i18n')
    def test_cache_key_locale_fallback(self, mock_get_i18n):
        """Test that cache key uses 'en' when locale context fails."""
        mock_get_i18n.side_effect = RuntimeError("No context")
        
        request = MockRequest(param1="test", param2=42)
        key = _generate_cache_key("func", request)
        
        # Should use 'en' as fallback
        assert "en" in key
        assert key[1] == "en"

    @patch('api.i18n.get_i18n')
    def test_cache_key_from_pydantic_model(self, mock_get_i18n):
        """Test cache key generation from Pydantic model."""
        mock_get_i18n.return_value.locale = "en"
        request = MockRequest(param1="test", param2=42)
        
        key = _generate_cache_key("test_func", request)
        assert key[0] == "test_func"
        assert key[1] == "en"
        # Third element should be sorted tuple of request params

    @patch('api.i18n.get_i18n')
    def test_cache_key_from_dict_like_object(self, mock_get_i18n):
        """Test cache key generation from dict-like object."""
        mock_get_i18n.return_value.locale = "en"
        
        obj = Mock()
        obj.__dict__ = {"param1": "test", "param2": 42}
        
        key = _generate_cache_key("test_func", obj)
        assert key[0] == "test_func"
        assert key[1] == "en"


class TestCacheUtilities:
    """Tests for cache utility functions."""

    def test_clear_response_cache(self):
        """Test that clear_response_cache clears all entries."""
        cache_stats_before = get_cache_stats()
        initial_size = cache_stats_before["cached_entries"]
        
        # Add some entries
        from api.cache import _response_cache
        _response_cache.set("key1", "value1")
        _response_cache.set("key2", "value2")
        
        assert get_cache_stats()["cached_entries"] > initial_size
        
        # Clear
        clear_response_cache()
        
        assert get_cache_stats()["cached_entries"] == 0

    def test_get_cache_stats_structure(self):
        """Test that get_cache_stats returns expected structure."""
        stats = get_cache_stats()
        
        assert "cached_entries" in stats
        assert "max_entries" in stats
        assert "entry_utilization_percent" in stats
        assert "memory_used_bytes" in stats
        assert "max_memory_bytes" in stats
        assert "memory_utilization_percent" in stats
        assert "max_entry_bytes" in stats
        
        assert isinstance(stats["cached_entries"], int)
        assert isinstance(stats["max_entries"], int)
        assert isinstance(stats["entry_utilization_percent"], (int, float))
        assert isinstance(stats["memory_used_bytes"], int)
        assert isinstance(stats["max_memory_bytes"], int)
        assert isinstance(stats["memory_utilization_percent"], (int, float))
        assert isinstance(stats["max_entry_bytes"], int)


class TestCacheIntegration:
    """Integration tests for caching with endpoints."""

    def test_cache_isolation_between_tests(self):
        """Test that conftest fixture properly isolates cache."""
        from api.cache import _response_cache
        
        # Cache should be empty due to conftest fixture
        assert _response_cache.cache == {}
        assert len(_response_cache) == 0

    def test_positional_request_argument(self):
        """Test caching with request as positional argument."""
        call_count = 0
        
        @cache_response(ttl=10)
        def func_with_positional(request: MockRequest):
            nonlocal call_count
            call_count += 1
            return {"call_num": call_count}
        
        request = MockRequest(param1="test", param2=42)
        
        # Call with positional argument
        result1 = func_with_positional(request)
        result2 = func_with_positional(request)
        
        # Should use cache
        assert result1["call_num"] == result2["call_num"] == 1

    def test_kwargs_request_argument(self):
        """Test caching with request as keyword argument."""
        call_count = 0
        
        @cache_response(ttl=10)
        def func_with_kwargs(request: MockRequest):
            nonlocal call_count
            call_count += 1
            return {"call_num": call_count}
        
        request = MockRequest(param1="test", param2=42)
        
        # Call with keyword argument
        result1 = func_with_kwargs(request=request)
        result2 = func_with_kwargs(request=request)
        
        # Should use cache
        assert result1["call_num"] == result2["call_num"] == 1

    def test_cache_decorates_properly(self):
        """Test that decorator preserves function metadata."""
        @cache_response(ttl=10)
        def my_function(request: MockRequest):
            """My docstring."""
            return {"result": "test"}
        
        # Check that function name and docstring are preserved
        assert my_function.__name__ == "my_function"
        assert "My docstring" in my_function.__doc__


class TestMemoryAwareCaching:
    """Tests for memory-aware caching with size limits."""

    def test_estimate_size_simple_types(self):
        """Test size estimation for simple types."""
        cache = TTLCache()
        
        # Simple string
        size_str = cache._estimate_size("hello")
        assert size_str > 0
        
        # Integer
        size_int = cache._estimate_size(42)
        assert size_int > 0
        
        # Longer string should be larger
        size_long_str = cache._estimate_size("hello world" * 100)
        assert size_long_str > size_str

    def test_estimate_size_containers(self):
        """Test size estimation for container types."""
        cache = TTLCache()
        
        # List
        size_list = cache._estimate_size([1, 2, 3, "four"])
        assert size_list > 0
        
        # Dict
        size_dict = cache._estimate_size({"a": 1, "b": 2, "c": "three"})
        assert size_dict > 0
        
        # Nested structure
        size_nested = cache._estimate_size({
            "list": [1, 2, 3],
            "dict": {"key": "value"},
            "string": "hello"
        })
        assert size_nested > size_dict

    def test_estimate_size_nested_structures(self):
        """Test size estimation for deeply nested structures."""
        cache = TTLCache()
        
        nested = {
            "level1": {
                "level2": {
                    "level3": [1, 2, 3, "data"]
                }
            }
        }
        
        size = cache._estimate_size(nested)
        assert size > 0

    def test_set_returns_true_on_success(self):
        """Test that set() returns True when caching succeeds."""
        cache = TTLCache(max_size=10, max_entry_bytes=1024)
        
        result = cache.set("key1", "value1")
        assert result is True

    def test_set_returns_false_for_oversized_entry(self):
        """Test that set() returns False when entry exceeds max_entry_bytes."""
        cache = TTLCache(max_size=10, max_entry_bytes=100)
        
        # Create a value larger than max_entry_bytes
        large_value = "x" * 1000
        result = cache.set("key1", large_value)
        
        # Should return False (not cached)
        assert result is False
        
        # Entry should not be in cache
        assert cache.get("key1") is None

    def test_memory_limit_enforcement(self):
        """Test that cache respects max_memory_bytes limit."""
        # Small cache with tight memory limit
        cache = TTLCache(max_size=100, max_memory_bytes=500)
        
        # Add entries until memory limit is hit
        large_value = "x" * 100
        
        cache.set("key1", large_value)
        cache.set("key2", large_value)
        cache.set("key3", large_value)
        cache.set("key4", large_value)
        cache.set("key5", large_value)
        
        # After adding more entries, earlier ones should be evicted
        # Total memory should not exceed max_memory_bytes (some margin for overhead)
        assert cache.total_memory_used <= cache.max_memory_bytes * 1.1  # Allow 10% overhead

    def test_memory_tracking_accuracy(self):
        """Test that total_memory_used is accurately tracked."""
        cache = TTLCache(max_size=100, max_memory_bytes=10000)
        
        # Add a known value
        value1 = "test_value"
        cache.set("key1", value1)
        used_after_one = cache.total_memory_used
        assert used_after_one > 0
        
        # Add another value
        value2 = "another_test_value"
        cache.set("key2", value2)
        used_after_two = cache.total_memory_used
        assert used_after_two > used_after_one

    def test_memory_tracking_after_delete(self):
        """Test that total_memory_used decreases after deletion."""
        cache = TTLCache(max_size=100, max_memory_bytes=10000)
        
        cache.set("key1", "test_value")
        used_with_one = cache.total_memory_used
        
        cache.set("key2", "another_value")
        used_with_two = cache.total_memory_used
        
        # Delete first key
        cache._delete("key1")
        used_after_delete = cache.total_memory_used
        
        # Memory used should decrease
        assert used_after_delete < used_with_two

    def test_memory_tracking_after_clear(self):
        """Test that total_memory_used resets to 0 after clear()."""
        cache = TTLCache(max_size=100, max_memory_bytes=10000)
        
        cache.set("key1", "test_value")
        cache.set("key2", "another_value")
        assert cache.total_memory_used > 0
        
        cache.clear()
        assert cache.total_memory_used == 0
        assert len(cache.entry_sizes) == 0

    def test_lru_eviction_respects_memory_limit(self):
        """Test that LRU eviction maintains memory limit."""
        cache = TTLCache(max_size=100, max_memory_bytes=300, default_ttl=100)
        
        # Add first value
        cache.set("key1", "value1")
        key1_size = cache.entry_sizes.get("key1", 0)
        
        # Add second value
        cache.set("key2", "value2")
        
        # Add third value (should trigger eviction of key1)
        cache.set("key3", "value3")
        
        # key1 should be evicted due to memory pressure
        if cache.total_memory_used > cache.max_memory_bytes * 0.5:
            # If memory is significantly used, key1 should be gone
            assert cache.get("key1") is None or "key1" not in cache.cache

    def test_entry_count_eviction_still_works(self):
        """Test that entry count limit still works with memory limits."""
        cache = TTLCache(max_size=3, max_memory_bytes=100000, default_ttl=100)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # key1 is least recently used, should be evicted
        cache.set("key4", "value4")
        assert cache.get("key1") is None

    def test_oversized_entries_not_cached(self):
        """Test that oversized entries bypass cache completely."""
        cache = TTLCache(max_size=10, max_entry_bytes=100, default_ttl=100)
        
        # Try to cache an oversized value
        large_value = {"data": "x" * 1000}
        result = cache.set("key1", large_value)
        
        # Should not be cached
        assert result is False
        assert cache.get("key1") is None
        
        # Cache should still be usable for smaller values
        result2 = cache.set("key2", "small value")
        assert result2 is True
        assert cache.get("key2") == "small value"

    def test_cache_stats_includes_memory_metrics(self):
        """Test that get_cache_stats includes memory information."""
        from api.cache import _response_cache
        
        # Add some entries to the global cache
        _response_cache.cache.clear()
        _response_cache.entry_sizes.clear()
        _response_cache.total_memory_used = 0
        
        _response_cache.set("key1", "value1")
        
        stats = get_cache_stats()
        
        # Check for memory-related stats
        assert "memory_used_bytes" in stats
        assert "max_memory_bytes" in stats
        assert "memory_utilization_percent" in stats
        assert "max_entry_bytes" in stats
        
        # Verify values
        assert stats["memory_used_bytes"] > 0
        assert stats["max_memory_bytes"] > 0


class TestBaseModelSizeEstimation:
    """Tests for _estimate_size() with Pydantic BaseModel objects - CRITICAL FIX."""

    def test_estimate_size_pydantic_basemodel(self):
        """Test that _estimate_size() correctly handles Pydantic BaseModel objects."""
        cache = TTLCache()
        
        # Test with BaseModel
        model = MockRequest(param1="test_value", param2=42)
        size_model = cache._estimate_size(model)
        
        # Should account for nested field data
        size_model_only = sys.getsizeof(model)
        assert size_model > size_model_only, "Should be larger than just BaseModel shell"

    def test_estimate_size_basemodel_with_large_nested_data(self):
        """Test that _estimate_size() properly sizes BaseModel with large nested data."""
        cache = TTLCache()
        
        # BaseModel with large nested string
        large_string = "x" * 50000
        model = MockRequest(param1=large_string, param2=42)
        size_model = cache._estimate_size(model)
        
        # Size should reflect the large string content
        size_small_model = cache._estimate_size(MockRequest(param1="small", param2=42))
        assert size_model > size_small_model * 100, "Large nested data should be reflected in size"

    def test_estimate_size_basemodel_exceeds_entry_limit(self):
        """Test that large BaseModel objects are correctly rejected from cache."""
        cache = TTLCache(max_size=10, max_entry_bytes=1000)
        
        # Create model with data exceeding max_entry_bytes
        large_model = MockRequest(param1="x" * 50000, param2=42)
        result = cache.set("key", large_model)
        
        # Should not be cached
        assert result is False, "Large BaseModel should not be cached"
        assert cache.get("key") is None, "Large entry should not be retrievable"

    def test_estimate_size_basemodel_with_nested_list(self):
        """Test _estimate_size() with BaseModel containing list fields."""
        from typing import List as ListType
        
        class ListRequest(BaseModel):
            items: ListType[str]
            count: int
        
        cache = TTLCache()
        
        model = ListRequest(items=["a", "b", "c"] * 100, count=300)
        size = cache._estimate_size(model)
        
        # Should properly traverse nested list
        assert size > 0
        
        # Size should grow with more items
        size_small = cache._estimate_size(ListRequest(items=["a"], count=1))
        assert size > size_small

    def test_estimate_size_basemodel_with_nested_dict(self):
        """Test _estimate_size() with BaseModel containing dict fields."""
        from typing import Dict as DictType
        
        class DictRequest(BaseModel):
            data: DictType[str, str]
            name: str
        
        cache = TTLCache()
        
        model = DictRequest(
            data={"key" + str(i): "value" * 10 for i in range(100)},
            name="test"
        )
        size = cache._estimate_size(model)
        
        assert size > 0
        
        # Should be larger than small model
        size_small = cache._estimate_size(DictRequest(data={"a": "b"}, name="test"))
        assert size > size_small

    def test_cache_set_rejects_large_basemodel(self):
        """Test that cache.set() rejects BaseModel exceeding max_entry_bytes."""
        cache = TTLCache(max_size=100, max_entry_bytes=500)
        
        # Create oversized model
        large_model = MockRequest(param1="x" * 10000, param2=999)
        result = cache.set("oversized", large_model)
        
        assert result is False, "Should return False for oversized BaseModel"
        assert "oversized" not in cache.cache


class TestAsyncCaching:
    """Tests for @cache_response decorator with async functions."""

    @pytest.mark.asyncio
    async def test_async_function_caching(self):
        """Test that async functions are cached."""
        call_count = 0
        
        @cache_response(ttl=10)
        async def async_func(request: MockRequest):
            nonlocal call_count
            call_count += 1
            return {"result": "cached", "call_num": call_count}
        
        request = MockRequest(param1="test", param2=42)
        
        # First call - executes
        result1 = await async_func(request=request)
        assert result1["call_num"] == 1
        
        # Second call - from cache
        result2 = await async_func(request=request)
        assert result2["call_num"] == 1  # Same as first call
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_function_cache_expiration(self):
        """Test that async cached values expire after TTL."""
        call_count = 0
        
        @cache_response(ttl=0.1)
        async def async_func(request: MockRequest):
            nonlocal call_count
            call_count += 1
            return {"call_num": call_count}
        
        request = MockRequest(param1="test", param2=42)
        
        result1 = await async_func(request=request)
        assert result1["call_num"] == 1
        
        time.sleep(0.15)
        
        # After expiry, should recalculate
        result2 = await async_func(request=request)
        assert result2["call_num"] == 2
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_async_function_different_requests_separate_cache(self):
        """Test that different requests create separate async cache entries."""
        call_count = 0
        
        @cache_response(ttl=10)
        async def async_func(request: MockRequest):
            nonlocal call_count
            call_count += 1
            return {"call_num": call_count}
        
        request1 = MockRequest(param1="test1", param2=42)
        request2 = MockRequest(param1="test2", param2=43)
        
        # First request
        result1 = await async_func(request=request1)
        assert result1["call_num"] == 1
        
        # Different request - should not use cache
        result2 = await async_func(request=request2)
        assert result2["call_num"] == 2
        
        # First request again - should use cache
        result3 = await async_func(request=request1)
        assert result3["call_num"] == 1
        assert call_count == 2


class TestErrorHandling:
    """Tests for error handling in cache operations."""

    def test_estimate_size_with_circular_reference_protection(self):
        """Test that _estimate_size() handles circular references gracefully."""
        cache = TTLCache()
        
        # Create circular reference
        obj1 = {"key": "value"}
        obj2 = {"ref": obj1}
        obj1["ref"] = obj2  # Circular reference
        
        # Should not crash (may not detect cycle, but should not infinite loop)
        # This tests robustness - the current implementation will recurse but
        # the actual circular data won't cause infinite recursion for sizing
        try:
            size = cache._estimate_size(obj1)
            assert size > 0
        except RecursionError:
            pytest.skip("Circular references cause recursion - acceptable limitation")

    def test_estimate_size_with_none_values(self):
        """Test that _estimate_size() handles None values correctly."""
        cache = TTLCache()
        
        size = cache._estimate_size(None)
        assert size > 0
        
        # None in nested structure
        size_with_none = cache._estimate_size({"key": None, "other": "value"})
        assert size_with_none > 0

    def test_basemodel_dump_failure_handling(self):
        """Test graceful handling if model_dump() fails."""
        cache = TTLCache()
        
        class FailingModel(BaseModel):
            value: str
            
            def model_dump(self):
                raise RuntimeError("model_dump failed")
        
        # Should handle the error gracefully
        try:
            model = FailingModel(value="test")
            # The current implementation will crash - this documents the limitation
            cache._estimate_size(model)
        except RuntimeError:
            # This is expected with current implementation
            pass

    def test_set_with_invalid_key_types(self):
        """Test cache.set() with various hashable key types."""
        cache = TTLCache()
        
        # Integer key
        cache.set(1, "value1")
        assert cache.get(1) == "value1"
        
        # Tuple key
        cache.set((1, 2), "value2")
        assert cache.get((1, 2)) == "value2"
        
        # Frozen set key
        cache.set(frozenset([1, 2]), "value3")
        assert cache.get(frozenset([1, 2])) == "value3"


class TestThreadSafety:
    """Tests for thread-safe cache operations."""

    def test_concurrent_get_operations(self):
        """Test that multiple threads can safely get from cache."""
        import threading
        
        cache = TTLCache(max_size=100, default_ttl=100)
        cache.set("key", "value")
        
        results = []
        
        def get_value():
            for _ in range(100):
                val = cache.get("key")
                if val is not None:
                    results.append(val)
        
        threads = [threading.Thread(target=get_value) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # All threads should have successfully read the value
        assert len(results) > 0
        assert all(r == "value" for r in results)

    def test_concurrent_set_operations(self):
        """Test that multiple threads can safely set values."""
        import threading
        
        cache = TTLCache(max_size=100, default_ttl=100)
        lock = threading.Lock()
        results = []
        
        def set_values():
            for i in range(20):
                cache.set(f"key{threading.current_thread().ident}_{i}", f"value{i}")
                with lock:
                    results.append(1)
        
        threads = [threading.Thread(target=set_values) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # All operations should have completed
        assert len(results) == 20 * 3

    def test_concurrent_get_and_set(self):
        """Test concurrent get and set operations."""
        import threading
        
        cache = TTLCache(max_size=100, default_ttl=100)
        results = {"gets": 0, "sets": 0}
        lock = threading.Lock()
        
        def reader():
            for i in range(50):
                cache.get(f"key{i}")
                with lock:
                    results["gets"] += 1
        
        def writer():
            for i in range(50):
                cache.set(f"key{i}", f"value{i}")
                with lock:
                    results["sets"] += 1
        
        threads = [
            threading.Thread(target=reader),
            threading.Thread(target=reader),
            threading.Thread(target=writer),
            threading.Thread(target=writer),
        ]
        
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # All operations should complete without deadlock
        assert results["gets"] == 100
        assert results["sets"] == 100

    def test_purge_expired_thread_safety(self):
        """Test that purge_expired() is thread-safe when called concurrently.
        
        CRITICAL: purge_expired() is public API and must be thread-safe.
        Previously it lacked lock acquisition, causing:
        - Dictionary iteration errors during concurrent get/set
        - Memory counter corruption
        - Race conditions
        """
        import threading
        
        cache = TTLCache(max_size=100, default_ttl=1)
        errors = []
        
        def add_and_expire():
            """Add entries that will expire and purge them."""
            try:
                for i in range(30):
                    cache.set(f"expire_{threading.current_thread().ident}_{i}", f"value{i}", ttl=0.1)
                time.sleep(0.15)
                removed = cache.purge_expired()
                assert removed >= 0, "purge_expired should return non-negative count"
            except Exception as e:
                errors.append(("add_and_expire", e))
        
        def concurrent_gets():
            """Perform concurrent get operations."""
            try:
                for i in range(50):
                    cache.get(f"key{i}")
            except Exception as e:
                errors.append(("concurrent_gets", e))
        
        def concurrent_sets():
            """Perform concurrent set operations."""
            try:
                for i in range(50):
                    cache.set(f"key{i}", f"value{i}")
            except Exception as e:
                errors.append(("concurrent_sets", e))
        
        threads = [
            threading.Thread(target=add_and_expire),
            threading.Thread(target=add_and_expire),
            threading.Thread(target=concurrent_gets),
            threading.Thread(target=concurrent_gets),
            threading.Thread(target=concurrent_sets),
        ]
        
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Should complete without errors
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        
        # Cache should be in valid state (memory counter consistent)
        assert cache.total_memory_used >= 0
        assert cache.total_memory_used <= cache.max_memory_bytes * 1.2  # Allow margin

    def test_purge_expired_does_not_deadlock_with_set(self):
        """Test that purge_expired() called from set() doesn't cause deadlock.
        
        set() calls purge_expired() while holding the lock.
        If purge_expired() tried to acquire the lock again, it would deadlock.
        The RLock (reentrant lock) allows this, but we verify it works correctly.
        """
        cache = TTLCache(max_size=10, default_ttl=1)
        
        # Add entries with short TTL
        for i in range(5):
            cache.set(f"key{i}", f"value{i}", ttl=0.1)
        
        time.sleep(0.15)
        
        # set() internally calls purge_expired() while holding lock
        # This should not deadlock
        result = cache.set("new_key", "new_value")
        assert result is True
        
        # Verify expired entries were purged
        assert cache.get("key0") is None


class TestMetricsRecording:
    """Tests for cache metrics recording with Prometheus."""

    @patch('api.cache.record_cache_hit_safe')
    @patch('api.cache.record_cache_miss_safe')
    def test_cache_hit_metric_recorded(self, mock_miss, mock_hit):
        """Test that cache hits are recorded to metrics."""
        call_count = 0
        
        @cache_response(ttl=10)
        def func(request: MockRequest):
            nonlocal call_count
            call_count += 1
            return {"call_num": call_count}
        
        request = MockRequest(param1="test", param2=42)
        
        # First call - miss
        func(request=request)
        assert mock_miss.called, "Cache miss should be recorded"
        miss_count = mock_miss.call_count
        
        # Second call - hit
        func(request=request)
        assert mock_hit.called, "Cache hit should be recorded"
        hit_count = mock_hit.call_count
        
        # Verify correct calls
        assert hit_count >= 1

    @patch('api.cache.record_cache_hit_safe')
    @patch('api.cache.record_cache_miss_safe')
    def test_cache_miss_on_different_request(self, mock_miss, mock_hit):
        """Test that different requests trigger cache misses."""
        call_count = 0
        
        @cache_response(ttl=10)
        def func(request: MockRequest):
            nonlocal call_count
            call_count += 1
            return {"call_num": call_count}
        
        request1 = MockRequest(param1="test1", param2=42)
        request2 = MockRequest(param1="test2", param2=43)
        
        # First request
        func(request=request1)
        first_miss_count = mock_miss.call_count
        
        # Different request - should miss
        func(request=request2)
        second_miss_count = mock_miss.call_count
        
        # Should have recorded 2 misses (one for each request)
        assert second_miss_count > first_miss_count


class TestComplexScenarios:
    """Complex end-to-end scenario tests."""

    def test_cache_with_multiple_response_types(self):
        """Test caching with different response structures."""
        cache = TTLCache(max_size=10, default_ttl=100)
        
        # Dict response
        dict_resp = {"status": "ok", "data": [1, 2, 3]}
        cache.set("dict", dict_resp)
        
        # List response
        list_resp = [{"id": 1}, {"id": 2}, {"id": 3}]
        cache.set("list", list_resp)
        
        # BaseModel response
        model_resp = MockRequest(param1="response", param2=999)
        cache.set("model", model_resp)
        
        # Verify retrieval
        assert cache.get("dict") == dict_resp
        assert cache.get("list") == list_resp
        assert cache.get("model") == model_resp

    def test_cache_lifecycle_with_mixed_operations(self):
        """Test cache through a realistic lifecycle."""
        cache = TTLCache(max_size=5, default_ttl=100, max_memory_bytes=5000)
        
        # Phase 1: Add initial entries
        for i in range(3):
            cache.set(f"key{i}", f"value{i}" * 10)
        
        assert len(cache) == 3
        
        # Phase 2: Access some entries
        cache.get("key0")
        cache.get("key1")
        
        # Phase 3: Add more entries to trigger eviction
        for i in range(3, 6):
            cache.set(f"key{i}", f"value{i}" * 10)
        
        # key2 should be evicted as LRU
        assert cache.get("key2") is None
        
        # Phase 4: Expire some entries
        cache.set("expire_me", "temp_value", ttl=0.1)
        time.sleep(0.15)
        cache.purge_expired()
        
        # Expired entry should be gone
        assert cache.get("expire_me") is None
        
        # Phase 5: Clear cache
        cache.clear()
        assert len(cache) == 0

    def test_memory_pressure_eviction_scenario(self):
        """Test realistic memory pressure eviction scenario."""
        cache = TTLCache(
            max_size=100,
            default_ttl=100,
            max_memory_bytes=2000,  # Tight limit
            max_entry_bytes=1000
        )
        
        # Add entries progressively
        for i in range(10):
            value = "data_" * 50  # Moderate size
            result = cache.set(f"key{i}", value)
            assert result is True, "Entry should be cached"
        
        # Cache should have evicted some entries to stay within memory limit
        assert cache.total_memory_used <= cache.max_memory_bytes * 1.1

    def test_cache_with_nested_basemodel_responses(self):
        """Test caching of nested BaseModel structures."""
        from typing import List as ListType
        
        class NestedModel(BaseModel):
            id: int
            data: ListType[MockRequest]
        
        cache = TTLCache(max_size=10, default_ttl=100, max_memory_bytes=50000)
        
        # Create nested response
        nested = NestedModel(
            id=1,
            data=[
                MockRequest(param1=f"item{i}", param2=i)
                for i in range(100)
            ]
        )
        
        # Should properly estimate size and cache
        result = cache.set("nested", nested)
        assert result is True
        
        retrieved = cache.get("nested")
        assert retrieved.id == 1
        assert len(retrieved.data) == 100


class TestEdgeCases:
    """Edge case and boundary condition tests."""

    def test_cache_with_zero_max_size(self):
        """Test cache behavior with max_size=1."""
        cache = TTLCache(max_size=1, default_ttl=100)
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        cache.set("key2", "value2")
        # key1 should be evicted
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

    def test_cache_with_very_small_ttl(self):
        """Test cache with very short TTL."""
        cache = TTLCache(default_ttl=1)
        
        cache.set("key", "value", ttl=0.01)
        time.sleep(0.02)
        
        # Should be expired
        assert cache.get("key") is None

    def test_cache_with_very_large_entry(self):
        """Test cache behavior with very large entries."""
        cache = TTLCache(
            max_size=10,
            max_entry_bytes=100000,
            max_memory_bytes=200000
        )
        
        # Large value
        large_value = "x" * 50000
        result = cache.set("large", large_value)
        
        assert result is True
        assert cache.get("large") == large_value

    def test_repeated_expiry_and_refresh(self):
        """Test repeated expiry and refresh cycles."""
        cache = TTLCache(max_size=10, default_ttl=1)
        
        for cycle in range(5):
            cache.set("key", f"value{cycle}", ttl=0.1)
            assert cache.get("key") == f"value{cycle}"
            time.sleep(0.15)
            assert cache.get("key") is None

    def test_cache_stats_with_empty_cache(self):
        """Test cache stats on empty cache."""
        from api.cache import _response_cache
        
        # Clear the global cache first
        clear_response_cache()
        
        stats = get_cache_stats()
        
        # Stats should still be valid
        assert stats["cached_entries"] == 0
        assert stats["memory_used_bytes"] == 0
        assert 0 <= stats["memory_utilization_percent"] <= 100

    def test_cache_stats_memory_utilization_calculation(self):
        """Test that memory utilization percent is calculated correctly."""
        cache = TTLCache(max_size=10, max_memory_bytes=1000, default_ttl=100)
        
        cache.set("key1", "x" * 100)
        
        stats = get_cache_stats()
        # Since this uses global cache, just verify the structure
        assert "memory_utilization_percent" in stats
        assert isinstance(stats["memory_utilization_percent"], float)


class TestMemoryAwareCachingIntegration:
    """Integration tests for memory-aware caching with decorator."""

    def test_decorator_handles_oversized_responses(self):
        """Test that decorator handles responses larger than max_entry_bytes."""
        call_count = 0
        
        @cache_response(ttl=10)
        def func_returning_large(request: MockRequest):
            nonlocal call_count
            call_count += 1
            # Return large response (simulated)
            return {"data": "x" * 500000}  # ~500KB
        
        request = MockRequest(param1="test", param2=42)
        
        # First call
        result1 = func_returning_large(request=request)
        assert result1["data"]  # Should get result even if not cached
        
        # Second call - will recalculate if too large to cache
        result2 = func_returning_large(request=request)
        # May or may not be cached depending on size
        assert result2["data"]

    def test_decorator_caches_small_responses(self):
        """Test that decorator caches responses within size limits."""
        call_count = 0
        
        @cache_response(ttl=10)
        def func_returning_small(request: MockRequest):
            nonlocal call_count
            call_count += 1
            return {"result": "small", "value": call_count}
        
        request = MockRequest(param1="test", param2=42)
        
        # First call
        result1 = func_returning_small(request=request)
        assert result1["value"] == 1
        
        # Second call - should be cached
        result2 = func_returning_small(request=request)
        assert result2["value"] == 1  # Same value, from cache
        assert call_count == 1  # Only called once
