"""Subprocess-only application: production routes/middleware, deterministic service work.

Run with ``python -m uvicorn runtime_app:app --app-dir tests --no-proxy-headers``.
Never mount these control routes in the deployed application.
"""

import os
import threading
import time

from fastapi import HTTPException, Response

import api.cache as cache_module
import api.main as main
import api.routes.events as events
from api.metrics import record_cache_lifecycle_safe


app = main.app
gate = threading.Event()
lock = threading.Lock()
state = {"contact_started": 0, "contact_finished": 0, "stream_finished": 0}
blocked = os.environ.get("TEST_RUNTIME_BLOCK_CONTACT") == "true"
budget = float(os.environ.get("TEST_RUNTIME_BUDGET", "10"))
cache_module._response_cache = cache_module.TTLCache(  # pylint: disable=protected-access
    max_size=int(os.environ.get("TEST_RUNTIME_CACHE_SIZE", "256")),
    observer=record_cache_lifecycle_safe,
)
original_timeout = main.calculate_adaptive_timeout
main.calculate_adaptive_timeout = lambda endpoint: (
    budget if endpoint in (
        "/api/v1/astronomical-events/contact-times",
        "/api/v1/astronomical-events-stream",
    ) else original_timeout(endpoint)
)


def contact_times(**_kwargs):
    """Block inside the worker thread, not in an async imitation of a sync route."""
    with lock:
        state["contact_started"] += 1
    if blocked and not gate.wait(15):
        raise RuntimeError("Test did not release contact computation")
    delay = float(os.environ.get("TEST_RUNTIME_DELAY", "0"))
    if _kwargs.get("event_date_iso", "").endswith(":59.000"):
        delay = float(os.environ.get("TEST_RUNTIME_SLOW_DELAY", str(delay)))
    time.sleep(delay)
    with lock:
        state["contact_finished"] += 1
    return {"eclipse_begins": "2026-08-12 01:15:00.000"}


def event_results(**_kwargs):
    """Keep rate-limit tests independent of ephemeris runtime."""
    return {
        "events": [],
        "pagination": {"page": 1, "page_size": 10, "total_events": 0, "total_pages": 0},
    }


def event_stream(**_kwargs):
    """Exercise the real sync streaming route, including cancellation shielding."""
    try:
        yield {"page": 1, "events": []}
        if os.environ.get("TEST_RUNTIME_BLOCK_STREAM") == "true" and not gate.wait(15):
            raise RuntimeError("Test did not release stream computation")
        yield {"total_events": 0, "total_pages": 0}
    finally:
        with lock:
            state["stream_finished"] += 1


events.get_contact_times_for_event = contact_times
events.get_astronomical_events = event_results
events.stream_astronomical_events = event_stream


@app.get("/__test/state")
def snapshot():
    """Expose synchronization evidence without triggering cache expiry."""
    with lock:
        return dict(state)


@app.post("/__test/release")
def release():
    gate.set()
    return {"released": True}


@app.post("/__test/clear")
def clear():
    cache_module.clear_response_cache()
    return {"cleared": True}


@app.get("/__test/status/{status}")
def result(status: int):
    if status == 500:
        raise HTTPException(500, "Handled test failure")
    return Response(status_code=status)


@app.get("/__test/broken")
def broken():
    raise RuntimeError("Intentional runtime test failure")
