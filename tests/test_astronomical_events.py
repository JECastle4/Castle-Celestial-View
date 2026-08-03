"""
Tests for astronomical events detection (new/full moons + eclipse classification).

The expected eclipse types below were validated against Wikipedia's published
eclipse records for 2025-2026 during implementation.
"""
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.services.astronomical_events import get_astronomical_events

client = TestClient(app)


# (date, event_type, expected eclipse_type)
KNOWN_ECLIPSES = [
    ("2025-09-07", "full_moon", "TOTAL"),
    ("2025-09-21", "new_moon", "PARTIAL"),
    ("2026-02-17", "new_moon", "ANNULAR"),
    ("2026-03-03", "full_moon", "TOTAL"),
    ("2026-08-12", "new_moon", "TOTAL"),
    ("2026-08-28", "full_moon", "PARTIAL"),
]


def test_service_finds_known_eclipses():
    """Service-level: all 6 known 2025-2026 eclipses are found and classified correctly."""
    result = get_astronomical_events(
        start_date_str="2025-08-01",
        end_date_str="2026-09-01",
        page=1,
        page_size=100,
    )
    events_by_date = {e["date"][:10]: e for e in result["events"]}

    for date_str, event_type, expected_type in KNOWN_ECLIPSES:
        assert date_str in events_by_date, f"Missing event on {date_str}"
        event = events_by_date[date_str]
        assert event["event_type"] == event_type
        assert event["eclipse_type"] == expected_type
        assert event["eclipse_occurs"] is True
        assert event["greatest_eclipse_time"] is not None


def test_service_non_eclipse_events_marked_none():
    """Non-eclipse new/full moons should classify as NONE with eclipse_occurs False."""
    result = get_astronomical_events(
        start_date_str="2025-08-01",
        end_date_str="2026-09-01",
        page=1,
        page_size=100,
    )
    known_dates = {d for d, _, _ in KNOWN_ECLIPSES}
    non_eclipse_events = [e for e in result["events"] if e["date"][:10] not in known_dates]
    assert len(non_eclipse_events) > 0
    for event in non_eclipse_events:
        assert event["eclipse_type"] == "NONE"
        assert event["eclipse_occurs"] is False


def test_service_pagination():
    """Pagination math should be consistent with total_events."""
    result = get_astronomical_events(
        start_date_str="2025-08-01",
        end_date_str="2026-09-01",
        page=1,
        page_size=5,
    )
    assert len(result["events"]) == 5
    assert result["pagination"]["page"] == 1
    assert result["pagination"]["page_size"] == 5
    assert result["pagination"]["total_events"] == 27
    assert result["pagination"]["total_pages"] == 6


def test_service_event_type_filter():
    """Filtering by event_types should only return the requested phase."""
    result = get_astronomical_events(
        start_date_str="2025-08-01",
        end_date_str="2026-09-01",
        page=1,
        page_size=100,
        event_types=["full_moon"],
    )
    assert len(result["events"]) > 0
    assert all(e["event_type"] == "full_moon" for e in result["events"])


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
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["pagination"]["total_events"] == 1
    assert data["events"][0]["eclipse_type"] == "TOTAL"
    assert data["events"][0]["event_type"] == "full_moon"


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
        "start_date": "2025-08-01",
        "end_date": "2026-09-01",
        "event_types": ["eclipse"],
    })
    assert resp.status_code == 422


def test_route_pagination_params():
    """Custom page/page_size should be honored end-to-end."""
    resp = client.post("/api/v1/astronomical-events", json={
        "start_date": "2025-08-01",
        "end_date": "2026-09-01",
        "page": 2,
        "page_size": 5,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["events"]) == 5
    assert data["pagination"]["page"] == 2
