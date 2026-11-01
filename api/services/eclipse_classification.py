"""Global solar-eclipse classification using finite-distance WGS84 shadow cones.

The numerical model follows research/validate_global_solar_eclipses.py v4. Its
catalog validation is empirical, not a proof of absence for arbitrary epochs.
"""

from dataclasses import dataclass
from collections import OrderedDict
import threading
from typing import Literal

import erfa
import numpy as np
from astropy.coordinates import EarthLocation, get_body, get_sun
from astropy.time import Time
import astropy.units as u
from scipy.optimize import brentq, minimize, minimize_scalar

MODEL_REVISION = "wgs84-finite-distance-cones-v4"
SolarGlobalType = Literal["NONE", "PARTIAL", "ANNULAR", "TOTAL", "HYBRID"]
SolarMaximumPhase = Literal["NONE", "PARTIAL", "ANNULAR", "TOTAL"]
SolarFootprintPhase = Literal["PARTIAL", "ANNULAR", "TOTAL"]
EARTH_AXES_KM = np.array([6378.137, 6378.137, 6356.752314245])
GEOCENTRIC = EarthLocation.from_geocentric(0, 0, 0, unit=u.km)
PHASE_TOLERANCE_KM = 0.001
ROOT_TOLERANCE_SECONDS = 0.001
SEARCH_HALF_WIDTH_HOURS = 4
SEARCH_STEP_SECONDS = 120

# ERFA's nominal high-accuracy model range is 1900–2100. Earlier/later
# evaluations are allowed for catalog regression, but are extrapolations.
MODEL_METADATA = {
    "revision": MODEL_REVISION,
    "ephemeris": "astropy-builtin",
    "radius_model": "NASA eclipse-prediction convention",
    "supported_epoch": ("1900-01-01 through 2100-12-31 (ERFA nominal range); "
                        "outside this range is extrapolation"),
    "latest_catalog_case": "2185-07-26",
    "limitations": "Finite catalog validation; not a certified all-history exclusion solver.",
}


@dataclass(frozen=True)
class RadiusModel:
    sun_km: float
    central_moon_km: float
    penumbral_moon_km: float


RADIUS_MODELS = {
    "repository": RadiusModel(695700., 1737.4, 1737.4),
    "nasa": RadiusModel(696000., 6378.137 * .272281, 6378.137 * .2725076),
}


@dataclass(frozen=True)
class SolarSurfaceWitness:
    phase: SolarFootprintPhase
    time_utc: str
    clearance_km: float
    sun_altitude_deg: float
    surface_point_cirs_km: tuple[float, float, float]
    angular_clearance_arcsec: float
    method: str


@dataclass(frozen=True)
class SolarEclipseClassification:
    global_type: SolarGlobalType
    maximum_phase: SolarMaximumPhase
    model_revision: str
    central: bool
    greatest_eclipse_time: Time
    size_ratio: float
    witnesses: tuple[SolarSurfaceWitness, ...]
    central_interval_utc: tuple[str, str] | None
    hybrid_sequence: str | None
    axis_phase_transitions_utc: tuple[str, ...]


class _ClassificationCache:
    def __init__(self, maximum_size=128):
        self._maximum_size = maximum_size
        self._entries = OrderedDict()
        self._lock = threading.RLock()

    def get(self, key):
        with self._lock:
            value = self._entries.get(key)
            if value is not None:
                self._entries.move_to_end(key)
            return value

    def set(self, key, value):
        with self._lock:
            self._entries[key] = value
            self._entries.move_to_end(key)
            while len(self._entries) > self._maximum_size:
                self._entries.popitem(last=False)

    def clear(self):
        with self._lock:
            self._entries.clear()


_CLASSIFICATION_CACHE = _ClassificationCache()
_CONTACT_CACHE = _ClassificationCache()
_CLASSIFICATION_LOCKS = tuple(threading.RLock() for _ in range(32))
_CONTACT_LOCKS = tuple(threading.RLock() for _ in range(32))


