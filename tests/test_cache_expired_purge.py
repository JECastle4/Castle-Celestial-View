"""
Tests for cache.py fixes - verifying expired entry purging before LRU eviction.
"""

import time
import pytest
from api.cache import TTLCache


class TestCachePurgeExpiredBeforeLRUEviction:
    """Test that expired entries are purged before LRU eviction."""
    
    def test_purge_expired_removes_expired_entries(self):
        """Test that purge_expired() removes all expired entries."""
        cache = TTLCache(max_size=10, default_ttl=1)
        
        # Add entries
        cache.set("key1", "value1", ttl=1)
        cache.set("key2", "value2", ttl=10)
        
        # Wait for first entry to expire
        time.sleep(1.1)
        
        # Purge expired
        removed = cache.purge_expired()
        
        assert removed == 1, "Should remove 1 expired entry"
        assert "key1" not in cache.cache, "Expired key should be removed"
        assert "key2" in cache.cache, "Non-expired key should remain"
    
    def test_purge_expired_returns_count(self):
        """Test that purge_expired() returns count of removed entries."""
        cache = TTLCache(max_size=10, default_ttl=1)
        
        # Add multiple expiring entries
        for i in range(5):
            cache.set(f"key{i}", f"value{i}", ttl=1)
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Purge
        removed = cache.purge_expired()
        
        assert removed == 5, "Should return count of removed entries"
        assert len(cache.cache) == 0, "All entries should be removed"
    
    def test_set_purges_expired_before_eviction(self):
        """Test that set() purges expired entries before LRU eviction.
        
        Scenario:
        1. Fill cache with 5 entries
        2. Let some entries expire
        3. Add new entry when cache is at max_size
        4. Verify expired entries are purged first (before LRU eviction)
        5. Verify LRU entry is NOT evicted if space freed by purge
        """
        # Small cache for testing
        cache = TTLCache(max_size=5, default_ttl=1)
        
        # Fill cache with 5 entries
        cache.set("key1", "value1", ttl=1)  # Will expire
        cache.set("key2", "value2", ttl=1)  # Will expire
        cache.set("key3", "value3", ttl=1)  # Will expire
        cache.set("key4", "value4", ttl=1)  # Will expire
        cache.set("key5", "value5", ttl=100)  # Won't expire (LRU candidate)
        
        # Access key1-4 to make key5 the LRU entry (least recently used)
        for key in ["key1", "key2", "key3", "key4"]:
            _ = cache.get(key)
        
        # Wait for first 4 entries to expire
        time.sleep(1.1)
        
        # Add new entry when cache is full
        # Without purge: LRU eviction would remove key5
        # With purge: Expired entries are removed first, key5 is preserved
        cache.set("key6", "value6", ttl=100)
        
        # Verify: key5 should still be in cache (not evicted by LRU)
        # The 4 expired entries were purged, creating space
        assert "key5" in cache.cache, "LRU entry should NOT be evicted if purge frees space"
        assert "key6" in cache.cache, "New entry should be added"
        
        # Verify: expired entries are gone
        assert "key1" not in cache.cache, "Expired entries should be removed"
        assert "key2" not in cache.cache, "Expired entries should be removed"
        assert "key3" not in cache.cache, "Expired entries should be removed"
        assert "key4" not in cache.cache, "Expired entries should be removed"
    
    def test_set_still_evicts_lru_if_no_expired_entries(self):
        """Test that set() still evicts LRU entries if no expired entries exist."""
        cache = TTLCache(max_size=3, default_ttl=100)
        
        # Fill cache with non-expiring entries
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Access key2 and key3 to make key1 the LRU entry
        _ = cache.get("key2")
        _ = cache.get("key3")
        
        # Add new entry - should evict key1 (LRU)
        cache.set("key4", "value4")
        
        # Verify: key1 was evicted
        assert "key1" not in cache.cache, "LRU entry should be evicted"
        assert "key2" in cache.cache, "Non-LRU entries should remain"
        assert "key3" in cache.cache, "Non-LRU entries should remain"
        assert "key4" in cache.cache, "New entry should be added"
    
    def test_purge_frees_memory_correctly(self):
        """Test that purging expired entries frees memory correctly."""
        cache = TTLCache(max_size=10, default_ttl=1)
        
        # Add entry with known size
        large_value = "x" * 1000
        cache.set("key1", large_value, ttl=1)
        initial_memory = cache.total_memory_used
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Purge
        cache.purge_expired()
        
        # Memory should be freed
        assert cache.total_memory_used < initial_memory, "Memory should be freed after purge"
        assert cache.total_memory_used == 0, "Cache should be empty"
    
    def test_purge_does_not_remove_non_expired_entries(self):
        """Test that purge only removes expired entries, not non-expired ones."""
        cache = TTLCache(max_size=10, default_ttl=100)
        
        # Mix of entries with different TTLs
        cache.set("key1", "value1", ttl=1)    # Will expire
        cache.set("key2", "value2", ttl=10)   # Won't expire
        cache.set("key3", "value3", ttl=100)  # Won't expire
        
        # Wait for first to expire
        time.sleep(1.1)
        
        # Purge
        removed = cache.purge_expired()
        
        assert removed == 1, "Should only remove 1 expired entry"
        assert "key1" not in cache.cache, "Expired entry should be removed"
        assert "key2" in cache.cache, "Non-expired entry should remain"
        assert "key3" in cache.cache, "Non-expired entry should remain"
    
    def test_empty_cache_purge_is_safe(self):
        """Test that purge on empty cache doesn't cause errors."""
        cache = TTLCache(max_size=10, default_ttl=100)
        
        # Purge empty cache
        removed = cache.purge_expired()
        
        assert removed == 0, "Should return 0 for empty cache"
        assert len(cache.cache) == 0, "Cache should remain empty"
    
    def test_purge_expired_handles_partial_expiry(self):
        """Test purging when only some entries have expired."""
        cache = TTLCache(max_size=10, default_ttl=1)
        
        # Add entries with different expiry times
        cache.set("key1", "value1", ttl=1)     # Will expire soon
        cache.set("key2", "value2", ttl=1)     # Will expire soon
        time.sleep(0.5)
        cache.set("key3", "value3", ttl=100)   # Won't expire soon
        cache.set("key4", "value4", ttl=100)   # Won't expire soon
        
        # Wait for first 2 to expire
        time.sleep(0.6)
        
        # Purge - should only remove first 2
        removed = cache.purge_expired()
        
        assert removed == 2, "Should remove only expired entries"
        assert len(cache.cache) == 2, "Non-expired entries should remain"
        assert cache.cache.get("key3") == "value3"
        assert cache.cache.get("key4") == "value4"
