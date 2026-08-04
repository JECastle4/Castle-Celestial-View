"""
Tests for astronomical events detection (new/full moons + eclipse classification).

The expected eclipse types below were validated against Wikipedia's published
eclipse records for 2025-2026 during implementation.
"""
import json
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.services.astronomical_events import get_astronomical_events, stream_astronomical_events

client = TestClient(app)

# (date, event_type, expected eclipse_type)
KNOWN_ECLIPSES = [
    ("2025-09-07", "Full Moon", "Total"),
    ("2025-09-21", "New Moon", "Partial"),
    ("2026-02-17", "New Moon", "Annular"),
    ("2026-03-03", "Full Moon", "Total"),
    ("2026-08-12", "New Moon", "Total"),
    ("2026-08-28", "Full Moon", "Partial"),
]

# Full ~13-month window containing all 6 known eclipses above. This is by far
# the most expensive range to compute (dozens of eclipse-candidate events), so
# it is only used by the couple of tests below that genuinely need it, and is
# computed once via a module-scoped fixture rather than per-test.
FULL_RANGE_START = "2025-08-01"
FULL_RANGE_END = "2026-09-01"

# Small ~5-week window with exactly 3 events (1 non-eclipse, 2 known eclipses)
# used by tests that just need "a couple of real events", not the full window.
NARROW_RANGE_START = "2025-08-20"
NARROW_RANGE_END = "2025-09-25"


@pytest.fixture(scope="module")
def full_range_result():
    """The expensive full-range computation, shared across tests that need it."""
    return get_astronomical_events(
        start_date_str=FULL_RANGE_START,
        end_date_str=FULL_RANGE_END,
        page=1,
        page_size=100,
        include_contact_times=False,
    )


def test_service_finds_known_eclipses(full_range_result):
    """Service-level: all 6 known 2025-2026 eclipses are found and classified correctly."""
    events_by_date = {e["date"][:10]: e for e in full_range_result["events"]}

    for date_str, event_type, expected_type in KNOWN_ECLIPSES:
        assert date_str in events_by_date, f"Missing event on {date_str}"
        event = events_by_date[date_str]
        assert event["event_type"] == event_type
        assert event["eclipse_type"] == expected_type
        assert event["eclipse_occurs"] is True
        assert event["greatest_eclipse_time"] is not None


def test_service_non_eclipse_events_marked_none(full_range_result):
    """Non-eclipse new/full moons should classify as No Eclipse with eclipse_occurs False."""
    known_dates = {d for d, _, _ in KNOWN_ECLIPSES}
    non_eclipse_events = [e for e in full_range_result["events"] if e["date"][:10] not in known_dates]
    assert len(non_eclipse_events) > 0
    for event in non_eclipse_events:
        assert event["eclipse_type"] == "No Eclipse"
        assert event["eclipse_occurs"] is False


def test_service_pagination():
    """Pagination math should be consistent with total_events."""
    result = get_astronomical_events(
        start_date_str=NARROW_RANGE_START,
        end_date_str=NARROW_RANGE_END,
        page=1,
        page_size=2,
        include_contact_times=False,
    )
    assert len(result["events"]) == 2
    assert result["pagination"]["page"] == 1
    assert result["pagination"]["page_size"] == 2
    assert result["pagination"]["total_events"] == 3
    assert result["pagination"]["total_pages"] == 2


def test_service_event_type_filter():
    """Filtering by event_types should only return the requested phase."""
    result = get_astronomical_events(
        start_date_str=NARROW_RANGE_START,
        end_date_str=NARROW_RANGE_END,
        page=1,
        page_size=100,
        event_types=["full_moon"],
        include_contact_times=False,
    )
    assert len(result["events"]) > 0
    assert all(e["event_type"] == "Full Moon" for e in result["events"])


def test_service_invalid_date_range_raises():
    """End date before start date should raise ValueError."""
    with pytest.raises(ValueError):
        get_astronomical_events(
            start_date_str="2026-01-01",
            end_date_str="2025-01-01",
        )


def test_service_contact_times_included_for_eclipses():
    """Eclipse events should include contact_times when requested."""
    result = get_astronomical_events(
        start_date_str="2025-09-01",
        end_date_str="2025-09-10",
        page=1,
        page_size=10,
        include_contact_times=True,
    )
    eclipse_events = [e for e in result["events"] if e["eclipse_occurs"]]
    assert len(eclipse_events) == 1
    assert eclipse_events[0]["contact_times"] is not None


