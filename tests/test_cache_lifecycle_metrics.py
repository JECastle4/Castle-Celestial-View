"""Response cache lifecycle accounting and real Prometheus recording."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial

import pytest
from prometheus_client import CollectorRegistry
from pydantic import BaseModel

from api import cache as cache_module
from api import metrics as metrics_module
from api.cache import TTLCache, cache_response


@pytest.fixture
def observed_cache(monkeypatch):
    """Use deterministic retained sizes and capture every endpoint update."""
    events = []
    cache = TTLCache(observer=lambda *event: events.append(event))
    monkeypatch.setattr(cache, "_estimate_size", len)
    return cache, events


def test_insert_replace_clear_and_generic_caches(observed_cache):
    cache, events = observed_cache
    cache.set("a1", "abc", endpoint="endpoint_a")
    cache.set("a2", "12345", endpoint="endpoint_a")
    cache.set("b1", "xy", endpoint="endpoint_b")
    cache.set("a1", "replacement", endpoint="endpoint_a")
    assert events == [
        ("set", "endpoint_a", 3, 1),
        ("set", "endpoint_a", 8, 2),
        ("set", "endpoint_b", 2, 1),
        ("replacement", "endpoint_a", 5, 1),
        ("set", "endpoint_a", 16, 2),
    ]
    assert cache.total_memory_used == 18
    cache.clear()
    assert events[-2:] == [
        ("clear", "endpoint_a", 0, 0), ("clear", "endpoint_b", 0, 0),
    ]
    cache.clear()
    assert events[-2:] == [
        ("clear", "endpoint_a", 0, 0), ("clear", "endpoint_b", 0, 0),
    ]
    generic = TTLCache()
    generic.set(("arbitrary", "request"), "value", endpoint="ignored")
    assert not generic._entry_endpoints
    assert not generic._endpoint_usage


@pytest.mark.parametrize("limit", ["entries", "memory"])
def test_lru_eviction_is_attributed_to_victim(observed_cache, limit):
    cache, events = observed_cache
    if limit == "entries":
        cache.max_size = 2
    else:
        cache.max_memory_bytes = 6
    cache.set("a", "aaa", endpoint="endpoint_a")
    cache.set("b", "bbb", endpoint="endpoint_b")
    cache.get("a")
    cache.set("c", "ccc", endpoint="endpoint_a")
    assert events[-2:] == [
        ("eviction", "endpoint_b", 0, 0), ("set", "endpoint_a", 6, 2),
    ]
    assert cache.total_memory_used == 6
    cache.clear()
    assert events[-2:] == [
        ("clear", "endpoint_a", 0, 0), ("clear", "endpoint_b", 0, 0),
    ]


@pytest.mark.parametrize("operation", ["get", "purge", "len", "set"])
def test_expiration_is_counted_only_at_removal(observed_cache, monkeypatch, operation):
    cache, events = observed_cache
    monkeypatch.setattr(cache_module.time, "time", lambda: 100)
    cache.set("expired", "abc", ttl=5, endpoint="endpoint_a")
    cache.set("live", "12345", ttl=50, endpoint="endpoint_b")
    monkeypatch.setattr(cache_module.time, "time", lambda: 105)
    assert len(events) == 2
    if operation == "get":
        assert cache.get("expired") is None
    elif operation == "purge":
        assert cache.purge_expired() == 1
    elif operation == "len":
        assert len(cache) == 1
    else:
        cache.max_size = 2
        cache.set("new", "xy", endpoint="endpoint_b")
    assert ("expiration", "endpoint_a", 0, 0) in events
    assert sum(event[0] == "expiration" for event in events) == 1
    assert not any(event[0] == "eviction" for event in events)
    assert cache.total_memory_used == (7 if operation == "set" else 5)
    cache.get("expired")
    cache.purge_expired()
    len(cache)
    assert sum(event[0] == "expiration" for event in events) == 1


def test_replacement_is_not_expiration_even_after_ttl(observed_cache, monkeypatch):
    cache, events = observed_cache
    monkeypatch.setattr(cache_module.time, "time", lambda: 100)
    cache.set("a", "abc", ttl=0, endpoint="endpoint_a")
    cache.set("a", "12345", endpoint="endpoint_a")
    assert events == [
        ("set", "endpoint_a", 3, 1),
        ("replacement", "endpoint_a", 0, 0),
        ("set", "endpoint_a", 5, 1),
    ]


def test_oversized_replacement_leaves_state_and_metrics_unchanged(observed_cache):
    cache, events = observed_cache
    cache.max_entry_bytes = 3
    cache.set("a", "abc", ttl=0, endpoint="endpoint_a")
    snapshot = list(events)
    assert not cache.set("a", "too large", endpoint="endpoint_b")
    assert not cache.set("new", "too large", endpoint="unrecorded")
    assert events == snapshot
    assert cache.cache["a"] == "abc"
    assert cache.total_memory_used == 3
    assert cache._endpoint_usage == {"endpoint_a": [3, 1]}


def test_concurrent_lifecycle_observers_see_consistent_endpoint_state():
    updates = []

    def observe(event, endpoint, size, count):
        keys = [key for key, label in cache._entry_endpoints.items() if label == endpoint]
        assert size == sum(cache.entry_sizes[key] for key in keys)
        assert count == len(keys)
        assert size >= 0
        updates.append((event, endpoint, size, count))

    cache = TTLCache(max_size=3, observer=observe)

    def worker(worker_id):
        endpoint = f"endpoint_{worker_id % 2}"
        for index in range(100):
            key = (worker_id, index % 5)
            cache.set(key, "value", ttl=0 if index % 3 == 0 else 300, endpoint=endpoint)
            cache.get(key)
            if index % 7 == 0:
                cache.purge_expired()
                len(cache)
            if index % 19 == 0:
                cache.clear()

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(worker, range(8)))
    assert updates
    cache.clear()
    assert cache.total_memory_used == 0
    assert cache._endpoint_usage == {"endpoint_0": [0, 0], "endpoint_1": [0, 0]}
    assert {event[0] for event in updates} >= {"set", "clear", "expiration", "eviction"}


@pytest.fixture
def real_metrics(monkeypatch):
    """Bypass pytest's safe-helper no-op and isolate real Prometheus collectors."""
    registry = CollectorRegistry()
    for metric_type in ("Counter", "Gauge", "Histogram"):
        constructor = getattr(metrics_module, metric_type)
        monkeypatch.setattr(metrics_module, metric_type, partial(constructor, registry=registry))
    monkeypatch.setattr(metrics_module.MetricsCollector, "_instance", None)
    monkeypatch.setattr(metrics_module.MetricsCollector, "_initialized", False)
    monkeypatch.setattr(metrics_module, "_METRICS_INSTANCE", None)
    monkeypatch.setattr(metrics_module, "_is_test_mode", lambda: False)
    return registry