@dataclass
class Geometry:
    sun: np.ndarray
    moon: np.ndarray
    axis: np.ndarray
    umbral_sine: float
    penumbral_sine: float
    radii: RadiusModel

    @classmethod
    def at(cls, time, radii):
        if not time.isscalar:
            raise ValueError("Geometry.at requires a scalar time")
        return cls.at_many(time.reshape((1,)), radii)[0]

    @classmethod
    def at_many(cls, times, radii):
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
        if phase not in ("TOTAL", "ANNULAR", "PARTIAL"):
            raise ValueError(f"Unsupported phase: {phase}")

    def axis_surface(self):
        m = self.moon / EARTH_AXES_KM
        n = self.axis / EARTH_AXES_KM
        discriminant = self.axis_discriminant()
        if discriminant < 0:
            return None
        distance = (-np.dot(m, n) - np.sqrt(discriminant)) / np.dot(n, n)
        return self.moon + distance * self.axis

    def clearance(self, point, phase):
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


def refine_maxima(times, values, objective, tolerance_seconds):
    """Refine each bracketed sampled peak, not just the largest grid value."""
    maxima = []
    for index in range(1, len(times) - 1):
        if (values[index] >= max(values[index - 1], values[index + 1])
                and values[index] > min(values[index - 1], values[index + 1])):
            maximum = minimize_scalar(
                lambda seconds: -objective(float(seconds)),
                bounds=(times[index - 1], times[index + 1]),
                method="bounded", options={"xatol": tolerance_seconds},
            )
            if not maximum.success or not np.isfinite(maximum.fun):
                raise RuntimeError("Temporal footprint search failed")
            maxima.append(float(maximum.x))
    return maxima


