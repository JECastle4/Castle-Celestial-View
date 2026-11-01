# /// script
# requires-python = ">=3.12"
# dependencies = ["astropy", "numpy", "scipy"]
# ///
"""Validate the shared finite-distance solar classifier against known cases.

Run with: uv run research/validate_global_solar_eclipses.py
Expected classifications are assertions, never inputs to the numerical solver.
"""
import argparse
from dataclasses import dataclass
from importlib.metadata import version
import json
from pathlib import Path
import sys
from time import perf_counter

from astropy.time import Time
import astropy.units as u
from astropy.utils import iers

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from api.services.eclipse_classification import (  # noqa: E402
    EARTH_AXES_KM, GEOCENTRIC, PHASE_TOLERANCE_KM, ROOT_TOLERANCE_SECONDS,
    Geometry, RADIUS_MODELS, RadiusModel, SOLAR_MODEL_REVISION, _analyze, refine_maxima,
)
from api.services.eclipse_detection import find_greatest_eclipse_time  # noqa: E402


REVISION = SOLAR_MODEL_REVISION


@dataclass(frozen=True)
class Reference:
    approximate_utc: str
    global_type: str
    central: bool
    source: str
    hybrid_sequence: str | None = None
    verification: str = "published"


def load_references():
    fixture = Path(__file__).resolve().parents[1] / "tests/fixtures/eclipse_reference_cases.json"
    cases = json.loads(fixture.read_text(encoding="utf-8"))["cases"]
    return tuple(
        Reference(
            case["approximate_greatest_utc"] or f"{case['date']} 12:00",
            case["global_type"],
            case["arrangement"] in ("central_two_limits", "central_one_limit"),
            case["sources"][0], case["hybrid_sequence"], case["verification"],
        )
        for case in cases if case["body"] == "solar"
    )


REFERENCES = load_references()


def analyze(approximate_utc, step_seconds=120, radius_model="nasa"):
    started = perf_counter()
    # Do not recenter the research window: shifted seeds test the actual search,
    # whereas the public service recenters approximate event timestamps.
    raw = _analyze(approximate_utc, step_seconds, radius_model, refine_seed=False)
    greatest = find_greatest_eclipse_time(Time(approximate_utc, scale="utc"), is_lunar=False)
    radii = RADIUS_MODELS[radius_model]
    return {
        "revision": REVISION,
        "dependencies": {package: version(package)
                         for package in ("astropy", "numpy", "scipy", "astropy-iers-data")},
        "ephemeris": "astropy-builtin",
        "radius_model": radius_model,
        "radii_km": {
            "sun": radii.sun_km,
            "central_moon": radii.central_moon_km,
            "penumbral_moon": radii.penumbral_moon_km,
        },
        "step_seconds": step_seconds,
        "date": approximate_utc[:10],
        "global_type": raw["global_type"],
        "maximum_phase": raw["maximum_phase"],
        "central": raw["central"],
        "central_interval_utc": raw["central_interval_utc"],
        "hybrid_sequence": raw["hybrid_sequence"],
        "axis_phase_transitions_utc": raw["axis_phase_transitions_utc"],
        "witnesses": dict(raw["witnesses"]),
        "searched_max_clearances_km": raw["searched_max_clearances_km"],
        "geometry_evaluations": raw["geometry_evaluations"],
        "ephemeris_batches": raw["ephemeris_batches"],
        "surface_optimizations": raw["surface_optimizations"],
        "legacy_greatest_eclipse_time": greatest.iso,
        "elapsed_seconds": perf_counter() - started,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Analyze one UTC timestamp without reference assertions")
    parser.add_argument("--step-seconds", type=float, default=120)
    parser.add_argument("--radius-model", choices=RADIUS_MODELS, default="nasa")
    parser.add_argument("--json", action="store_true", help="Include numerical phase witnesses")
    parser.add_argument("--reference-date", action="append", help="Repeatable reference UTC date")
    parser.add_argument("--check-stability", action="store_true")
    args = parser.parse_args()
    iers.conf.auto_download = False
    iers.conf.auto_max_age = None
    if args.date:
        if args.reference_date or args.check_stability:
            parser.error("--date cannot be combined with reference validation options")
        print(json.dumps(analyze(args.date, args.step_seconds, args.radius_model), indent=2))
        return 0

    references = REFERENCES
    if args.reference_date:
        requested = set(args.reference_date)
        known = {r.approximate_utc[:10] for r in REFERENCES}
        if requested - known:
            parser.error(f"Unknown reference dates: {', '.join(sorted(requested - known))}")
        references = tuple(r for r in REFERENCES if r.approximate_utc[:10] in requested)
    failures = []
    keys = ("global_type", "maximum_phase", "central", "hybrid_sequence")
    for reference in references:
        result = analyze(reference.approximate_utc, args.step_seconds, args.radius_model)
        expected_maximum = "TOTAL" if reference.global_type == "HYBRID" else reference.global_type
        passed = tuple(result[k] for k in keys) == (
            reference.global_type, expected_maximum, reference.central, reference.hybrid_sequence,
        )
        if args.check_stability:
            shifted_seed = (Time(reference.approximate_utc) + 17 * u.min).iso
            for seed, step in (
                (reference.approximate_utc, args.step_seconds / 2),
                (shifted_seed, args.step_seconds),
            ):
                repeat = analyze(seed, step, args.radius_model)
                if tuple(result[k] for k in keys) != tuple(repeat[k] for k in keys):
                    raise AssertionError(f"Unstable classification for {result['date']}")
            result["stability_checked"] = True
        print(f"{'PASS' if passed else 'FAIL'} {result['date']} "
              f"expected={reference.global_type:7} actual={result['global_type']:7} "
              f"maximum={result['maximum_phase']:7} central={result['central']}",
              file=sys.stderr if args.json else sys.stdout)
        result["reference"] = reference.source
        result["reference_verification"] = reference.verification
        if args.json:
            print(json.dumps(result))
        if not passed:
            failures.append(result["date"])
    if failures:
        raise AssertionError(f"Reference mismatches: {', '.join(failures)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