def test_real_prometheus_lifecycle_values(real_metrics, monkeypatch):
    cache = TTLCache(max_size=2, observer=metrics_module.record_cache_lifecycle_safe)
    monkeypatch.setattr(cache, "_estimate_size", len)

    def sample(name, endpoint):
        return real_metrics.get_sample_value(name, {"endpoint": endpoint}) or 0

    cache.set("a", "abc", endpoint="endpoint_a")
    cache.set("b", "12345", endpoint="endpoint_b")
    assert sample("cache_memory_bytes", "endpoint_a") == 3
    assert sample("cache_memory_bytes", "endpoint_b") == 5
    cache.set("b", "xy", endpoint="endpoint_b")
    assert sample("cache_memory_bytes", "endpoint_b") == 2
    assert sample("cache_entry_count", "endpoint_b") == 1
    assert sample("cache_evictions_total", "endpoint_b") == 0
    assert sample("cache_expirations_total", "endpoint_b") == 0
    cache.set("c", "1234", ttl=0, endpoint="endpoint_b")
    assert sample("cache_evictions_total", "endpoint_a") == 1
    assert sample("cache_evictions_total", "endpoint_b") == 0
    assert sample("cache_expirations_total", "endpoint_b") == 0
    assert sample("cache_memory_bytes", "endpoint_a") == 0
    assert sample("cache_memory_bytes", "endpoint_b") == 6
    assert sample("cache_entry_count", "endpoint_b") == 2
    cache.get("c")
    assert sample("cache_expirations_total", "endpoint_b") == 1
    assert sample("cache_memory_bytes", "endpoint_b") == 2
    assert sample("cache_entry_count", "endpoint_b") == 1
    cache.clear()
    for endpoint in ("endpoint_a", "endpoint_b"):
        assert sample("cache_memory_bytes", endpoint) == 0
        assert sample("cache_entry_count", endpoint) == 0
    assert sample("cache_evictions_total", "endpoint_a") == 1
    assert sample("cache_expirations_total", "endpoint_b") == 1


def test_real_decorator_metrics_use_only_function_names(real_metrics, monkeypatch):
    cache = TTLCache(observer=metrics_module.record_cache_lifecycle_safe)
    monkeypatch.setattr(cache_module, "_response_cache", cache)

    class Request(BaseModel):
        value: str

    @cache_response()
    def sync_endpoint(request):
        return request.value

    @cache_response()
    async def async_endpoint(request):
        return request.value

    for value in ("private-location-1", "private-location-2"):
        request = Request(value=value)
        sync_endpoint(request)
        sync_endpoint(request)
        asyncio.run(async_endpoint(request))
        asyncio.run(async_endpoint(request))
    # Arbitrary keys are not interpreted as labels, even on the response cache.
    cache.set(("untrusted-endpoint", "private-request"), "unlabeled")
    for endpoint in ("sync_endpoint", "async_endpoint"):
        assert real_metrics.get_sample_value("cache_hits_total", {"endpoint": endpoint}) == 2
        assert real_metrics.get_sample_value("cache_misses_total", {"endpoint": endpoint}) == 2
        assert real_metrics.get_sample_value("cache_entry_count", {"endpoint": endpoint}) == 2
        expected_size = sum(
            cache.entry_sizes[key] for key, label in cache._entry_endpoints.items()
            if label == endpoint
        )
        assert real_metrics.get_sample_value(
            "cache_memory_bytes", {"endpoint": endpoint},
        ) == expected_size
    endpoints = {
        sample.labels["endpoint"]
        for metric in real_metrics.collect()
        for sample in metric.samples if "endpoint" in sample.labels
    }
    assert endpoints == {"sync_endpoint", "async_endpoint"}