def _analyze(approximate_utc, step_seconds=120, radius_model="nasa", *, refine_seed=True):
    epoch = (approximate_utc if isinstance(approximate_utc, Time)
             else Time(approximate_utc, scale="utc"))
    if not epoch.isscalar or not np.isfinite(epoch.jd):
        raise ValueError("A finite scalar UTC timestamp is required")
    if not np.isfinite(step_seconds) or not 0 < step_seconds <= 600:
        raise ValueError("step_seconds must be in (0, 600]")
    if radius_model not in RADIUS_MODELS:
        raise ValueError(f"Unsupported radius model: {radius_model}")
    if refine_seed:
        epoch = _greatest_eclipse_time(epoch)
    samples = np.linspace(-14400., 14400.,
                          int(np.ceil(28800 / step_seconds)) + 1)
    geometry_cache = {}
    surface_cache = {}
    radii = RADIUS_MODELS[radius_model]
    ephemeris_batches = 0

    def preload(times):
        nonlocal ephemeris_batches
        missing = [float(s) for s in times if float(s) not in geometry_cache]
        if missing:
            geometries = Geometry.at_many(epoch + np.array(missing) * u.s, radii)
            geometry_cache.update(zip(missing, geometries, strict=True))
            ephemeris_batches += 1

    def geometry(seconds):
        seconds = float(seconds)
        preload([seconds])
        return geometry_cache[seconds]

    def surface(seconds, phase):
        key = (float(seconds), phase)
        if key not in surface_cache:
            geom = geometry(seconds)
            bound = geom.clearance_upper_bound(phase)
            surface_cache[key] = ((bound, None) if bound < -PHASE_TOLERANCE_KM
                                  else geom.best_surface_clearance(phase))
        return surface_cache[key]

    preload(samples)
    discriminants = np.array([geometry(s).axis_discriminant() for s in samples])
    if discriminants[0] >= 0 or discriminants[-1] >= 0:
        raise RuntimeError("Central path extends outside the search window")

    # Maximize the discriminant, even if no coarse sample detects an intersection.
    # This catches short grazing central paths instead of calling them partial.
    peak_index = int(np.argmax(discriminants))
    if peak_index in (0, len(samples) - 1):
        raise RuntimeError("Closest approach is not bracketed")
    peak = minimize_scalar(
        lambda s: -geometry(s).axis_discriminant(),
        bounds=(samples[peak_index - 1], samples[peak_index + 1]),
        method="bounded", options={"xatol": ROOT_TOLERANCE_SECONDS},
    )
    if not peak.success or not np.isfinite(peak.fun):
        raise RuntimeError("Closest-approach search failed")
    closest_seconds = float(peak.x)
    if abs(geometry(closest_seconds).axis_margin_km()) <= PHASE_TOLERANCE_KM:
        raise RuntimeError("Indeterminate axis intersection within numerical tolerance")
    central = geometry(closest_seconds).axis_discriminant() > 0
    witnesses = {}
    witness_seconds = {}

    def retain(phase, seconds, clearance, point, method):
        if not np.isfinite(clearance):
            raise RuntimeError(f"Non-finite {phase} surface clearance")
        if point is None:
            if clearance > PHASE_TOLERANCE_KM:
                raise RuntimeError(f"Missing {phase} surface witness")
            return
        if clearance > PHASE_TOLERANCE_KM:
            geom = geometry(seconds)
            angular_margin = geom.angular_clearance(point, phase)
            altitude = geom.sun_altitude(point)
            if (not np.all(np.isfinite(point))
                    or not np.isclose(np.linalg.norm(point / EARTH_AXES_KM),
                                      1, atol=1e-8, rtol=0)
                    or not np.isfinite(angular_margin) or angular_margin <= 0
                    or not np.isfinite(altitude) or altitude < -1e-6):
                raise RuntimeError(f"Invalid {phase} surface witness")
            if phase not in witnesses or clearance > witnesses[phase]["clearance_km"]:
                witness_seconds[phase] = float(seconds)
                witnesses[phase] = {
                    "time_utc": (epoch + seconds * u.s).iso,
                    "clearance_km": float(clearance),
                    "sun_altitude_deg": altitude,
                    "surface_point_cirs_km": point.tolist(),
                    "angular_clearance_arcsec": angular_margin,
                    "method": method,
                }

    central_interval = None
    hybrid_sequence = None
    transitions = []
    # A strong-phase witness implies penumbral overlap, but not window closure.
    for seconds in (samples[0], samples[-1]):
        if surface(seconds, "PARTIAL")[0] >= -PHASE_TOLERANCE_KM:
            raise RuntimeError("Penumbral footprint extends outside the search window")
    if central:
        beginning = brentq(lambda s: geometry(s).axis_discriminant(),
                          samples[0], closest_seconds,
                          xtol=ROOT_TOLERANCE_SECONDS)
        ending = brentq(lambda s: geometry(s).axis_discriminant(),
                       closest_seconds, samples[-1],
                       xtol=ROOT_TOLERANCE_SECONDS)
        central_interval = [
            (epoch + beginning * u.s).iso, (epoch + ending * u.s).iso]
        # Explicitly inspect both limbs. A coarse
        # time grid alone can miss the ~15-second annular part of the 2013 hybrid.
        limb_offset = min(.01, (ending - beginning) / 4)
        if limb_offset <= ROOT_TOLERANCE_SECONDS:
            raise RuntimeError("Indeterminate central path within root tolerance")
        path_samples = np.unique(np.concatenate((
            samples[(samples > beginning) & (samples < ending)],
            [beginning + limb_offset, ending - limb_offset, closest_seconds],
        )))
        preload(path_samples)

        def axis_radius(seconds):
            geom = geometry(seconds)
            point = geom.axis_surface()
            if point is None:
                raise RuntimeError("Axis-surface search left the central interval")
            return geom.clearance(point, "TOTAL")

        radii_on_path = np.array([axis_radius(s) for s in path_samples])
        extra = []
        for sign in (1, -1):
            extra.extend(refine_maxima(
                path_samples, sign * radii_on_path,
                lambda seconds: sign * axis_radius(seconds), .001))
        path_samples = np.unique(np.concatenate((path_samples, extra)))
        preload(path_samples)
        phases = []
        for seconds in path_samples:
            point = geometry(seconds).axis_surface()
            if point is not None:
                phases.append("T" if axis_radius(seconds) > 0 else "A")
                for phase in ("TOTAL", "ANNULAR"):
                    retain(phase, seconds, geometry(seconds).clearance(point, phase),
                           point, "axis-surface")
        sequence = [p for i, p in enumerate(phases) if i == 0 or p != phases[i - 1]]
        if len(sequence) > 1:
            hybrid_sequence = "-".join(sequence)
            for before, after, p, q in zip(
                    path_samples[:-1], path_samples[1:], phases[:-1], phases[1:], strict=True):
                if p != q:
                    crossing = brentq(axis_radius, before, after,
                                      xtol=ROOT_TOLERANCE_SECONDS)
                    transitions.append((epoch + crossing * u.s).iso)
        search_times = np.unique(np.concatenate((
            samples,
            np.linspace(beginning - 120, beginning + 120, 9),
            np.linspace(ending - 120, ending + 120, 9),
            [closest_seconds],
        )))
    else:
        search_times = np.unique(np.concatenate((samples, [closest_seconds])))

    preload(search_times)
    searched_maxima = {}
    for phase in ("TOTAL", "ANNULAR", "PARTIAL"):
        if phase == "PARTIAL":
            for strong_phase in ("TOTAL", "ANNULAR"):
                if strong_phase in witnesses:
                    witness = witnesses[strong_phase]
                    seconds = witness_seconds[strong_phase]
                    point = np.array(witness["surface_point_cirs_km"])
                    retain("PARTIAL", seconds, geometry(seconds).clearance(point, "PARTIAL"),
                           point, "strong-phase-witness")
        if phase in witnesses:
            continue
        upper_bounds = np.array([geometry(s).clearance_upper_bound(phase) for s in search_times])
        bound_peaks = refine_maxima(
            search_times, upper_bounds,
            lambda seconds: geometry(seconds).clearance_upper_bound(phase), .01)
        phase_times = np.unique(np.concatenate((search_times, bound_peaks)))
        preload(phase_times)
        results = [surface(s, phase) for s in phase_times]
        index = max(range(len(results)), key=lambda i: results[i][0])
        seconds = float(phase_times[index])
        clearance, point = results[index]
        retain(phase, seconds, clearance, point, "surface-optimization")
        best_clearance = clearance
        # Refine every sampled local maximum, not an assumed unimodal maximum.
        for seconds in refine_maxima(
                phase_times, [r[0] for r in results],
                lambda s: surface(s, phase)[0], .01):
            clearance, point = surface(seconds, phase)
            retain(phase, seconds, clearance, point, "surface-optimization")
            best_clearance = max(best_clearance, clearance)
        searched_maxima[phase] = float(best_clearance)
        if phase not in witnesses and abs(best_clearance) <= PHASE_TOLERANCE_KM:
            raise RuntimeError(f"Indeterminate {phase} within numerical tolerance")

    if "TOTAL" in witnesses and "ANNULAR" in witnesses:
        global_type = "HYBRID"
    elif "TOTAL" in witnesses:
        global_type = "TOTAL"
    elif "ANNULAR" in witnesses:
        global_type = "ANNULAR"
    elif "PARTIAL" in witnesses:
        global_type = "PARTIAL"
    else:
        global_type = "NONE"
    if hybrid_sequence is not None and global_type != "HYBRID":
        raise RuntimeError("Indeterminate hybrid: axis transition lacks both phase witnesses")
    greatest = epoch
    legacy_geometry = Geometry.at(greatest, RADIUS_MODELS["repository"])
    sun_distance = np.linalg.norm(legacy_geometry.sun)
    moon_distance = np.linalg.norm(legacy_geometry.moon)
    legacy_radii = RADIUS_MODELS["repository"]
    size_ratio = round(np.arctan(legacy_radii.central_moon_km / moon_distance)
                       / np.arctan(legacy_radii.sun_km / sun_distance), 6)
    return {
        "global_type": global_type,
        "maximum_phase": "TOTAL" if global_type == "HYBRID" else global_type,
        "central": bool(central),
        "central_interval_utc": tuple(central_interval) if central_interval else None,
        "hybrid_sequence": hybrid_sequence,
        "axis_phase_transitions_utc": tuple(transitions),
        "witnesses": tuple(witnesses.items()),
        "size_ratio": size_ratio,
        "greatest_eclipse_time": greatest,
        "geometry_evaluations": len(geometry_cache),
        "ephemeris_batches": ephemeris_batches,
        "surface_optimizations": sum(point is not None for _, point in surface_cache.values()),
        "searched_max_clearances_km": searched_maxima,
    }


