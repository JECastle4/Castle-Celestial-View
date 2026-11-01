"""Canonical classification parity across calendar transports and contacts."""
import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.cache import clear_response_cache
from api.i18n import get_i18n
from api.main import app
from api.models import AstronomicalEvent
from api.services.astronomical_events import get_astronomical_events, get_contact_times_for_event
from api.services.eclipse_classification import clear_classification_cache


client = TestClient(app)


def streamed_events(response):
    assert response.status_code == 200
    chunks = response.text.strip().split("\n\n")
    assert sum(chunk.startswith("event: metadata") for chunk in chunks) == 1
    return [
        event
        for chunk in chunks if chunk.startswith("event: page")
        for event in json.loads(chunk.split("data: ", 1)[1])["events"]
    ]


@pytest.mark.parametrize("locale", ["en", "en-us", "en-uk", "xx-reverse"])
def test_hybrid_post_stream_and_warm_cache_parity(locale):
    clear_response_cache()
    clear_classification_cache()
    payload = {
        "start_date": "2023-04-19",
        "end_date": "2023-04-21",
        "include_contact_times": False,
        "page_size": 10,
    }
    cold = client.post(f"/api/v1/astronomical-events?lang={locale}", json=payload)
    assert cold.status_code == 200
    warm = client.post(f"/api/v1/astronomical-events?lang={locale}", json=payload)
    assert warm.json() == cold.json()
    stream = client.get("/api/v1/astronomical-events-stream", params={
        **payload, "include_contact_times": "false", "lang": locale,
    })
    assert streamed_events(stream) == cold.json()["events"]
    event = cold.json()["events"][0]
    assert event["global_eclipse_type"] == "HYBRID"
    assert event["maximum_eclipse_phase"] == "TOTAL"
    assert event["eclipse_type"] == get_i18n(locale).get("events.eclipseTypes.TOTAL")
    assert event["classification_revision"]
    assert event["date"].startswith("2023-04-20")


@pytest.mark.parametrize("date,phase", [
    ("2023-04-20", "TOTAL"),
    ("2023-10-14", "ANNULAR"),
    ("2025-03-29", "PARTIAL"),
    ("2014-04-29", "ANNULAR"),
    ("2043-04-09", "TOTAL"),
])
def test_inline_lazy_and_stream_contacts_share_geometry(date, phase):
    result = get_astronomical_events(
        date, date, include_contact_times=True, locale="en",
    )
    event = result["events"][0]
    assert event["maximum_eclipse_phase"] == phase
    lazy = get_contact_times_for_event(event["date"], False)
    assert lazy == event["contact_times"]
    stream = client.get("/api/v1/astronomical-events-stream", params={
        "start_date": date, "end_date": date, "include_contact_times": "true", "lang": "en",
    })
    assert streamed_events(stream)[0]["contact_times"] == lazy
    assert lazy["eclipse_begins"] < lazy["eclipse_ends"]
    if phase == "PARTIAL":
        assert lazy["central_phase_begins"] is None
        assert lazy["central_phase_ends"] is None
    else:
        assert (lazy["eclipse_begins"] < lazy["central_phase_begins"]
                < lazy["central_phase_ends"] < lazy["eclipse_ends"])


def test_solar_numerical_failure_is_not_no_eclipse():
    clear_response_cache()
    with patch("api.services.astronomical_events.classify_solar_eclipse",
               side_effect=RuntimeError("private numerical detail")):
        response = client.post("/api/v1/astronomical-events", json={
            "start_date": "2023-04-20", "end_date": "2023-04-20",
            "include_contact_times": False,
        })
    assert response.status_code == 500
    assert "private numerical detail" not in response.text


def test_stream_failure_is_terminal_and_does_not_emit_metadata():
    def failing_stream(**kwargs):
        yield {"page": 1, "events": []}
        raise RuntimeError("private numerical detail")

    with patch("api.routes.events.stream_astronomical_events", side_effect=failing_stream):
        response = client.get("/api/v1/astronomical-events-stream", params={
            "start_date": "2023-04-20", "end_date": "2023-04-20",
        })
    assert response.status_code == 200
    assert "event: calculation-error" in response.text
    assert "event: metadata" not in response.text
    assert "private numerical detail" not in response.text


def test_out_of_range_solar_circumstances_are_explicit():
    event = get_astronomical_events(
        "2185-07-26", "2185-07-26", include_contact_times=False, locale="en",
    )["events"][0]
    assert event["global_eclipse_type"] == "TOTAL"
    assert "1900-2100" in event["classification_warning"]


@pytest.mark.parametrize("changes", [
    {"maximum_eclipse_phase": "ANNULAR"},
    {"eclipse_occurs": False},
    {"is_lunar": True},
    {"global_eclipse_type": "PENUMBRAL", "maximum_eclipse_phase": "PENUMBRAL"},
])
def test_response_model_rejects_contradictory_classification(changes):
    event = get_astronomical_events(
        "2023-04-20", "2023-04-20", include_contact_times=False, locale="en",
    )["events"][0]
    with pytest.raises(ValueError):
        AstronomicalEvent(**{**event, **changes})