def test_route_basic_request():
    """Route-level: basic request returns 200 and matches known eclipse."""
    resp = client.post("/api/v1/astronomical-events", json={
        "start_date": "2025-09-01",
        "end_date": "2025-09-10",
        "include_contact_times": False,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["pagination"]["total_events"] == 1
    assert data["events"][0]["eclipse_type"] == "Total"
    assert data["events"][0]["event_type"] == "Full Moon"


def test_route_invalid_date_format_returns_422():
    """Malformed date strings should fail Pydantic pattern validation (422)."""
    resp = client.post("/api/v1/astronomical-events", json={
        "start_date": "not-a-date",
        "end_date": "2025-09-10",
    })
    assert resp.status_code == 422


def test_route_end_before_start_returns_422():
    """End date before start date is caught by Pydantic model_validator -> 422."""
    resp = client.post("/api/v1/astronomical-events", json={
        "start_date": "2026-01-01",
        "end_date": "2025-01-01",
    })
    assert resp.status_code == 422


def test_route_invalid_event_type_returns_422():
    """Unsupported event_types entries should fail validation."""
    resp = client.post("/api/v1/astronomical-events", json={
        "start_date": NARROW_RANGE_START,
        "end_date": NARROW_RANGE_END,
        "event_types": ["eclipse"],
    })
    assert resp.status_code == 422


def test_route_pagination_params():
    """Custom page/page_size should be honored end-to-end."""
    resp = client.post("/api/v1/astronomical-events", json={
        "start_date": NARROW_RANGE_START,
        "end_date": NARROW_RANGE_END,
        "page": 2,
        "page_size": 2,
        "include_contact_times": False,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["events"]) == 1
    assert data["pagination"]["page"] == 2


def test_service_stream_matches_get_events_first_page():
    """stream_astronomical_events should yield the same first page as get_astronomical_events."""
    paginated = get_astronomical_events(
        start_date_str=NARROW_RANGE_START,
        end_date_str=NARROW_RANGE_END,
        page=1,
        page_size=2,
        include_contact_times=False,
    )
    items = list(stream_astronomical_events(
        start_date_str=NARROW_RANGE_START,
        end_date_str=NARROW_RANGE_END,
        page_size=2,
        include_contact_times=False,
    ))
    page_items = [item for item in items if 'events' in item]
    metadata_items = [item for item in items if 'events' not in item]

    assert page_items[0]['page'] == 1
    assert page_items[0]['events'] == paginated['events']
    assert len(metadata_items) == 1
    assert metadata_items[0]['total_events'] == paginated['pagination']['total_events']
    assert metadata_items[0]['total_pages'] == paginated['pagination']['total_pages']
    assert metadata_items[0]['page_size'] == 2


def test_service_stream_yields_all_pages_in_order():
    """Every raw event should appear exactly once, across pages, in page order."""
    items = list(stream_astronomical_events(
        start_date_str=NARROW_RANGE_START,
        end_date_str=NARROW_RANGE_END,
        page_size=1,
        include_contact_times=False,
    ))
    page_items = [item for item in items if 'events' in item]
    metadata = next(item for item in items if 'events' not in item)

    assert [p['page'] for p in page_items] == list(range(1, metadata['total_pages'] + 1))
    all_events = [e for p in page_items for e in p['events']]
    assert len(all_events) == metadata['total_events']


def test_service_stream_invalid_range_raises():
    """stream_astronomical_events should raise ValueError for a too-large range,
    matching get_astronomical_events."""
    with pytest.raises(ValueError):
        list(stream_astronomical_events(
            start_date_str="2000-01-01",
            end_date_str="2025-01-01",
        ))


def test_route_stream_basic_request():
    """Route-level SSE: basic request streams pages then a metadata event."""
    resp = client.get("/api/v1/astronomical-events-stream", params={
        "start_date": "2025-09-01",
        "end_date": "2025-09-10",
        "include_contact_times": "false",
    })
    assert resp.status_code == 200
    events = resp.text.strip().split("\n\n")
    page_events = [e for e in events if e.startswith("event: page")]
    metadata_events = [e for e in events if e.startswith("event: metadata")]

    assert len(page_events) >= 1
    assert len(metadata_events) == 1

    all_events = []
    for e in page_events:
        data = json.loads(e.split("data: ", 1)[1])
        all_events.extend(data['events'])

    metadata = json.loads(metadata_events[0].split("data: ", 1)[1])
    assert metadata['total_events'] == len(all_events)
    assert any(
        ev['date'][:10] == '2025-09-07' and ev['eclipse_type'] == 'Total'
        for ev in all_events
    )


def test_route_stream_paginates_like_post_endpoint():
    """SSE pages should group events the same way page_size does for the POST endpoint."""
    resp = client.get("/api/v1/astronomical-events-stream", params={
        "start_date": NARROW_RANGE_START,
        "end_date": NARROW_RANGE_END,
        "page_size": 2,
        "include_contact_times": "false",
    })
    assert resp.status_code == 200
    events = resp.text.strip().split("\n\n")
    page_events = [e for e in events if e.startswith("event: page")]
    for e in page_events[:-1]:
        data = json.loads(e.split("data: ", 1)[1])
        assert len(data['events']) == 2


def test_route_stream_invalid_date_format_returns_422():
    """Malformed date strings should fail Pydantic pattern validation (422) before streaming starts."""
    resp = client.get("/api/v1/astronomical-events-stream", params={
        "start_date": "not-a-date",
        "end_date": "2025-09-10",
    })
    assert resp.status_code == 422


def test_route_stream_end_before_start_returns_422():
    """End date before start date is caught by Pydantic model_validator -> 422."""
    resp = client.get("/api/v1/astronomical-events-stream", params={
        "start_date": "2026-01-01",
        "end_date": "2025-01-01",
    })
    assert resp.status_code == 422


def test_route_stream_range_too_large_returns_400():
    """A date range exceeding MAX_RANGE_DAYS should fail fast with 400 before streaming starts."""
    resp = client.get("/api/v1/astronomical-events-stream", params={
        "start_date": "2000-01-01",
        "end_date": "2025-01-01",
    })
    assert resp.status_code == 400


def test_route_stream_event_types_filter():
    """event_types filter (repeated query param) should be honored."""
    resp = client.get("/api/v1/astronomical-events-stream", params={
        "start_date": NARROW_RANGE_START,
        "end_date": NARROW_RANGE_END,
        "event_types": ["new_moon"],
        "include_contact_times": "false",
    })
    assert resp.status_code == 200
    events = resp.text.strip().split("\n\n")
    page_events = [e for e in events if e.startswith("event: page")]
    for e in page_events:
        data = json.loads(e.split("data: ", 1)[1])
        for ev in data['events']:
            assert ev['event_type'] == 'New Moon'
