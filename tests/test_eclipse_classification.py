"""Regression and geometry tests for the reusable global solar classifier."""

import json
from pathlib import Path
from dataclasses import FrozenInstanceError, replace
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from types import SimpleNamespace

import numpy as np
import pytest
from astropy.time import Time
from astropy.utils import iers

from api.services import eclipse_classification as solar
from api.services.eclipse_errors import EclipseCalculationError


FIXTURE = Path(__file__).parent / "fixtures" / "eclipse_reference_cases.json"


@pytest.mark.parametrize(
    ("phases", "expected"),
    [
        ((), "NONE"),
        (("PARTIAL",), "PARTIAL"),
        (("ANNULAR", "PARTIAL"), "ANNULAR"),
        (("TOTAL", "PARTIAL"), "TOTAL"),
        (("TOTAL", "ANNULAR", "PARTIAL"), "HYBRID"),
    ],
)
def test_global_phase_resolution(phases, expected):
    assert solar._global_type(dict.fromkeys(phases), None) == expected


def test_axis_transition_requires_both_strong_witnesses():
    with pytest.raises(EclipseCalculationError, match="axis transition lacks both phase witnesses"):
        solar._global_type({"TOTAL": object()}, "A-T")


@pytest.mark.parametrize(
    ("values", "expected"),
    [([-1., -0.1, -1.], False), ([-1., 1., -1.], True)],
)
def test_contact_interval_resolution(values, expected):
    assert solar._has_contact_interval(values) is expected


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ([0., 1., -1.], "outside the search window"),
        ([-1., 1., 0.], "outside the search window"),
        ([-1., 0., -1.], "Indeterminate global solar contact"),
    ],
)
def test_contact_interval_rejects_ambiguity_or_open_window(values, message):
    with pytest.raises(EclipseCalculationError, match=message):
        solar._has_contact_interval(values)


@pytest.mark.parametrize(
    ("clearance", "point", "message"),
    [
        (np.nan, None, "Non-finite TOTAL surface clearance"),
        (1., None, "Missing TOTAL surface witness"),
    ],
)
def test_witness_clearance_rejects_invalid_evidence(clearance, point, message):
    with pytest.raises(EclipseCalculationError, match=message):
        solar._validate_witness_clearance("TOTAL", clearance, point)


def test_contact_crossings_keep_first_and_last_of_disjoint_intervals(monkeypatch):
    monkeypatch.setattr(
        solar, "_combined_margin", lambda _context, seconds, _phases: np.cos(np.pi * seconds)
    )
    times = np.array([-1., 0., 1., 2., 3.])
    crossings = solar._contact_crossings(None, ("TOTAL", "ANNULAR"), times, [-1, 1, -1, 1, -1])
    assert crossings == pytest.approx([-0.5, 0.5, 1.5, 2.5], abs=0.001)


@pytest.mark.parametrize("error_type", [ValueError, RuntimeError, EclipseCalculationError])
def test_contact_crossings_preserve_callback_exceptions(monkeypatch, error_type):
    error = error_type("callback failure")

    def broken_margin(*_args):
        raise error

    monkeypatch.setattr(solar, "_combined_margin", broken_margin)
    with pytest.raises(error_type) as raised:
        solar._contact_crossings(None, ("TOTAL",), [-1., 0., 1.], [-1., 1., -1.])
    assert raised.value is error


@pytest.mark.parametrize(("root", "converged"), [(0., False), (np.nan, True)])
def test_contact_crossings_reject_solver_failure(monkeypatch, root, converged):
    def failed_solver(*_args, **kwargs):
        assert kwargs["full_output"] is True
        assert kwargs["disp"] is False
        return root, SimpleNamespace(converged=converged)

    monkeypatch.setattr(solar, "brentq", failed_solver)
    with pytest.raises(EclipseCalculationError, match="did not converge"):
        solar._contact_crossings(None, ("TOTAL",), [-1., 0., 1.], [-1., 1., -1.])


