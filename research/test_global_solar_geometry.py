# /// script
# requires-python = ">=3.12"
# dependencies = ["astropy", "numpy", "scipy"]
# ///
"""Small synthetic checks, without ephemeris downloads or HTTP API startup."""

import unittest
from unittest.mock import patch

import numpy as np
from astropy.time import Time
import astropy.units as u
from astropy.utils import iers

from scipy.optimize import brentq

from validate_global_solar_eclipses import (
    EARTH_AXES_KM, Geometry, RADIUS_MODELS, RadiusModel, analyze, refine_maxima,
)


class GlobalSolarGeometryTests(unittest.TestCase):
    def geometry(self, distance, offset=0., rotation=None):
        sun = np.array([149600000., 0., 0.])
        moon = np.array([distance, offset, 0.])
        if rotation is not None:
            sun = rotation @ sun
            moon = rotation @ moon
        return Geometry.from_vectors(sun, moon, RADIUS_MODELS["nasa"])

    def assert_witness(self, geometry, phase):
        margin, point = geometry.best_surface_clearance(phase)
        self.assertGreater(margin, 0)
        self.assertAlmostEqual(np.linalg.norm(point / EARTH_AXES_KM), 1, places=8)
        self.assertGreaterEqual(geometry.sun_altitude(point), -1e-6)
        self.assertGreater(geometry.angular_clearance(point, phase), 0)
        return point

    def test_axis_uses_near_surface(self):
        geometry = self.geometry(360000)
        np.testing.assert_allclose(geometry.axis_surface(), [EARTH_AXES_KM[0], 0, 0],
                                   atol=1e-7)
        self.assert_witness(geometry, "TOTAL")

    def test_annular_footprint(self):
        self.assert_witness(self.geometry(400000), "ANNULAR")

    def test_noncentral_total_has_no_axis_intersection(self):
        geometry = self.geometry(360000, 6410)
        self.assertIsNone(geometry.axis_surface())
        self.assert_witness(geometry, "TOTAL")

    def test_noncentral_annular_has_no_axis_intersection(self):
        geometry = self.geometry(400000, 6420)
        self.assertIsNone(geometry.axis_surface())
        self.assert_witness(geometry, "ANNULAR")

    def test_partial_does_not_imply_total_or_annular(self):
        geometry = self.geometry(400000, 6800)
        self.assert_witness(geometry, "PARTIAL")
        for phase in ("TOTAL", "ANNULAR"):
            self.assertLess(geometry.best_surface_clearance(phase)[0], 0)

    def test_local_partial_can_belong_to_a_global_total(self):
        geometry = self.geometry(360000)
        self.assert_witness(geometry, "TOTAL")
        equatorial_radius = EARTH_AXES_KM[0]
        point = np.array([np.sqrt(equatorial_radius ** 2 - 1000 ** 2), 1000., 0.])
        self.assertGreater(geometry.angular_clearance(point, "PARTIAL"), 0)
        self.assertLess(geometry.angular_clearance(point, "TOTAL"), 0)
        self.assertLess(geometry.angular_clearance(point, "ANNULAR"), 0)

    def test_none_has_no_surface_footprint(self):
        geometry = self.geometry(400000, 12000)
        for phase in ("TOTAL", "ANNULAR", "PARTIAL"):
            self.assertLess(geometry.best_surface_clearance(phase)[0], 0)

    def test_night_side_antumbra_is_not_a_hybrid(self):
        geometry = self.geometry(375000)
        far_surface = np.array([-EARTH_AXES_KM[0], 0., 0.])
        self.assertGreater(geometry.clearance(far_surface, "ANNULAR"), 0)
        self.assertLess(geometry.sun_altitude(far_surface), 0)
        self.assert_witness(geometry, "TOTAL")
        self.assertLess(geometry.best_surface_clearance("ANNULAR")[0], 0)

    def test_polar_alignment_is_finite(self):
        rotation = np.array([[0., 0., -1.], [0., 1., 0.], [1., 0., 0.]])
        point = self.assert_witness(self.geometry(360000, rotation=rotation), "TOTAL")
        self.assertTrue(np.all(np.isfinite(point)))

    def test_longitude_rotation_preserves_global_clearance(self):
        angle = .73
        rotation = np.array([[np.cos(angle), -np.sin(angle), 0.],
                             [np.sin(angle), np.cos(angle), 0.], [0., 0., 1.]])
        for phase, distance, offset in (
            ("TOTAL", 360000, 6410), ("ANNULAR", 400000, 6420),
        ):
            original = self.geometry(distance, offset)
            rotated = self.geometry(distance, offset, rotation)
            self.assertAlmostEqual(original.best_surface_clearance(phase)[0],
                                   rotated.best_surface_clearance(phase)[0], places=5)

    def test_cone_tangency_transitions_between_strong_and_partial(self):
        for phase, distance in (("TOTAL", 360000), ("ANNULAR", 400000)):
            with self.subTest(phase=phase):
                offset = brentq(
                    lambda y: self.geometry(distance, y).best_surface_clearance(phase)[0],
                    6400, 6800, xtol=1e-6)
                touching = self.geometry(distance, offset)
                self.assertIsNone(touching.axis_surface())
                self.assertAlmostEqual(touching.best_surface_clearance(phase)[0],
                                       0, places=5)
                self.assertGreater(self.geometry(distance, offset - .01)
                                   .best_surface_clearance(phase)[0], 0)
                outside = self.geometry(distance, offset + .01)
                self.assertLess(outside.best_surface_clearance(phase)[0], 0)
                self.assert_witness(outside, "PARTIAL")

    def test_invalid_input_does_not_return_none(self):
        for step in (0, -1, 601, np.nan, np.inf):
            with self.subTest(step=step), self.assertRaises(ValueError):
                analyze("2023-04-20 04:17", step_seconds=step)
        with self.assertRaises(ValueError):
            analyze("2023-04-20 04:17", radius_model="unknown")
        for moon in ([0., 0., 0.], [np.nan, 0., 0.], [1., 2.]):
            with self.subTest(moon=moon), self.assertRaises(ValueError):
                Geometry.from_vectors(np.array([0., 0., 0.]), moon,
                                      RADIUS_MODELS["nasa"])

    def test_surface_optimizer_failure_is_explicit(self):
        with patch("api.services.eclipse_classification.minimize") as optimizer:
            optimizer.return_value.success = False
            with self.assertRaisesRegex(RuntimeError, "did not converge"):
                self.geometry(360000).best_surface_clearance("TOTAL")

    def test_unsupported_phase_is_explicit(self):
        geometry = self.geometry(360000)
        point = np.array([6378.137, 0., 0.])
        for method, args in (
            (geometry.clearance, (point, "HYBRID")),
            (geometry.angular_clearance, (point, "HYBRID")),
            (geometry.clearance_upper_bound, ("HYBRID",)),
            (geometry.best_surface_clearance, ("HYBRID",)),
        ):
            with self.subTest(method=method.__name__), self.assertRaisesRegex(
                    ValueError, "Unsupported phase"):
                method(*args)

    def test_spatial_bound_contains_clearance_on_entire_ellipsoid(self):
        random = np.random.default_rng(275)
        points = random.normal(size=(200, 3))
        points = EARTH_AXES_KM * points / np.linalg.norm(points, axis=1)[:, None]
        for distance, offset in ((360000, 6410), (375000, 0), (400000, 6420), (400000, 12000)):
            geometry = self.geometry(distance, offset)
            for phase in ("TOTAL", "ANNULAR", "PARTIAL"):
                bound = geometry.clearance_upper_bound(phase)
                for point in points:
                    self.assertLessEqual(geometry.clearance(point, phase), bound + 1e-8)
                self.assertLessEqual(geometry.best_surface_clearance(phase)[0], bound + 1e-8)

    def test_vectorized_ephemeris_matches_scalar(self):
        times = Time(["1986-10-03 19:06", "2023-04-20 04:17"], scale="utc")
        with iers.conf.set_temp("auto_download", False):
            batched = Geometry.at_many(times, RADIUS_MODELS["nasa"])
            for time, geometry in zip(times, batched, strict=True):
                scalar = Geometry.at(time, RADIUS_MODELS["nasa"])
                np.testing.assert_allclose(geometry.sun, scalar.sun, atol=1e-7, rtol=0)
                np.testing.assert_allclose(geometry.moon, scalar.moon, atol=1e-7, rtol=0)
                self.assertAlmostEqual(geometry.axis_discriminant(),
                                       scalar.axis_discriminant(), places=15)

    def test_invalid_radii_and_earth_intersections_are_explicit(self):
        for radii in (RadiusModel(np.inf, 1737., 1737.),
                      RadiusModel(696000., 1737., 1700.)):
            with self.assertRaises(ValueError):
                Geometry.from_vectors([149600000., 0., 0.], [360000., 0., 0.], radii)
        for sun, moon in (([100., 0., 0.], [360000., 0., 0.]),
                          ([149600000., 0., 0.], [6000., 0., 0.])):
            with self.assertRaises(ValueError):
                Geometry.from_vectors(sun, moon, RADIUS_MODELS["nasa"])

    def synthetic_ephemeris(self, times, radii, offset=6340., centre=83.):
        seconds = (times - Time("2023-04-20 04:17", scale="utc")).to_value(u.s)
        return [Geometry.from_vectors([149600000., 0., 0.],
                                      [360000., offset, 5 * (s - centre)], radii)
                for s in seconds]

    def test_short_central_interval_between_coarse_samples(self):
        with patch("validate_global_solar_eclipses.Geometry.at_many",
                   side_effect=self.synthetic_ephemeris), patch(
                       "validate_global_solar_eclipses.find_greatest_eclipse_time",
                       side_effect=lambda epoch, is_lunar: epoch):
            result = analyze("2023-04-20 04:17", step_seconds=600)
        self.assertTrue(result["central"])
        self.assertEqual(result["global_type"], "TOTAL")
        beginning, ending = [Time(t) for t in result["central_interval_utc"]]
        self.assertLess((ending - beginning).to_value(u.s), 600)
        self.assertGreater((ending - beginning).to_value(u.s), 0)

    def test_positive_footprint_at_window_boundary_is_explicit(self):
        def slow_ephemeris(times, radii):
            return [self.geometry(360000) for _ in times]

        with patch("validate_global_solar_eclipses.Geometry.at_many",
                   side_effect=slow_ephemeris), self.assertRaisesRegex(
                       RuntimeError, "outside the search window"):
            analyze("2023-04-20 04:17")

    def test_temporal_optimizer_failure_and_nonfinite_success_are_explicit(self):
        for success, value in ((False, 0.), (True, np.nan)):
            with patch("api.services.eclipse_classification.minimize_scalar") as optimizer:
                optimizer.return_value.success = success
                optimizer.return_value.fun = value
                with self.assertRaisesRegex(RuntimeError, "Temporal footprint search failed"):
                    refine_maxima([0, 1, 2], [0, 1, 0], lambda s: s, .001)

    def test_nonfinite_surface_optimizer_success_is_rejected(self):
        with patch("api.services.eclipse_classification.minimize") as optimizer:
            optimizer.return_value.success = True
            optimizer.return_value.x = np.array([np.nan, 0.])
            with self.assertRaisesRegex(RuntimeError, "did not converge"):
                self.geometry(360000).best_surface_clearance("TOTAL")

    def test_near_axis_tangency_is_not_silently_noncentral(self):
        offset = brentq(lambda y: self.geometry(360000, y).axis_margin_km(),
                        6300, 6500, xtol=1e-8)

        def tangent_ephemeris(times, radii):
            return self.synthetic_ephemeris(times, radii, offset=offset)

        with patch("validate_global_solar_eclipses.Geometry.at_many",
                   side_effect=tangent_ephemeris), self.assertRaisesRegex(
                       RuntimeError, "Indeterminate axis intersection"):
            analyze("2023-04-20 04:17")

    def test_invalid_positive_witness_is_explicit(self):
        original = Geometry.best_surface_clearance

        def noncentral_ephemeris(times, radii):
            return self.synthetic_ephemeris(times, radii, offset=6410.)

        def invalid_surface(geometry, phase):
            margin, point = original(geometry, phase)
            return margin, point * 1.000001

        with patch("validate_global_solar_eclipses.Geometry.at_many",
                   side_effect=noncentral_ephemeris), patch(
                       "validate_global_solar_eclipses.Geometry.best_surface_clearance",
                       new=invalid_surface), self.assertRaisesRegex(
                           RuntimeError, "Invalid TOTAL surface witness"):
            analyze("2023-04-20 04:17", step_seconds=600)


if __name__ == "__main__":
    unittest.main()
