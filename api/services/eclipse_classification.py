"""Global solar-eclipse classification using finite-distance WGS84 shadow cones.

The numerical model follows research/validate_global_solar_eclipses.py v4. Its
catalog validation is empirical, not a proof of absence for arbitrary epochs.
"""

from dataclasses import dataclass
from collections import OrderedDict
import threading
from typing import Literal

import numpy as np
from astropy.time import Time
import astropy.units as u
from scipy.optimize import brentq, minimize_scalar
from api.services import eclipse_ephemeris
from api.services.eclipse_geometry import (
    EARTH_AXES_KM,
    GEOCENTRIC,
    RADIUS_MODELS,
    Geometry,
    RadiusModel,
    SolarFootprintPhase,
)

__all__ = [
    "EARTH_AXES_KM",
    "GEOCENTRIC",
    "Geometry",
    "MODEL_METADATA",
    "MODEL_REVISION",
    "PHASE_TOLERANCE_KM",
    "RADIUS_MODELS",
    "ROOT_TOLERANCE_SECONDS",
    "RadiusModel",
    "SOLAR_MODEL_REVISION",
    "SEARCH_HALF_WIDTH_HOURS",
    "SEARCH_STEP_SECONDS",
    "SolarEclipseClassification",
    "SolarCentralPath",
    "SolarFootprintPhase",
    "SolarGlobalType",
    "SolarMaximumPhase",
    "SolarSurfaceWitness",
    "calculate_global_solar_contacts",
    "classify_solar_eclipse",
    "clear_classification_cache",
    "clear_solar_eclipse_classification_cache",
    "refine_maxima",
]

MODEL_REVISION = "wgs84-finite-distance-cones-v4"
SolarGlobalType = Literal["NONE", "PARTIAL", "ANNULAR", "TOTAL", "HYBRID"]
SolarMaximumPhase = Literal["NONE", "PARTIAL", "ANNULAR", "TOTAL"]
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
class SolarSurfaceWitness:
    """Validated daylight-surface evidence for one eclipse phase."""

    phase: SolarFootprintPhase
    time_utc: str
    clearance_km: float
    sun_altitude_deg: float
    surface_point_cirs_km: tuple[float, float, float]
    angular_clearance_arcsec: float
    method: str


@dataclass(frozen=True)
class SolarCentralPath:
    """Shadow-axis diagnostics, distinct from global footprint contacts."""

    central: bool
    central_interval_utc: tuple[str, str] | None
    hybrid_sequence: str | None
    axis_phase_transitions_utc: tuple[str, ...]


@dataclass(frozen=True)
class SolarEclipseClassification:
    """Whole-event classification, witnesses and central-path diagnostics."""

    global_type: SolarGlobalType
    maximum_phase: SolarMaximumPhase
    model_revision: str
    greatest_eclipse_time: Time
    size_ratio: float
    witnesses: tuple[SolarSurfaceWitness, ...]
    central_path: SolarCentralPath


class _ClassificationCache:
    """Thread-safe bounded LRU storage for classification and contact results."""

    def __init__(self, maximum_size=128):
        self._maximum_size = maximum_size
        self._entries = OrderedDict()
        self._lock = threading.RLock()

    def get(self, key):
        """Retrieve an entry and mark it as recently used."""
        with self._lock:
            value = self._entries.get(key)
            if value is not None:
                self._entries.move_to_end(key)
            return value

    def set(self, key, value):
        """Store an entry, evicting the least recently used when full."""
        with self._lock:
            self._entries[key] = value
            self._entries.move_to_end(key)
            while len(self._entries) > self._maximum_size:
                self._entries.popitem(last=False)

    def clear(self):
        """Remove all retained entries."""
        with self._lock:
            self._entries.clear()


_CLASSIFICATION_CACHE = _ClassificationCache()
_CONTACT_CACHE = _ClassificationCache()
_CLASSIFICATION_LOCKS = tuple(threading.RLock() for _ in range(32))
_CONTACT_LOCKS = tuple(threading.RLock() for _ in range(32))


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