def _solar_cases():
    cases = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
    return [case for case in cases if case["body"] == "solar"]


def _seconds_apart(actual, expected):
    return abs((Time(actual, scale="utc") - Time(expected, scale="utc")).to_value("sec"))


def test_full_21_case_solar_catalog():
    cases = _solar_cases()
    assert len(cases) == 21
    with iers.conf.set_temp("auto_download", False), iers.conf.set_temp("auto_max_age", None):
        for case in cases:
            seed = case["approximate_greatest_utc"] or f'{case["date"]} 12:00'
            result = solar.classify_solar_eclipse(Time(seed, scale="utc"))
            assert result.global_type == case["global_type"], case["id"]
            assert result.maximum_phase == case["calendar_type"], case["id"]
            assert result.central_path.central == (case["arrangement"] in (
                "central_two_limits", "central_one_limit")), case["id"]
            assert result.central_path.hybrid_sequence == case["hybrid_sequence"], case["id"]
            if result.central_path.central:
                assert result.central_path.central_interval_utc is not None
            else:
                assert result.central_path.central_interval_utc is None
            assert len(result.central_path.axis_phase_transitions_utc) == (
                len(case["hybrid_sequence"].split("-")) - 1
                if case["hybrid_sequence"] else 0
            ), case["id"]
            assert result.model_revision == solar.SOLAR_MODEL_REVISION
            assert result.greatest_eclipse_time.isscalar
            assert result.size_ratio > 0
            assert all(witness.clearance_km > solar.PHASE_TOLERANCE_KM
                       for witness in result.witnesses)
            assert all(len(witness.surface_point_cirs_km) == 3
                       for witness in result.witnesses)
            if case["global_type"] == "HYBRID":
                assert {witness.phase for witness in result.witnesses} >= {
                    "TOTAL", "ANNULAR"
                }


@pytest.mark.parametrize(
    ("seed", "contact_key", "expected", "tolerance_seconds"),
    [
        ("2023-04-20 04:17", "eclipse_begins", "2023-04-20 01:34:26", 90),
        ("2023-04-20 04:17", "central_phase_begins", "2023-04-20 02:37:00", 90),
        ("2023-04-20 04:17", "central_phase_ends", "2023-04-20 05:58:00", 120),
        ("2023-04-20 04:17", "eclipse_ends", "2023-04-20 06:59:22", 90),
        ("2017-08-21 18:26", "central_phase_begins", "2017-08-21 16:48:32", 90),
        ("2017-08-21 18:26", "central_phase_ends", "2017-08-21 20:01:35", 90),
        ("2023-10-14 17:59", "eclipse_begins", "2023-10-14 15:03:00", 90),
        ("2023-10-14 17:59", "central_phase_ends", "2023-10-14 19:49:00", 90),
        ("2025-03-29 10:48", "eclipse_begins", "2025-03-29 08:50:40", 90),
        ("2025-03-29 10:48", "eclipse_ends", "2025-03-29 12:43:38", 90),
        ("2014-04-29 06:04", "eclipse_begins", "2014-04-29 03:52:38", 90),
        ("2014-04-29 06:04", "central_phase_begins", "2014-04-29 05:57:00", 120),
        ("2014-04-29 06:04", "eclipse_ends", "2014-04-29 08:14:28", 90),
    ],
)
def test_published_global_contact_references(seed, contact_key, expected, tolerance_seconds):
    """NASA/EclipseWise global contacts, not local observer contacts.

    Sources: NASA 2023 hybrid path
    (https://eclipse.gsfc.nasa.gov/SEpath/SEpath2001/SE2023Apr20Hpath.html),
    NASA's 2017 eclipse figure
    (https://eclipse.gsfc.nasa.gov/SEmono/TSE2017/TSE2017fig/TSE2017Aug21-Fig01.pdf),
    USNO's 2023 annular table (https://aa.usno.navy.mil/data/Eclipse2023),
    timeanddate's 2025 partial table
    (https://www.timeanddate.com/eclipse/solar/2025-march-29), and NASA's
    2014 Besselian elements
    (https://eclipse.gsfc.nasa.gov/SEsearch/SEdata.php?Ecl=20140429).
    """
    analysis = solar.classify_solar_eclipse(Time(seed, scale="utc"))
    contacts = solar.calculate_global_solar_contacts(analysis)
    actual = contacts[contact_key]
    assert actual is not None
    assert _seconds_apart(actual, expected) <= tolerance_seconds


