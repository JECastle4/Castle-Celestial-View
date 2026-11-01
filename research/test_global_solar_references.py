# /// script
# requires-python = ">=3.12"
# dependencies = ["astropy", "numpy", "scipy"]
# ///
"""Exact solar catalog regression and sampling/seed sensitivity checks.

Run with: uv run research/test_global_solar_references.py
This validates classifications, not published timings or geographic paths.
"""
import unittest

import numpy as np
from astropy.time import Time
import astropy.units as u
from astropy.utils import iers

from validate_global_solar_eclipses import (
    EARTH_AXES_KM, PHASE_TOLERANCE_KM, Geometry, RADIUS_MODELS, REFERENCES, analyze,
)


class SolarReferenceTests(unittest.TestCase):
    def assert_reference(self, reference, seed, step):
        result = analyze(seed, step)
        self.assertEqual(result["global_type"], reference.global_type)
        self.assertEqual(result["maximum_phase"],
                         "TOTAL" if reference.global_type == "HYBRID" else reference.global_type)
        self.assertEqual(result["central"], reference.central)
        self.assertEqual(result["hybrid_sequence"], reference.hybrid_sequence)
        self.assertEqual(len(result["axis_phase_transitions_utc"]),
                         0 if reference.hybrid_sequence is None
                         else len(reference.hybrid_sequence.split("-")) - 1)
        required = {
            "HYBRID": {"TOTAL", "ANNULAR", "PARTIAL"},
            "TOTAL": {"TOTAL", "PARTIAL"},
            "ANNULAR": {"ANNULAR", "PARTIAL"},
            "PARTIAL": {"PARTIAL"},
            "NONE": set(),
        }[reference.global_type]
        self.assertEqual(set(result["witnesses"]), required)
        for phase, witness in result["witnesses"].items():
            self.assertGreater(witness["clearance_km"], PHASE_TOLERANCE_KM)
            point = np.array(witness["surface_point_cirs_km"])
            # Re-query the ephemeris at the serialized (millisecond) timestamp.
            geom = Geometry.at(Time(witness["time_utc"], scale="utc"), RADIUS_MODELS["nasa"])
            self.assertAlmostEqual(np.linalg.norm(point / EARTH_AXES_KM), 1, places=8)
            self.assertGreater(geom.angular_clearance(point, phase), 0)
            self.assertGreaterEqual(geom.sun_altitude(point), -1e-6)
        if reference.central:
            start, end = [Time(t, scale="utc") for t in result["central_interval_utc"]]
            self.assertLess(start, end)
            for timestamp in result["axis_phase_transitions_utc"]:
                self.assertLess(start, Time(timestamp, scale="utc"))
                self.assertLess(Time(timestamp, scale="utc"), end)
        else:
            self.assertIsNone(result["central_interval_utc"])
        if reference.global_type == "NONE":
            self.assertEqual(result["surface_optimizations"], 0)
        if reference.approximate_utc[:10] == "2013-11-03":
            annular_seconds = (Time(result["axis_phase_transitions_utc"][0], scale="utc")
                               - Time(result["central_interval_utc"][0], scale="utc")).to_value(u.s)
            self.assertGreater(annular_seconds, 10)
            self.assertLess(annular_seconds, 20)
        return result

    def test_full_solar_catalog_and_stability(self):
        self.assertEqual(len(REFERENCES), 21)
        with iers.conf.set_temp("auto_download", False), iers.conf.set_temp("auto_max_age", None):
            for reference in REFERENCES:
                baseline = None
                for step, offset_seconds in ((120, 0), (60, 0), (600, -1020), (120, 91)):
                    with self.subTest(date=reference.approximate_utc[:10],
                                      step=step, offset_seconds=offset_seconds):
                        seed = (Time(reference.approximate_utc, scale="utc")
                                + offset_seconds * u.s).iso
                        result = self.assert_reference(reference, seed, step)
                        if baseline is None:
                            baseline = result
                        for key in ("central_interval_utc", "axis_phase_transitions_utc"):
                            for original, repeated in zip(
                                    baseline[key] or [], result[key] or [], strict=True):
                                difference = (Time(original, scale="utc")
                                              - Time(repeated, scale="utc")).to_value(u.s)
                                self.assertLess(abs(difference), .02)


if __name__ == "__main__":
    unittest.main()