class SolarSearchContext:
    """Per-analysis ephemeris and surface-result caches shared across search phases."""

    def __init__(self, epoch, radii):
        self.epoch = epoch
        self.radii = radii
        self.geometries = {}
        self.surfaces = {}
        self.ephemeris_batches = 0

    def preload(self, times):
        """Batch-load geometries while retaining caller sample order."""
        missing = [float(seconds) for seconds in times
                   if float(seconds) not in self.geometries]
        if missing:
            batch = Geometry.at_many(self.epoch + np.array(missing) * u.s, self.radii)
            self.geometries.update(zip(missing, batch, strict=True))
            self.ephemeris_batches += 1

    def geometry(self, seconds):
        """Return cached geometry at seconds from the search epoch."""
        seconds = float(seconds)
        self.preload([seconds])
        return self.geometries[seconds]

    def surface(self, seconds, phase):
        """Return cached best daylight footprint margin and witness point."""
        key = (float(seconds), phase)
        if key not in self.surfaces:
            geometry = self.geometry(seconds)
            bound = geometry.clearance_upper_bound(phase)
            self.surfaces[key] = (
                (bound, None) if bound < -PHASE_TOLERANCE_KM
                else geometry.best_surface_clearance(phase)
            )
        return self.surfaces[key]


def _find_closest_approach(context, samples):
    """Refine the maximum axis intersection discriminant within the search window."""
    discriminants = np.array([
        context.geometry(seconds).axis_discriminant() for seconds in samples
    ])
    if discriminants[0] >= 0 or discriminants[-1] >= 0:
        raise RuntimeError("Central path extends outside the search window")
    peak_index = int(np.argmax(discriminants))
    if peak_index in (0, len(samples) - 1):
        raise RuntimeError("Closest approach is not bracketed")
    peak = minimize_scalar(
        lambda seconds: -context.geometry(seconds).axis_discriminant(),
        bounds=(samples[peak_index - 1], samples[peak_index + 1]),
        method="bounded", options={"xatol": ROOT_TOLERANCE_SECONDS},
    )
    if not peak.success or not np.isfinite(peak.fun):
        raise RuntimeError("Closest-approach search failed")
    closest = float(peak.x)
    if abs(context.geometry(closest).axis_margin_km()) <= PHASE_TOLERANCE_KM:
        raise RuntimeError("Indeterminate axis intersection within numerical tolerance")
    return closest, context.geometry(closest).axis_discriminant() > 0


def _validate_witness_clearance(phase, clearance, point):
    """Reject invalid positive margins and identify strict candidate witnesses."""
    if not np.isfinite(clearance):
        raise RuntimeError(f"Non-finite {phase} surface clearance")
    if point is None:
        if clearance > PHASE_TOLERANCE_KM:
            raise RuntimeError(f"Missing {phase} surface witness")
        return False
    return clearance > PHASE_TOLERANCE_KM


def _witness_measurements(context, phase, seconds, clearance, point):
    """Return validated illumination measurements for a strict surface witness."""
    if not _validate_witness_clearance(phase, clearance, point):
        return None
    geometry = context.geometry(seconds)
    angular_margin = geometry.angular_clearance(point, phase)
    altitude = geometry.sun_altitude(point)
    on_surface = np.all(np.isfinite(point)) and np.isclose(
        np.linalg.norm(point / EARTH_AXES_KM), 1, atol=1e-8, rtol=0)
    overlaps = np.isfinite(angular_margin) and angular_margin > 0
    daylight = np.isfinite(altitude) and altitude >= -1e-6
    if not (on_surface and overlaps and daylight):
        raise RuntimeError(f"Invalid {phase} surface witness")
    return angular_margin, altitude


def _retain_witness(context, witnesses, witness_seconds, phase, seconds,
                    clearance, point, method):
    """Validate a strict daylight witness and retain its strongest instance."""
    measurements = _witness_measurements(context, phase, seconds, clearance, point)
    if measurements is None:
        return
    if phase in witnesses and clearance <= witnesses[phase]["clearance_km"]:
        return
    angular_margin, altitude = measurements
    witness_seconds[phase] = float(seconds)
    witnesses[phase] = {
        "time_utc": (context.epoch + seconds * u.s).iso,
        "clearance_km": float(clearance),
        "sun_altitude_deg": altitude,
        "surface_point_cirs_km": point.tolist(),
        "angular_clearance_arcsec": angular_margin,
        "method": method,
    }


