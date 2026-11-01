"""Reference eclipse cases for maximum-phase classification (issue #275).

Cases live in tests/fixtures/eclipse_reference_cases.json. Entries with a
``known_failure`` are strict xfails, so fixing the classifier makes them fail
until the fixture is updated.
"""
import datetime as dt
import json
from pathlib import Path

import pytest

from api.i18n import get_i18n
from api.services.astronomical_events import get_astronomical_events

FIXTURE = Path(__file__).parent / "fixtures" / "eclipse_reference_cases.json"
CASES = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]

SOLAR_TYPES = {"HYBRID", "TOTAL", "ANNULAR", "PARTIAL", "NONE"}
LUNAR_TYPES = {"TOTAL", "PARTIAL", "PENUMBRAL", "NONE"}
ARRANGEMENTS = {"central_two_limits", "central_one_limit", "non_central_one_limit"}
CENTRAL_TYPES = {"HYBRID", "TOTAL", "ANNULAR"}


def _param(case):
    marks = []
    if case["known_failure"]:
        marks.append(pytest.mark.xfail(strict=True, reason=case["known_failure"]))
    return pytest.param(case, id=case["id"], marks=marks)


@pytest.mark.parametrize("case", [pytest.param(c, id=c["id"]) for c in CASES])
def test_reference_case_is_well_formed(case):
    dt.date.fromisoformat(case["date"])
    assert case["body"] in {"solar", "lunar"}
    assert case["verification"] in {"published", "computed"}
    assert case["sources"]
    allowed = SOLAR_TYPES if case["body"] == "solar" else LUNAR_TYPES
    assert case["global_type"] in allowed
    expected_calendar = "TOTAL" if case["global_type"] == "HYBRID" else case["global_type"]
    assert case["calendar_type"] == expected_calendar
    if case["body"] == "solar" and case["global_type"] in CENTRAL_TYPES:
        assert case["arrangement"] in ARRANGEMENTS
    else:
        assert case["arrangement"] is None
    assert (case["hybrid_sequence"] is not None) == (case["global_type"] == "HYBRID")
    assert (case["approximate_greatest_utc"] is None) == (case["global_type"] == "NONE")


def test_reference_cases_cover_known_edge_cases():
    ids = [c["id"] for c in CASES]
    assert len(ids) == len(set(ids))

    solar = [c for c in CASES if c["body"] == "solar"]
    lunar = [c for c in CASES if c["body"] == "lunar"]
    assert {c["global_type"] for c in solar} == SOLAR_TYPES
    assert {c["global_type"] for c in lunar} == LUNAR_TYPES
    for phase in ("TOTAL", "ANNULAR"):
        assert {c["arrangement"] for c in solar if c["global_type"] == phase} == ARRANGEMENTS
    assert {c["hybrid_sequence"] for c in solar if c["hybrid_sequence"]} >= {"A-T-A", "A-T"}


@pytest.mark.parametrize("case", [_param(c) for c in CASES])
def test_reference_case_calendar_type(case):
    date = dt.date.fromisoformat(case["date"])
    result = get_astronomical_events(
        start_date_str=str(date - dt.timedelta(days=1)),
        end_date_str=str(date + dt.timedelta(days=1)),
        page_size=10,
        include_contact_times=False,
        event_types=["new_moon" if case["body"] == "solar" else "full_moon"],
        locale="en",
    )
    events = result["events"]
    assert len(events) == 1, f"Expected one {case['body']} event near {date}: {events}"
    event = events[0]

    assert event["is_lunar"] is (case["body"] == "lunar")
    expected_label = get_i18n("en").get(f"events.eclipseTypes.{case['calendar_type']}")
    assert event["eclipse_type"] == expected_label
    assert event["global_eclipse_type"] == case["global_type"]
    assert event["maximum_eclipse_phase"] == case["calendar_type"]
    assert event["classification_revision"]
    assert event["eclipse_occurs"] is (case["calendar_type"] != "NONE")