def _greatest_eclipse_time(time_obj):
    """Keep the established minimum Sun–Moon separation convention."""
    from api.services.eclipse_detection import find_greatest_eclipse_time

    return find_greatest_eclipse_time(time_obj, is_lunar=False)


def _cache_key(time_obj):
    timestamp = time_obj.utc.replicate()
    timestamp.precision = 3
    return (timestamp.iso, MODEL_REVISION)


def classify_solar_eclipse(time_obj):
    """Classify the global eclipse seeded by a scalar new-moon/syzygy time."""
    if not isinstance(time_obj, Time) or not time_obj.isscalar or not np.isfinite(time_obj.jd):
        raise ValueError("A finite scalar astropy Time is required")
    time_obj = time_obj.utc
    key = _cache_key(time_obj)
    with _CLASSIFICATION_LOCKS[hash(key) % len(_CLASSIFICATION_LOCKS)]:
        cached = _CLASSIFICATION_CACHE.get(key)
        if cached is not None:
            return cached

        from api.services.eclipse_detection import is_new_moon

        if not is_new_moon(time_obj):
            raise ValueError("Solar eclipse seed must be within 10 degrees of new moon")
        raw = _analyze(time_obj)
        witnesses = tuple(
            SolarSurfaceWitness(
                phase=phase,
                time_utc=item["time_utc"],
                clearance_km=float(item["clearance_km"]),
                sun_altitude_deg=float(item["sun_altitude_deg"]),
                surface_point_cirs_km=tuple(float(value)
                                            for value in item["surface_point_cirs_km"]),
                angular_clearance_arcsec=float(item["angular_clearance_arcsec"]),
                method=item["method"],
            )
            for phase, item in raw["witnesses"]
        )
        result = SolarEclipseClassification(
            global_type=raw["global_type"],
            maximum_phase=raw["maximum_phase"],
            model_revision=MODEL_REVISION,
            central=raw["central"],
            greatest_eclipse_time=raw["greatest_eclipse_time"],
            size_ratio=raw["size_ratio"],
            witnesses=witnesses,
            central_interval_utc=raw["central_interval_utc"],
            hybrid_sequence=raw["hybrid_sequence"],
            axis_phase_transitions_utc=raw["axis_phase_transitions_utc"],
        )
        _CLASSIFICATION_CACHE.set(key, result)
        return result


