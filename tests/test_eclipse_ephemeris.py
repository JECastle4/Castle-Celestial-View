import pytest
from astropy.time import Time

from api.services import eclipse_classification, eclipse_detection, eclipse_ephemeris


def test_solar_classifier_uses_lower_level_phase_guard(monkeypatch):
    seed = Time("2025-03-29 10:48", scale="utc")

    def stop_after_phase_check(*_args, **_kwargs):
        raise RuntimeError("analysis reached")

    monkeypatch.setattr(eclipse_ephemeris, "is_new_moon", lambda _time: True)
    monkeypatch.setattr(
        eclipse_detection,
        "is_new_moon",
        lambda *_args, **_kwargs: pytest.fail("legacy detector must not be called"),
    )
    monkeypatch.setattr(eclipse_classification, "_analyze", stop_after_phase_check)

    with pytest.raises(RuntimeError, match="analysis reached"):
        eclipse_classification.classify_solar_eclipse(seed)


def test_legacy_greatest_time_keeps_separation_patch_point(monkeypatch):
    calls = []
    eclipse_ephemeris.GREATEST_ECLIPSE_CACHE.clear()
    monkeypatch.setattr(
        eclipse_detection,
        "_solar_separation_deg",
        lambda time: calls.append(time) or 1.0,
    )

    eclipse_detection.find_greatest_eclipse_time(
        Time("2034-01-02 03:04", scale="utc"),
        is_lunar=False,
        iterations=2,
    )

    assert len(calls) == 4
