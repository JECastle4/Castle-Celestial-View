"""Finite-distance Sun–Moon shadow geometry on the daylight WGS84 surface."""

from dataclasses import dataclass
from typing import Literal

import erfa
import numpy as np
from astropy.coordinates import EarthLocation, get_body, get_sun
import astropy.units as u
from scipy.optimize import minimize

SolarFootprintPhase = Literal["PARTIAL", "ANNULAR", "TOTAL"]
EARTH_AXES_KM = np.array([6378.137, 6378.137, 6356.752314245])
GEOCENTRIC = EarthLocation.from_geocentric(0, 0, 0, unit=u.km)


@dataclass(frozen=True)
class RadiusModel:
    """Solar and lunar radii in kilometres for one prediction convention."""

    sun_km: float
    central_moon_km: float
    penumbral_moon_km: float


RADIUS_MODELS = {
    "repository": RadiusModel(695700., 1737.4, 1737.4),
    "nasa": RadiusModel(696000., 6378.137 * .272281, 6378.137 * .2725076),
}


@dataclass
class Geometry:
    """Apparent CIRS body vectors and their finite-distance shadow cones."""

    sun: np.ndarray
    moon: np.ndarray
    axis: np.ndarray
    umbral_sine: float
    penumbral_sine: float
    radii: RadiusModel

    @classmethod
    def at(cls, time, radii):
        """Evaluate shadow geometry at a scalar Astropy time."""
        if not time.isscalar:
            raise ValueError("Geometry.at requires a scalar time")
        return cls.at_many(time.reshape((1,)), radii)[0]

    @classmethod
    def at_many(cls, times, radii):
        """Batch ephemeris evaluation for a one-dimensional time array."""
        if times.ndim != 1:
            raise ValueError("Geometry.at_many requires one-dimensional times")
        # Rotate both apparent GCRS vectors to the celestial intermediate frame.
        # Its z axis is Earth's instantaneous pole. Longitude rotation is
        # unnecessary for an axisymmetric ellipsoid and global-only analysis.
        rotation = erfa.c2i06a(times.tt.jd1, times.tt.jd2)
        sun = np.einsum("nij,jn->ni", rotation, get_sun(times).cartesian.xyz.to_value(u.km))
        moon = np.einsum("nij,jn->ni", rotation, get_body(
            "moon", times, location=GEOCENTRIC
        ).cartesian.xyz.to_value(u.km))
        return [cls.from_vectors(s, m, radii) for s, m in zip(sun, moon, strict=True)]

    @classmethod
    def from_vectors(cls, sun, moon, radii):
        """Construct tangent cones from finite, non-intersecting body vectors."""
        sun = np.asarray(sun, dtype=float)
        moon = np.asarray(moon, dtype=float)
        if (sun.shape != (3,) or moon.shape != (3,)
                or not np.all(np.isfinite(sun)) or not np.all(np.isfinite(moon))):
            raise ValueError("Sun and Moon must be finite three-dimensional vectors")
        difference = moon - sun
        distance = np.linalg.norm(difference)
        if (not np.all(np.isfinite(
                [radii.sun_km, radii.central_moon_km, radii.penumbral_moon_km]))
                or not 0 < radii.central_moon_km <= radii.penumbral_moon_km < radii.sun_km
                or distance <= radii.sun_km + radii.penumbral_moon_km
                or np.linalg.norm(sun) <= radii.sun_km + max(EARTH_AXES_KM)
                or np.linalg.norm(moon) <= max(
                    radii.central_moon_km, radii.penumbral_moon_km) + max(EARTH_AXES_KM)):
            raise ValueError("Invalid radii or intersecting Sun/Moon spheres")
        return cls(sun, moon, difference / distance,
                   (radii.sun_km - radii.central_moon_km) / distance,
                   (radii.sun_km + radii.penumbral_moon_km) / distance, radii)

    def axis_discriminant(self):
        """Return the line/ellipsoid discriminant; positive means intersection."""
        m = self.moon / EARTH_AXES_KM
        n = self.axis / EARTH_AXES_KM
        foot = m - n * (np.dot(m, n) / np.dot(n, n))
        return float(np.dot(n, n) * (1 - np.dot(foot, foot)))

    def axis_margin_km(self):
        """Scaled-ellipsoid axis margin, used only to flag numerical tangency."""
        m = self.moon / EARTH_AXES_KM
        n = self.axis / EARTH_AXES_KM
        foot = m - n * (np.dot(m, n) / np.dot(n, n))
        return float((1 - np.linalg.norm(foot)) * min(EARTH_AXES_KM))

    def clearance_upper_bound(self, phase):
        """Conservative spatial bound using a sphere containing the ellipsoid."""
        self.validate_phase(phase)
        along = -np.dot(self.moon, self.axis)
        foot = self.moon + along * self.axis
        sine = self.penumbral_sine if phase == "PARTIAL" else self.umbral_sine
        cosine = np.sqrt(1 - sine ** 2)
        if phase == "PARTIAL":
            radius = (self.radii.penumbral_moon_km + along * sine) / cosine
        else:
            radius = (self.radii.central_moon_km - along * sine) / cosine
            if phase == "ANNULAR":
                radius = -radius
        earth_radius = max(EARTH_AXES_KM)
        return float(radius + earth_radius * sine / cosine
                     - max(0., np.linalg.norm(foot) - earth_radius))

    @staticmethod
    def validate_phase(phase):
        """Reject phases without a corresponding solar shadow footprint."""
        if phase not in ("TOTAL", "ANNULAR", "PARTIAL"):
            raise ValueError(f"Unsupported phase: {phase}")

    def axis_surface(self):
        """Return the near axis/ellipsoid intersection, or None for an axis miss."""
        m = self.moon / EARTH_AXES_KM
        n = self.axis / EARTH_AXES_KM
        discriminant = self.axis_discriminant()
        if discriminant < 0:
            return None
        distance = (-np.dot(m, n) - np.sqrt(discriminant)) / np.dot(n, n)
        return self.moon + distance * self.axis

    def clearance(self, point, phase):
        """Return signed cone clearance in kilometres at a surface point."""
        self.validate_phase(phase)
        offset = point - self.moon
        distance = np.dot(offset, self.axis)
        transverse = np.linalg.norm(offset - distance * self.axis)
        if phase == "PARTIAL":
            radius = ((self.radii.penumbral_moon_km + distance * self.penumbral_sine)
                      / np.sqrt(1 - self.penumbral_sine ** 2))
        else:
            radius = ((self.radii.central_moon_km - distance * self.umbral_sine)
                      / np.sqrt(1 - self.umbral_sine ** 2))
            if phase == "ANNULAR":
                radius = -radius
        return float(radius - transverse)

    def angular_clearance(self, point, phase):
        """Independent apparent-disk overlap check at a retained surface point."""
        self.validate_phase(phase)
        sun = self.sun - point
        moon = self.moon - point
        sun_distance = np.linalg.norm(sun)
        moon_distance = np.linalg.norm(moon)
        separation = np.arctan2(np.linalg.norm(np.cross(sun, moon)),
                                np.dot(sun, moon))
        sun_radius = np.arcsin(self.radii.sun_km / sun_distance)
        lunar_radius = (self.radii.penumbral_moon_km if phase == "PARTIAL"
                        else self.radii.central_moon_km)
        moon_radius = np.arcsin(lunar_radius / moon_distance)
        if phase == "TOTAL":
            margin = moon_radius - sun_radius - separation
        elif phase == "ANNULAR":
            margin = sun_radius - moon_radius - separation
        else:
            margin = sun_radius + moon_radius - separation
        return float(np.degrees(margin) * 3600)

    def sun_altitude(self, point):
        """Return solar altitude in degrees relative to the ellipsoid normal."""
        normal = point / EARTH_AXES_KM ** 2
        direction = self.sun - point
        sine = np.dot(normal, direction) / (
            np.linalg.norm(normal) * np.linalg.norm(direction))
        return float(np.degrees(np.arcsin(np.clip(sine, -1, 1))))

    def best_surface_clearance(self, phase):
        """Find a daylight-surface witness, including when the axis misses Earth.

        Optimize on the ellipsoid itself, never its interior or the night side.
        The scaled sphere's daylight cap has a simple angular parameterization.
        Multiple starts and convergence checking are deliberate research safeguards,
        not a proof of global optimization for arbitrary eclipse geometries.
        """
        self.validate_phase(phase)
        g = self.sun / EARTH_AXES_KM
        daylight_axis = g / np.linalg.norm(g)
        tangent = np.cross(
            daylight_axis, np.eye(3)[np.argmin(np.abs(daylight_axis))])
        tangent /= np.linalg.norm(tangent)
        bitangent = np.cross(daylight_axis, tangent)
        horizon = np.arccos(1 / np.linalg.norm(g))

        def point_at(angles):
            theta, phi = angles
            unit = (daylight_axis * np.cos(theta)
                    + np.sin(theta) * (
                        tangent * np.cos(phi) + bitangent * np.sin(phi)))
            return EARTH_AXES_KM * unit

        def angles_at(point):
            unit = point / EARTH_AXES_KM
            length = np.linalg.norm(unit)
            if length < 1e-12:
                return (0., 0.)
            unit /= length
            return (float(np.arccos(np.clip(np.dot(unit, daylight_axis), -1, 1))),
                    float(np.arctan2(np.dot(unit, bitangent), np.dot(unit, tangent))))

        # Closest approach of the shadow axis gives a useful grazing-eclipse seed.
        m = self.moon / EARTH_AXES_KM
        n = self.axis / EARTH_AXES_KM
        distance = -np.dot(m, n) / np.dot(n, n)
        foot = self.moon + distance * self.axis
        theta, phi = angles_at(foot)
        seeds = [(min(theta, horizon), phi), (horizon * .98, phi),
                 (horizon * .75, phi), (horizon * .5, phi),
                 (horizon * .75, phi - np.pi / 2),
                 (horizon * .75, phi + np.pi / 2)]
        axis_point = self.axis_surface()
        if axis_point is not None and self.sun_altitude(axis_point) >= 0:
            seeds.append(angles_at(axis_point))

        candidates = [(self.clearance(point_at(seed), phase), point_at(seed))
                      for seed in seeds]
        converged = False
        for seed in seeds:
            solution = minimize(
                lambda angles: -self.clearance(point_at(angles), phase),
                seed, method="Nelder-Mead",
                bounds=[(0., horizon), (phi - np.pi, phi + np.pi)],
                options={"xatol": 1e-10, "fatol": 1e-7, "maxiter": 1500},
            )
            if solution.success and np.all(np.isfinite(solution.x)) and np.isfinite(solution.fun):
                converged = True
                point = point_at(solution.x)
                candidates.append((self.clearance(point, phase), point))
        if not converged:
            raise RuntimeError(f"Surface optimizer did not converge for {phase}")
        return max(candidates, key=lambda candidate: candidate[0])
