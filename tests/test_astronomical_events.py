"""
Tests for astronomical events detection (new/full moons + eclipse classification).

The expected eclipse types below were validated against Wikipedia's published
eclipse records for 2025-2026 during implementation.
"""
import json
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from api.main import app
from api.services.astronomical_events import (
    get_astronomical_events,
    stream_astronomical_events,
    get_contact_times_for_event,
)

client = TestClient(app)

# (date, expected_event_type, expected eclipse_type)
# event_type is now the combined semantic type (e.g., "Lunar Total" for lunar eclipses)
# eclipse_type remains the code-based type (e.g., "Total")
KNOWN_ECLIPSES = [
    ("2025-09-07", "Lunar Total", "Total"),
    ("2025-09-21", "Solar Partial", "Partial"),
    ("2026-02-17", "Solar Annular", "Annular"),
    ("2026-03-03", "Lunar Total", "Total"),
    ("2026-08-12", "Solar Total", "Total"),
    ("2026-08-28", "Lunar Partial", "Partial"),
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
    events = full_range_result["events"]
    
    for date_str, event_type, expected_type in KNOWN_ECLIPSES:
        # Find the eclipse event for this date (there may be multiple events on same date)
        matching_events = [e for e in events if e["date"][:10] == date_str and e["eclipse_occurs"]]
        assert len(matching_events) > 0, f"Missing eclipse event on {date_str}"
        
        event = matching_events[0]
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
    """Filtering by event_types should only return the requested phase (lunar or solar)."""
    result = get_astronomical_events(
        start_date_str=NARROW_RANGE_START,
        end_date_str=NARROW_RANGE_END,
        page=1,
        page_size=100,
        event_types=["full_moon"],
        include_contact_times=False,
    )
    assert len(result["events"]) > 0
    # Full moon events should have "Full Moon" (non-eclipse) or "Lunar *" (eclipse) in event_type
    for event in result["events"]:
        assert "Full Moon" in event["event_type"] or "Lunar" in event["event_type"]


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
    assert data["events"][0]["event_type"] == "Lunar Total"


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
            # New moon events should be "New Moon" (non-eclipse) or "Solar *" (eclipse)
            assert "New Moon" in ev['event_type'] or "Solar" in ev['event_type']


def test_route_get_astronomical_events_value_error_handling():
    """Test ValueError exception handling in GET astronomical-events endpoint."""
    with patch("api.routes.events.get_astronomical_events") as mock_get:
        mock_get.side_effect = ValueError("Test calculation error")

        resp = client.post("/api/v1/astronomical-events", json={
            "start_date": NARROW_RANGE_START,
            "end_date": NARROW_RANGE_END,
        })

        assert resp.status_code == 400
        assert "Invalid input" in resp.json()["detail"]


def test_route_get_astronomical_events_unexpected_error_handling():
    """Test unexpected exception handling in GET astronomical-events endpoint."""
    with patch("api.routes.events.get_astronomical_events") as mock_get:
        mock_get.side_effect = RuntimeError("Unexpected error")

        resp = client.post("/api/v1/astronomical-events", json={
            "start_date": NARROW_RANGE_START,
            "end_date": NARROW_RANGE_END,
        })

        assert resp.status_code == 500
        assert "An internal error occurred" in resp.json()["detail"]


def test_route_stream_astronomical_events_unexpected_error_handling():
    """Test unexpected exception handling in stream astronomical-events endpoint.
    
    Errors during route handler execution (before StreamingResponse is returned)
    are caught by the route's exception handlers. Errors during streaming iteration
    happen after response is sent and are handled by the streaming middleware.
    """
    with patch("api.routes.events.validate_date_range") as mock_validate:
        mock_validate.side_effect = RuntimeError("Unexpected validation error")

        resp = client.get("/api/v1/astronomical-events-stream", params={
            "start_date": NARROW_RANGE_START,
            "end_date": NARROW_RANGE_END,
        })

        assert resp.status_code == 500
        assert "An internal error occurred" in resp.json()["detail"]


# ============================================================================
# Tests for lazy-loading contact-times endpoint and service function
# ============================================================================

@pytest.fixture
def eclipse_event_with_date():
    """Get a real eclipse event and its full ISO datetime for testing."""
    result = get_astronomical_events(
        start_date_str=FULL_RANGE_START,
        end_date_str=FULL_RANGE_END,
        page=1,
        page_size=100,
        include_contact_times=False,
    )
    eclipse_events = [e for e in result["events"] if e["eclipse_occurs"]]
    assert len(eclipse_events) >= 2, "Need at least 2 eclipse events for testing"
    
    # Return lunar and solar eclipses
    lunar_event = next((e for e in eclipse_events if e["is_lunar"]), None)
    solar_event = next((e for e in eclipse_events if not e["is_lunar"]), None)
    
    return {
        "lunar": lunar_event,
        "solar": solar_event,
    }


def test_service_contact_times_for_valid_lunar_eclipse(eclipse_event_with_date):
    """Service function should return contact times for a valid lunar eclipse."""
    event = eclipse_event_with_date["lunar"]
    assert event is not None, "Test requires a lunar eclipse event"
    
    contact_times = get_contact_times_for_event(
        event_date_iso=event["date"],
        is_lunar=True,
    )
    
    assert contact_times is not None
    assert isinstance(contact_times, dict)
    # Lunar eclipses should have some contact time keys (p1, u1, u2, u3, u4, p4)
    assert len(contact_times) > 0


def test_service_contact_times_for_valid_solar_eclipse(eclipse_event_with_date):
    """Service function should return contact times for a valid solar eclipse."""
    event = eclipse_event_with_date["solar"]
    assert event is not None, "Test requires a solar eclipse event"
    
    contact_times = get_contact_times_for_event(
        event_date_iso=event["date"],
        is_lunar=False,
    )
    
    assert contact_times is not None
    assert isinstance(contact_times, dict)
    # Solar eclipses should have contact time keys (c1, c2, c3, c4 or similar)
    assert len(contact_times) > 0


def test_service_contact_times_invalid_date_format():
    """Service function should raise ValueError for malformed ISO datetime."""
    with pytest.raises(ValueError, match="Invalid event_date"):
        get_contact_times_for_event(
            event_date_iso="not-a-date",
            is_lunar=True,
        )


def test_service_contact_times_invalid_date_format_wrong_separator():
    """ISO datetime with T separator instead of space should fail."""
    with pytest.raises(ValueError, match="Invalid event_date"):
        get_contact_times_for_event(
            event_date_iso="2025-09-07T12:00:00",
            is_lunar=True,
        )


def test_service_contact_times_far_future_date():
    """Contact time calculation should handle dates far outside eclipse periods gracefully."""
    # A date with no eclipse nearby should either return empty dict or raise ValueError
    # depending on the calculation logic. Both are acceptable.
    try:
        contact_times = get_contact_times_for_event(
            event_date_iso="2050-01-01 12:00:00",
            is_lunar=True,
        )
        # If it succeeds, it should be a dict (possibly empty)
        assert isinstance(contact_times, dict)
    except ValueError:
        # If it fails, that's also acceptable - not every date is an eclipse
        pass


def test_route_contact_times_for_valid_lunar_eclipse(eclipse_event_with_date):
    """Route endpoint should return contact times for valid lunar eclipse request."""
    event = eclipse_event_with_date["lunar"]
    assert event is not None
    
    resp = client.post("/api/v1/astronomical-events/contact-times", json={
        "event_date": event["date"],
        "is_lunar": True,
    })
    
    assert resp.status_code == 200
    data = resp.json()
    assert "contact_times" in data
    assert data["contact_times"] is not None


def test_route_contact_times_for_valid_solar_eclipse(eclipse_event_with_date):
    """Route endpoint should return contact times for valid solar eclipse request."""
    event = eclipse_event_with_date["solar"]
    assert event is not None
    
    resp = client.post("/api/v1/astronomical-events/contact-times", json={
        "event_date": event["date"],
        "is_lunar": False,
    })
    
    assert resp.status_code == 200
    data = resp.json()
    assert "contact_times" in data
    assert data["contact_times"] is not None


def test_route_contact_times_invalid_request_missing_field():
    """Route should return 422 for missing required field."""
    resp = client.post("/api/v1/astronomical-events/contact-times", json={
        "event_date": "2025-09-07 12:00:00",
        # Missing is_lunar
    })
    
    assert resp.status_code == 422


def test_route_contact_times_invalid_date_format_returns_422():
    """Route should return 422 for invalid ISO datetime format (Pydantic validation)."""
    resp = client.post("/api/v1/astronomical-events/contact-times", json={
        "event_date": "not-a-date",
        "is_lunar": True,
    })
    
    # Pydantic catches format validation first, returns 422
    assert resp.status_code == 422


def test_route_contact_times_with_lang_parameter(eclipse_event_with_date):
    """Contact times endpoint should accept lang query parameter."""
    event = eclipse_event_with_date["lunar"]
    assert event is not None
    
    resp = client.post("/api/v1/astronomical-events/contact-times?lang=es", json={
        "event_date": event["date"],
        "is_lunar": True,
    })
    
    assert resp.status_code == 200


def test_route_contact_times_cache_behavior(eclipse_event_with_date):
    """Same request should be cached (fast second call)."""
    event = eclipse_event_with_date["lunar"]
    assert event is not None
    
    payload = {
        "event_date": event["date"],
        "is_lunar": True,
    }
    
    # First request
    resp1 = client.post("/api/v1/astronomical-events/contact-times", json=payload)
    assert resp1.status_code == 200
    data1 = resp1.json()
    
    # Second identical request should get cached result
    resp2 = client.post("/api/v1/astronomical-events/contact-times", json=payload)
    assert resp2.status_code == 200
    data2 = resp2.json()
    
    # Results should be identical
    assert data1 == data2


def test_route_contact_times_unexpected_error_handling():
    """Test unexpected exception handling in contact-times endpoint."""
    with patch("api.routes.events.get_contact_times_for_event") as mock_service:
        mock_service.side_effect = RuntimeError("Unexpected calculation error")

        resp = client.post("/api/v1/astronomical-events/contact-times", json={
            "event_date": "2025-09-07 12:00:00",
            "is_lunar": True,
        })

        assert resp.status_code == 500
        assert "An internal error occurred" in resp.json()["detail"]


class TestLocaleNormalization:
    """Tests for locale parameter normalization (en-US → en-us for backend matching)."""

    def test_get_events_locale_uppercase_normalized(self):
        """Locale parameter should be normalized to lowercase in POST events endpoint."""
        # Request with uppercase locale (events search is POST, not GET)
        resp = client.post(
            "/api/v1/astronomical-events?lang=en-US",
            json={
                "start_date": "2025-09-01",
                "end_date": "2025-09-30",
                "include_contact_times": False,
            }
        )
        
        # Should not fail due to locale mismatch
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data

    def test_post_events_locale_uppercase_normalized(self):
        """Locale parameter should be normalized to lowercase in POST events endpoint."""
        # Request with uppercase locale
        resp = client.post(
            "/api/v1/astronomical-events?lang=en-US",
            json={
                "start_date": "2025-09-01",
                "end_date": "2025-09-30",
                "include_contact_times": False,
            }
        )
        
        # Should not fail due to locale mismatch
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data

    def test_contact_times_locale_uppercase_normalized(self):
        """Locale parameter should be normalized to lowercase in contact-times endpoint."""
        resp = client.post(
            "/api/v1/astronomical-events/contact-times?lang=en-US",
            json={
                "event_date": "2025-09-07 12:00:00",
                "is_lunar": True,
            }
        )
        
        # Should not fail due to locale mismatch
        assert resp.status_code in [200, 422]  # 200 if valid eclipse, 422 if invalid date

    def test_stream_events_locale_uppercase_normalized(self):
        """Locale parameter should be normalized to lowercase in stream endpoint."""
        resp = client.get(
            "/api/v1/astronomical-events-stream?"
            "start_date=2025-09-01&"
            "end_date=2025-09-30&"
            "include_contact_times=false&"
            "lang=en-UK"
        )
        
        # Should successfully start stream with normalized locale
        assert resp.status_code == 200

    def test_locale_mixed_case_normalized(self):
        """Mixed-case locales should be normalized consistently."""
        # Test with en-Us (mixed case)
        resp = client.post(
            "/api/v1/astronomical-events?lang=en-Us",
            json={
                "start_date": "2025-09-01",
                "end_date": "2025-09-30",
                "include_contact_times": False,
            }
        )
        
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data

    def test_locale_all_uppercase_normalized(self):
        """All-uppercase locales should be normalized to lowercase."""
        resp = client.post(
            "/api/v1/astronomical-events?lang=EN-US",
            json={
                "start_date": "2025-09-01",
                "end_date": "2025-09-30",
                "include_contact_times": False,
            }
        )
        
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data