def test_partial_and_none_contact_shapes():
    partial = solar.classify_solar_eclipse(Time("2025-03-29 10:48", scale="utc"))
    partial_contacts = solar.calculate_global_solar_contacts(partial)
    assert partial_contacts["eclipse_begins"] is not None
    assert partial_contacts["eclipse_ends"] is not None
    assert partial_contacts["central_phase_begins"] is None
    assert partial_contacts["central_phase_ends"] is None

    none = solar.classify_solar_eclipse(Time("2023-05-19 12:00", scale="utc"))
    assert none.global_type == "NONE"
    assert set(solar.calculate_global_solar_contacts(none).values()) == {None}


def test_noncentral_annular_contacts_are_found_without_axis_roots():
    result = solar.classify_solar_eclipse(Time("2014-04-29 06:04", scale="utc"))
    assert result.global_type == "ANNULAR"
    assert not result.central_path.central
    contacts = solar.calculate_global_solar_contacts(result)
    assert contacts["central_phase_begins"] is not None
    assert contacts["central_phase_ends"] is not None


def test_central_path_diagnostics_are_immutable():
    path = solar.SolarCentralPath(False, None, None, ())
    with pytest.raises(FrozenInstanceError):
        path.central = True
    assert replace(path, central=True).central


def test_cache_is_bounded_reusable_and_clearable():
    seed = Time("2023-04-20 04:17", scale="utc")
    solar.clear_classification_cache()
    with patch.object(solar, "_analyze", wraps=solar._analyze) as analyze:
        first = solar.classify_solar_eclipse(seed)
        second = solar.classify_solar_eclipse(seed)
        assert first is second
        assert analyze.call_count == 1
        solar.clear_classification_cache()
        solar.classify_solar_eclipse(seed)
        assert analyze.call_count == 2
    assert len(solar._CLASSIFICATION_CACHE._entries) <= 128


def test_failed_classification_is_not_cached():
    seed = Time("2023-04-20 04:17", scale="utc")
    solar.clear_classification_cache()
    with patch.object(solar, "_analyze", side_effect=RuntimeError("solver failed")):
        with pytest.raises(RuntimeError, match="solver failed"):
            solar.classify_solar_eclipse(seed)
    assert len(solar._CLASSIFICATION_CACHE._entries) == 0


def test_invalid_time_and_contact_window_raise():
    with pytest.raises(ValueError, match="scalar astropy Time"):
        solar.classify_solar_eclipse(Time(["2023-04-20", "2023-04-21"]))
    analysis = solar.classify_solar_eclipse(Time("2023-04-20 04:17", scale="utc"))
    with pytest.raises(ValueError, match="search_window_hours"):
        solar.calculate_global_solar_contacts(analysis, search_window_hours=0)
    with pytest.raises(ValueError, match="within 10 degrees of new moon"):
        solar.calculate_global_solar_contacts(Time("2023-05-26 12:00", scale="utc"))


def test_surface_optimizer_failure_is_explicit():
    geometry = solar.Geometry.from_vectors(
        [149600000.0, 0.0, 0.0], [360000.0, 0.0, 0.0], solar.RADIUS_MODELS["nasa"]
    )
    optimizer = type("Optimizer", (), {"success": False, "x": np.array([0.0, 0.0]),
                                       "fun": np.nan})()
    with patch("api.services.eclipse_geometry.minimize", return_value=optimizer):
        with pytest.raises(EclipseCalculationError, match="Surface optimizer did not converge"):
            geometry.best_surface_clearance("TOTAL")