def _axis_radius(context, seconds):
    """Return signed central-cone radius at the near axis/surface intersection."""
    geometry = context.geometry(seconds)
    point = geometry.axis_surface()
    if point is None:
        raise RuntimeError("Axis-surface search left the central interval")
    return geometry.clearance(point, "TOTAL")


def _central_path(context, samples, closest, witnesses, witness_seconds):
    """Find central-axis interval, phase transitions, and strong-phase witnesses."""
    epoch = context.epoch
    beginning, ending, interval, path_samples = _central_interval(
        context, samples, closest)
    path_samples, sequence = _sample_axis_phases(
        context, path_samples, witnesses, witness_seconds)
    transitions = _axis_transitions(context, epoch, path_samples, sequence)
    search_times = np.unique(np.concatenate((
        samples,
        np.linspace(beginning - 120, beginning + 120, 9),
        np.linspace(ending - 120, ending + 120, 9),
        [closest],
    )))
    changes = [value for index, value in enumerate(sequence)
               if index == 0 or value != sequence[index - 1]]
    hybrid_sequence = "-".join(changes) if len(changes) > 1 else None
    return interval, hybrid_sequence, transitions, search_times


def _central_interval(context, samples, closest):
    """Bracket central-axis entry/exit and preserve explicit near-limb samples."""
    epoch = context.epoch
    beginning = brentq(lambda seconds: context.geometry(seconds).axis_discriminant(),
                       samples[0], closest, xtol=ROOT_TOLERANCE_SECONDS)
    ending = brentq(lambda seconds: context.geometry(seconds).axis_discriminant(),
                    closest, samples[-1], xtol=ROOT_TOLERANCE_SECONDS)
    interval = [(epoch + beginning * u.s).iso, (epoch + ending * u.s).iso]
    limb_offset = min(.01, (ending - beginning) / 4)
    if limb_offset <= ROOT_TOLERANCE_SECONDS:
        raise RuntimeError("Indeterminate central path within root tolerance")
    path_samples = np.unique(np.concatenate((
        samples[(samples > beginning) & (samples < ending)],
        [beginning + limb_offset, ending - limb_offset, closest],
    )))
    return beginning, ending, interval, path_samples


def _sample_axis_phases(context, path_samples, witnesses, witness_seconds):
    """Refine axis-radius extrema and record each sampled central phase."""
    context.preload(path_samples)
    radii_on_path = np.array([_axis_radius(context, seconds) for seconds in path_samples])
    refined = []
    for sign in (1, -1):
        refined.extend(refine_maxima(
            path_samples, sign * radii_on_path,
            lambda seconds, sign=sign: sign * _axis_radius(context, seconds), .001))
    path_samples = np.unique(np.concatenate((path_samples, refined)))
    context.preload(path_samples)
    phases = []
    for seconds in path_samples:
        point = context.geometry(seconds).axis_surface()
        if point is not None:
            phases.append("T" if _axis_radius(context, seconds) > 0 else "A")
            for phase in ("TOTAL", "ANNULAR"):
                clearance = context.geometry(seconds).clearance(point, phase)
                _retain_witness(context, witnesses, witness_seconds, phase, seconds,
                                clearance, point, "axis-surface")
    return path_samples, phases


def _axis_transitions(context, epoch, path_samples, phases):
    """Refine every detected total/annular axis crossing."""
    transitions = []
    for before, after, phase_before, phase_after in zip(
            path_samples[:-1], path_samples[1:], phases[:-1], phases[1:], strict=True):
        if phase_before != phase_after:
            crossing = brentq(lambda seconds: _axis_radius(context, seconds),
                              before, after, xtol=ROOT_TOLERANCE_SECONDS)
            transitions.append((epoch + crossing * u.s).iso)
    return transitions


def _inherit_strong_partial(context, witnesses, witness_seconds):
    """Reuse a strict total/annular witness as proof of penumbral overlap."""
    for phase in ("TOTAL", "ANNULAR"):
        if phase not in witnesses:
            continue
        witness = witnesses[phase]
        seconds = witness_seconds[phase]
        point = np.array(witness["surface_point_cirs_km"])
        clearance = context.geometry(seconds).clearance(point, "PARTIAL")
        _retain_witness(context, witnesses, witness_seconds, "PARTIAL", seconds,
                        clearance, point, "strong-phase-witness")