def clear_solar_eclipse_classification_cache():
    """Clear the bounded, thread-safe global-classification cache."""
    _CLASSIFICATION_CACHE.clear()
    _CONTACT_CACHE.clear()


def _contact_pair(epoch, phases, radius_model="nasa", step_seconds=SEARCH_STEP_SECONDS,
                  search_window_hours=SEARCH_HALF_WIDTH_HOURS):
    if not np.isfinite(search_window_hours) or not 0 < search_window_hours <= 24:
        raise ValueError("search_window_hours must be in (0, 24]")
    radii = RADIUS_MODELS[radius_model]
    samples = np.linspace(
        -search_window_hours * 3600,
        search_window_hours * 3600,
        int(np.ceil(2 * search_window_hours * 3600 / step_seconds)) + 1,
    )
    geometries = {}
    margins = {}
    geometries.update(zip(
        (float(seconds) for seconds in samples),
        Geometry.at_many(epoch + samples * u.s, radii),
        strict=True,
    ))

    def geometry(seconds):
        seconds = float(seconds)
        if seconds not in geometries:
            geometries[seconds] = Geometry.at(epoch + seconds * u.s, radii)
        return geometries[seconds]

    def phase_margin(seconds, phase):
        key = (float(seconds), phase)
        if key not in margins:
            geom = geometry(seconds)
            bound = geom.clearance_upper_bound(phase)
            margins[key] = (bound if bound < -PHASE_TOLERANCE_KM
                            else geom.best_surface_clearance(phase)[0])
        return margins[key]

    def combined_margin(seconds):
        return max(phase_margin(seconds, phase) for phase in phases)

    bounds = {
        float(s): max(geometry(s).clearance_upper_bound(phase) for phase in phases)
        for s in samples
    }
    bound_peaks = refine_maxima(
        samples, [bounds[float(s)] for s in samples],
        lambda s: max(geometry(s).clearance_upper_bound(phase) for phase in phases),
        0.01,
    )
    times = np.unique(np.concatenate((samples, bound_peaks)))
    values = [combined_margin(s) for s in times]
    for peak in refine_maxima(times, values, combined_margin, 0.01):
        times = np.append(times, peak)
    times = np.unique(times)
    values = [combined_margin(s) for s in times]
    if values[0] >= -PHASE_TOLERANCE_KM or values[-1] >= -PHASE_TOLERANCE_KM:
        raise RuntimeError("Global solar contact interval extends outside the search window")
    peak_value = max(values)
    if abs(peak_value) <= PHASE_TOLERANCE_KM:
        raise RuntimeError("Indeterminate global solar contact within numerical tolerance")
    if peak_value < 0:
        return None, None

    crossings = []
    for left, right, left_value, right_value in zip(
            times[:-1], times[1:], values[:-1], values[1:], strict=True):
        if (left_value < 0 <= right_value) or (left_value >= 0 > right_value):
            try:
                crossings.append(brentq(
                    combined_margin, float(left), float(right),
                    xtol=ROOT_TOLERANCE_SECONDS,
                ))
            except (ValueError, RuntimeError) as error:
                raise RuntimeError("Unable to bracket global solar contact crossing") from error
    if len(crossings) < 2:
        raise RuntimeError("Global solar contact crossings were not bracketed")
    return (epoch + crossings[0] * u.s).iso, (epoch + crossings[-1] * u.s).iso