def test_model_epoch_policy_is_explicit():
    assert "1900-01-01 through 2100-12-31" in solar.MODEL_METADATA["supported_epoch"]
    assert "extrapolation" in solar.MODEL_METADATA["supported_epoch"]
    assert solar.MODEL_METADATA["revision"] == solar.SOLAR_MODEL_REVISION


def test_concurrent_identical_classification_is_computed_once():
    seed = Time("2023-04-20 04:17", scale="utc")
    solar.clear_classification_cache()
    with patch.object(solar, "_analyze", wraps=solar._analyze) as analyze:
        with ThreadPoolExecutor(max_workers=3) as executor:
            results = list(executor.map(solar.classify_solar_eclipse, [seed] * 3))
        assert analyze.call_count == 1
        assert results[0] is results[1] is results[2]


def test_cache_identity_matches_serialized_event_timestamp():
    seed = Time("2023-04-20 04:12:32.362123", scale="utc")
    serialized = Time(seed.iso, scale="utc")
    assert solar._cache_key(seed) == solar._cache_key(serialized)


def test_cold_cache_classification_matches_serialized_seed():
    seed = Time("2023-04-20 04:12:32.362123", scale="utc")
    serialized = Time(seed.iso, scale="utc")
    results = []
    contacts = []
    try:
        for time_obj in (seed, serialized):
            solar.clear_classification_cache()
            solar.eclipse_ephemeris.GREATEST_ECLIPSE_CACHE.clear()
            result = solar.classify_solar_eclipse(time_obj)
            results.append(result)
            contacts.append(solar.calculate_global_solar_contacts(result))
        assert results[0] == results[1]
        assert contacts[0] == contacts[1]
    finally:
        solar.clear_classification_cache()
        solar.eclipse_ephemeris.GREATEST_ECLIPSE_CACHE.clear()


def test_contact_cache_returns_isolated_values():
    analysis = solar.classify_solar_eclipse(Time("2023-04-20 04:17", scale="utc"))
    solar._CONTACT_CACHE.clear()
    with patch.object(solar, "_contact_pair", wraps=solar._contact_pair) as pair:
        first = solar.calculate_global_solar_contacts(analysis)
        original = dict(first)
        first["eclipse_begins"] = None
        assert solar.calculate_global_solar_contacts(analysis) == original
        assert pair.call_count == 2


@pytest.mark.parametrize("missing_phase", ["penumbral", "central"])
def test_confirmed_phase_missing_contacts_is_a_calculation_error(missing_phase):
    analysis = solar.classify_solar_eclipse(Time("2023-04-20 04:17", scale="utc"))
    solar._CONTACT_CACHE.clear()
    pairs = [(None, None)] if missing_phase == "penumbral" else [
        ("2023-04-20 01:34:00.000", "2023-04-20 06:59:00.000"), (None, None),
    ]
    with patch.object(solar, "_contact_pair", side_effect=pairs):
        with pytest.raises(EclipseCalculationError, match="no resolved"):
            solar.calculate_global_solar_contacts(analysis)
    assert not solar._CONTACT_CACHE._entries


def test_contacts_reject_old_model_analysis():
    analysis = solar.classify_solar_eclipse(Time("2023-04-20 04:17", scale="utc"))
    with pytest.raises(ValueError, match="model revision"):
        solar.calculate_global_solar_contacts(replace(analysis, model_revision="old-model"))


def test_calculation_failures_remain_runtime_errors_for_existing_callers():
    assert issubclass(EclipseCalculationError, RuntimeError)
    assert solar.EclipseCalculationError is EclipseCalculationError