def _search_phase(context, phase, search_times, witnesses, witness_seconds):
    """Search one phase's time-varying daylight footprint for a witness."""
    bounds = np.array([
        context.geometry(seconds).clearance_upper_bound(phase)
        for seconds in search_times
    ])
    bound_peaks = refine_maxima(
        search_times, bounds,
        lambda seconds: context.geometry(seconds).clearance_upper_bound(phase), .01)
    phase_times = np.unique(np.concatenate((search_times, bound_peaks)))
    context.preload(phase_times)
    results = [context.surface(seconds, phase) for seconds in phase_times]
    index = max(enumerate(results), key=lambda item: item[1][0])[0]
    best_clearance, point = results[index]
    best_seconds = float(phase_times[index])
    _retain_witness(context, witnesses, witness_seconds, phase, best_seconds,
                    best_clearance, point, "surface-optimization")
    refined = refine_maxima(
        phase_times, [result[0] for result in results],
        lambda seconds: context.surface(seconds, phase)[0], .01)
    for seconds in refined:
        clearance, point = context.surface(seconds, phase)
        _retain_witness(context, witnesses, witness_seconds, phase, seconds,
                        clearance, point, "surface-optimization")
        best_clearance = max(best_clearance, clearance)
    if phase not in witnesses and abs(best_clearance) <= PHASE_TOLERANCE_KM:
        raise RuntimeError(f"Indeterminate {phase} within numerical tolerance")
    return float(best_clearance)


def _global_type(witnesses, hybrid_sequence):
    """Resolve maximum global phase and reject incomplete hybrid evidence."""
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
    return global_type


def _analysis_context(approximate_utc, step_seconds, radius_model, refine_seed):
    """Validate analysis options and prepare the per-search context."""
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
    context = SolarSearchContext(epoch, RADIUS_MODELS[radius_model])
    context.preload(samples)
    return epoch, samples, context


def _search_phases(context, samples, closest, central):
    """Search ordered footprint phases and collect witnesses and signed margins."""
    witnesses = {}
    witness_seconds = {}
    for seconds in (samples[0], samples[-1]):
        if context.surface(seconds, "PARTIAL")[0] >= -PHASE_TOLERANCE_KM:
            raise RuntimeError("Penumbral footprint extends outside the search window")
    if central:
        interval, hybrid_sequence, transitions, search_times = _central_path(
            context, samples, closest, witnesses, witness_seconds)
    else:
        interval = None
        hybrid_sequence = None
        transitions = []
        search_times = np.unique(np.concatenate((samples, [closest])))
    context.preload(search_times)
    searched_maxima = _run_phase_search(
        context, search_times, witnesses, witness_seconds)
    return witnesses, searched_maxima, interval, hybrid_sequence, transitions


def _run_phase_search(context, search_times, witnesses, witness_seconds):
    """Evaluate phases in canonical order and return searched clearance maxima."""
    searched_maxima = {}
    for phase in ("TOTAL", "ANNULAR", "PARTIAL"):
        if phase == "PARTIAL":
            _inherit_strong_partial(context, witnesses, witness_seconds)
        if phase not in witnesses:
            searched_maxima[phase] = _search_phase(
                context, phase, search_times, witnesses, witness_seconds)
    return searched_maxima


def _analyze(approximate_utc, step_seconds=120, radius_model="nasa", *, refine_seed=True):
    epoch, samples, context = _analysis_context(
        approximate_utc, step_seconds, radius_model, refine_seed)
    closest_seconds, central = _find_closest_approach(context, samples)
    (witnesses, searched_maxima, central_interval,
     hybrid_sequence, transitions) = _search_phases(
         context, samples, closest_seconds, central)
    global_type = _global_type(witnesses, hybrid_sequence)
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
        "geometry_evaluations": len(context.geometries),
        "ephemeris_batches": context.ephemeris_batches,
        "surface_optimizations": sum(
            point is not None for _, point in context.surfaces.values()),
        "searched_max_clearances_km": searched_maxima,
    }