def calculate_global_solar_contacts(
    time_obj_or_analysis, search_window_hours=SEARCH_HALF_WIDTH_HOURS
):
    """Return first/last daylight penumbral and total/annular footprint crossings.

    Accepts either a scalar syzygy-seed ``Time`` or a prior
    ``SolarEclipseClassification``. Crossings are finite-distance shadow-cone
    footprint contacts on daylight WGS84, not shadow-axis roots.
    """
    if not np.isfinite(search_window_hours) or not 0 < search_window_hours <= 24:
        raise ValueError("search_window_hours must be in (0, 24]")
    analysis = (time_obj_or_analysis
                if isinstance(time_obj_or_analysis, SolarEclipseClassification)
                else classify_solar_eclipse(time_obj_or_analysis))
    empty = {
        "eclipse_begins": None,
        "central_phase_begins": None,
        "central_phase_ends": None,
        "eclipse_ends": None,
    }
    if analysis.model_revision != MODEL_REVISION:
        raise ValueError(
            "Solar contact calculation requires the current classification model revision"
        )
    if analysis.global_type == "NONE":
        return empty
    key = (*_cache_key(analysis.greatest_eclipse_time), analysis.global_type, search_window_hours)
    with _CONTACT_LOCKS[hash(key) % len(_CONTACT_LOCKS)]:
        cached = _CONTACT_CACHE.get(key)
        if cached is not None:
            return dict(cached)
        penumbral = _contact_pair(
            analysis.greatest_eclipse_time, ("PARTIAL",),
            search_window_hours=search_window_hours)
        if None in penumbral:
            raise RuntimeError("Confirmed solar eclipse has no resolved penumbral contacts")
        if analysis.global_type in ("TOTAL", "ANNULAR", "HYBRID"):
            central = _contact_pair(
                analysis.greatest_eclipse_time, ("TOTAL", "ANNULAR"),
                search_window_hours=search_window_hours)
            if None in central:
                raise RuntimeError("Confirmed strong solar phase has no resolved global contacts")
        else:
            central = (None, None)
        contacts = {
            "eclipse_begins": penumbral[0],
            "central_phase_begins": central[0],
            "central_phase_ends": central[1],
            "eclipse_ends": penumbral[1],
        }
        _CONTACT_CACHE.set(key, tuple(contacts.items()))
        return contacts


SOLAR_MODEL_REVISION = MODEL_REVISION
clear_classification_cache = clear_solar_eclipse_classification_cache