def _greatest_eclipse_time(time_obj):
    """Keep the established minimum Sun–Moon separation convention."""
    return eclipse_ephemeris.find_greatest_eclipse_time(time_obj, is_lunar=False)


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

        if not eclipse_ephemeris.is_new_moon(time_obj):
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
            greatest_eclipse_time=raw["greatest_eclipse_time"],
            size_ratio=raw["size_ratio"],
            witnesses=witnesses,
            central_path=SolarCentralPath(
                central=raw["central"],
                central_interval_utc=raw["central_interval_utc"],
                hybrid_sequence=raw["hybrid_sequence"],
                axis_phase_transitions_utc=raw["axis_phase_transitions_utc"],
            ),
        )
        _CLASSIFICATION_CACHE.set(key, result)
        return result


def clear_solar_eclipse_classification_cache():
    """Clear the bounded, thread-safe global-classification cache."""
    _CLASSIFICATION_CACHE.clear()
    _CONTACT_CACHE.clear()


def _combined_margin(context, seconds, phases):
    """Return the largest daylight-surface margin among requested contact phases."""
    return max(context.surface(seconds, phase)[0] for phase in phases)


def _contact_crossings(context, phases, times, values):
    """Refine all threshold transitions of the combined footprint margin."""
    crossings = []
    for left, right, left_value, right_value in zip(
            times[:-1], times[1:], values[:-1], values[1:], strict=True):
        if (left_value < 0 <= right_value) or (left_value >= 0 > right_value):
            try:
                crossings.append(brentq(
                    lambda seconds: _combined_margin(context, seconds, phases),
                    float(left), float(right),
                    xtol=ROOT_TOLERANCE_SECONDS,
                ))
            except (ValueError, RuntimeError) as error:
                raise RuntimeError("Unable to bracket global solar contact crossing") from error
    if len(crossings) < 2:
        raise RuntimeError("Global solar contact crossings were not bracketed")
    return crossings


def _contact_search_samples(context, phases, samples):
    """Refine the combined spatial bound and surface margin on a sample grid."""
    bounds = [
        max(context.geometry(seconds).clearance_upper_bound(phase) for phase in phases)
        for seconds in samples
    ]
    bound_peaks = refine_maxima(
        samples, bounds,
        lambda seconds: max(
            context.geometry(seconds).clearance_upper_bound(phase) for phase in phases),
        0.01,
    )
    times = np.unique(np.concatenate((samples, bound_peaks)))
    context.preload(times)
    values = [_combined_margin(context, seconds, phases) for seconds in times]
    margin_peaks = refine_maxima(
        times, values, lambda seconds: _combined_margin(context, seconds, phases), 0.01)
    times = np.unique(np.concatenate((times, margin_peaks)))
    values = [_combined_margin(context, seconds, phases) for seconds in times]
    return times, values


def _has_contact_interval(values):
    """Validate search-window closure and report whether a positive interval exists."""
    if values[0] >= -PHASE_TOLERANCE_KM or values[-1] >= -PHASE_TOLERANCE_KM:
        raise RuntimeError("Global solar contact interval extends outside the search window")
    peak_value = max(values)
    if abs(peak_value) <= PHASE_TOLERANCE_KM:
        raise RuntimeError("Indeterminate global solar contact within numerical tolerance")
    return peak_value > 0


def _contact_pair(epoch, phases, radius_model="nasa", step_seconds=SEARCH_STEP_SECONDS,
                  search_window_hours=SEARCH_HALF_WIDTH_HOURS):
    if not np.isfinite(search_window_hours) or not 0 < search_window_hours <= 24:
        raise ValueError("search_window_hours must be in (0, 24]")
    samples = np.linspace(
        -search_window_hours * 3600,
        search_window_hours * 3600,
        int(np.ceil(2 * search_window_hours * 3600 / step_seconds)) + 1,
    )
    context = SolarSearchContext(epoch, RADIUS_MODELS[radius_model])
    context.preload(samples)
    times, values = _contact_search_samples(context, phases, samples)
    if not _has_contact_interval(values):
        return None, None
    crossings = _contact_crossings(context, phases, times, values)
    return ((epoch + crossings[0] * u.s).iso, (epoch + crossings[-1] * u.s).iso)


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
