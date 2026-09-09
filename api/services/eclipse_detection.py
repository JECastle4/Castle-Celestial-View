"""
Eclipse Detection Service - Issue 141
Provides eclipse detection and classification using ecliptic latitude thresholds
and shadow cone geometry for precise type determination.

Key Reference: research/verify_eclipse_approach.py (validated implementation)
"""

import numpy as np
from astropy.coordinates import get_body, get_sun, EarthLocation, SkyCoord
from astropy.coordinates import GeocentricMeanEcliptic
import astropy.units as u
import astropy.constants as const
from functools import lru_cache

# Physical constants (IAU standard)
R_SUN_KM = const.R_sun.to(u.km).value        # ~695,700 km
R_MOON_KM = 1737.4                            # km
R_EARTH_KM = 6371.0                           # km

# True geocentric location (Earth's center, radius 0). get_body() applies topocentric
# parallax correction (up to ~1° for the Moon) when given a surface-based location such
# as EarthLocation.from_geodetic(0, 0). get_sun() is always purely geocentric, so using a
# surface location for the Moon while comparing against the Sun introduces a spurious
# parallax mismatch of up to ~1° into any separation-based calculation. Using this true
# geocentric location for every get_body() call keeps Sun and Moon positions in the same
# (parallax-free) reference frame.
GEOCENTRIC = EarthLocation.from_geocentric(0 * u.km, 0 * u.km, 0 * u.km)

# CRITICAL PRE-FILTER: "Ecliptic limits" (Meeus, Astronomical Algorithms, Ch. 54).
# The Moon's ecliptic latitude never exceeds its ~5.145° orbital inclination, so a
# fixed latitude threshold near that value (e.g. 5.3°) never actually rejects
# anything - every syzygy passes. The real, well-established fast test is the
# angular distance from a lunar node at syzygy: eclipses are only geometrically
# possible within a fixed distance of a node (Sun's distance from node for solar,
# Moon's distance from node for lunar), because that distance directly bounds how
# close the Moon can get to the shadow axis. Beyond these limits an eclipse is
# impossible and the expensive greatest-eclipse search/shadow geometry can be
# skipped entirely.
SOLAR_ECLIPSE_NODE_LIMIT_DEG = 18.5167   # 18°31' major limit - solar eclipse impossible beyond this
LUNAR_ECLIPSE_NODE_LIMIT_DEG = 12.25     # 12°15' major limit - lunar eclipse impossible beyond this

# Mean lunar ascending node longitude at J2000.0 and its (retrograde) regression
# rate - low-order term of Meeus Ch. 47, full regression every ~18.6 years.
# Precise enough to bracket eclipse seasons for this fast pre-filter.
MEAN_NODE_LON_J2000_DEG = 125.04452
MEAN_NODE_REGRESSION_DEG_PER_DAY = -0.0529538083

# Golden ratio conjugate, used by the golden-section minimum-separation search below.
_INV_PHI = (np.sqrt(5) - 1) / 2

# Phase 2.2 Optimization: Cache expensive eclipse calculations
# These caches avoid redundant find_greatest_eclipse_time() and classification calls
# within a single request or across similar time ranges (typical for batch operations)
_GREATEST_ECLIPSE_CACHE = {}  # key: (time.iso, is_lunar) -> Time object
_ECLIPSE_TYPE_CACHE_LUNAR = {}  # key: time.iso -> classification dict
_ECLIPSE_TYPE_CACHE_SOLAR = {}  # key: time.iso -> classification dict


def get_moon_ecliptic_coords(time_obj):
    """
    Calculate moon's ecliptic (latitude, longitude) from a single position query.

    Args:
        time_obj: astropy Time object

    Returns:
        (latitude_deg, longitude_deg) tuple
    """
    moon = get_body('moon', time_obj, location=GEOCENTRIC)
    moon_ecliptic = moon.transform_to(GeocentricMeanEcliptic(equinox=time_obj))
    return moon_ecliptic.lat.degree, moon_ecliptic.lon.degree % 360


def get_moon_ecliptic_latitude(time_obj):
    """
    Calculate moon's ecliptic latitude at given time.

    Args:
        time_obj: astropy Time object

    Returns:
        Moon's ecliptic latitude in degrees
    """
    lat, _ = get_moon_ecliptic_coords(time_obj)
    return lat


def get_sun_ecliptic_longitude(time_obj):
    """
    Calculate sun's ecliptic longitude at given time.

    Args:
        time_obj: astropy Time object

    Returns:
        Sun's ecliptic longitude in degrees (0-360)
    """
    sun = get_sun(time_obj)
    sun_ecliptic = sun.transform_to(GeocentricMeanEcliptic(equinox=time_obj))
    return sun_ecliptic.lon.degree % 360


def get_mean_lunar_node_longitude(time_obj):
    """
    Mean ecliptic longitude of the Moon's ascending node at the given time.

    Args:
        time_obj: astropy Time object

    Returns:
        Mean ascending node longitude in degrees (0-360)
    """
    days_since_j2000 = time_obj.jd - 2451545.0
    return (MEAN_NODE_LON_J2000_DEG + MEAN_NODE_REGRESSION_DEG_PER_DAY * days_since_j2000) % 360


def node_distance_deg(ecliptic_longitude_deg, time_obj):
    """
    Angular distance from an ecliptic longitude to the nearest lunar node.

    Ascending and descending nodes are 180° apart and equally valid crossing
    points, so the result is folded into [0, 90].

    Args:
        ecliptic_longitude_deg: ecliptic longitude of the Sun or Moon, in degrees
        time_obj: astropy Time object

    Returns:
        Distance to the nearest node, in degrees (0-90)
    """
    node_lon = get_mean_lunar_node_longitude(time_obj)
    diff = abs((ecliptic_longitude_deg - node_lon + 180) % 360 - 180)
    return diff if diff <= 90 else 180 - diff


def get_moon_phase_angle(time_obj):
    """
    Calculate moon's phase angle (elongation from sun).

    Args:
        time_obj: astropy Time object

    Returns:
        Phase angle in degrees (0° = new moon, 180° = full moon)
    """
    sun = get_sun(time_obj)
    moon = get_body('moon', time_obj, location=GEOCENTRIC)
    return sun.separation(moon).degree


def is_new_moon(time_obj, tolerance_deg=10):
    """Check if time is approximately at new moon."""
    phase_angle = get_moon_phase_angle(time_obj)
    return phase_angle < tolerance_deg


def is_full_moon(time_obj, tolerance_deg=10):
    """Check if time is approximately at full moon."""
    phase_angle = get_moon_phase_angle(time_obj)
    return abs(phase_angle - 180) < tolerance_deg


# ============================================================================
# SHADOW CONE GEOMETRY (Eclipse Type Classification)
# ============================================================================

def get_antisolar_separation_deg(time_obj):
    """
    Angular separation between the Moon and the antisolar point (the point in the sky
    exactly opposite the Sun), in degrees.

    This is the relevant separation for lunar eclipse geometry: Earth's umbral/penumbral
    shadow axis points toward the antisolar point, so the Moon must pass near it for a
    lunar eclipse to occur.
    """
    sun = get_sun(time_obj)
    moon = get_body('moon', time_obj, location=GEOCENTRIC)
    antisolar = SkyCoord(
        ra=(sun.ra + 180 * u.deg) % (360 * u.deg),
        dec=-sun.dec,
        frame='gcrs',
        obstime=time_obj,
    )
    return antisolar.separation(moon).degree


def find_greatest_eclipse_time(approx_time, is_lunar, search_window_hours=24, iterations=40):
    """
    Refine an approximate new/full moon time to the precise instant of greatest eclipse:
    the local minimum of angular separation between the Moon and the shadow axis.

    This instant can differ from the exact new/full moon (ecliptic-longitude conjunction)
    instant by up to a couple of hours, because the Moon's ecliptic latitude is also
    changing near conjunction/opposition. Classification and contact-time calculations
    must be anchored to the greatest-eclipse instant, not the new/full moon instant.

    Uses golden-section search, which is appropriate because separation(t) is unimodal
    (has a single minimum) within a +/- search_window_hours bracket around a new/full moon.

    Phase 2.2 Optimization: Results are cached to avoid redundant calculations
    when the same eclipse time is queried multiple times (common in batch processing
    or when contact times request additional analysis).

    Args:
        approx_time: astropy Time object, approximate new/full moon instant
        is_lunar: bool, True to minimize Moon-antisolar separation, False for Sun-Moon
        search_window_hours: half-width (hours) of the initial bracketing window
        iterations: number of golden-section iterations (40 narrows the interval to a
            small fraction of a second, far below any physically meaningful precision)

    Returns:
        astropy Time object at the (refined) instant of greatest eclipse
    """
    # Cache key: ISO string + eclipse type
    cache_key = (approx_time.iso, is_lunar)
    
    # Check cache first (Phase 2.2 optimization)
    if cache_key in _GREATEST_ECLIPSE_CACHE:
        return _GREATEST_ECLIPSE_CACHE[cache_key]
    
    # Compute if not cached
    if is_lunar:
        separation_fn = get_antisolar_separation_deg
    else:
        def separation_fn(t):
            sun = get_sun(t)
            moon = get_body('moon', t, location=GEOCENTRIC)
            return sun.separation(moon).degree

    a = approx_time - search_window_hours * u.hour
    b = approx_time + search_window_hours * u.hour
    span = b - a
    c = b - span * _INV_PHI
    d = a + span * _INV_PHI
    fc = separation_fn(c)
    fd = separation_fn(d)

    for _ in range(iterations):
        if fc < fd:
            b = d
            d = c
            fd = fc
            span = b - a
            c = b - span * _INV_PHI
            fc = separation_fn(c)
        else:
            a = c
            c = d
            fc = fd
            span = b - a
            d = a + span * _INV_PHI
            fd = separation_fn(d)

    result = a + (b - a) / 2
    
    # Cache the result (Phase 2.2 optimization)
    _GREATEST_ECLIPSE_CACHE[cache_key] = result
    
    return result


def get_sun_moon_parameters(time_obj):
    """
    Get all Sun and Moon parameters in a single astropy call.

    This minimizes API calls - all classification calculations are derived
    from this single query result.

    Args:
        time_obj: astropy Time object

    Returns:
        dict with positional and angular data for both bodies
    """
    sun = get_sun(time_obj)
    moon = get_body('moon', time_obj, location=GEOCENTRIC)

    sun_dist_km = sun.distance.to(u.km).value
    moon_dist_km = moon.distance.to(u.km).value

    # Angular radii (radians → degrees)
    sun_ang_radius = np.degrees(np.arctan(R_SUN_KM / sun_dist_km))
    moon_ang_radius = np.degrees(np.arctan(R_MOON_KM / moon_dist_km))

    # Ecliptic coordinates
    moon_ecl = moon.transform_to(GeocentricMeanEcliptic(equinox=time_obj))

    # Sun-Moon separation (used for solar eclipse geometry)
    sun_moon_separation_deg = sun.separation(moon).degree

    # Moon-antisolar separation (used for lunar eclipse geometry)
    antisolar = SkyCoord(
        ra=(sun.ra + 180 * u.deg) % (360 * u.deg),
        dec=-sun.dec,
        frame='gcrs',
        obstime=time_obj,
    )
    antisolar_separation_deg = antisolar.separation(moon).degree

    return {
        'sun_dist_km': sun_dist_km,
        'moon_dist_km': moon_dist_km,
        'sun_ang_radius_deg': sun_ang_radius,
        'moon_ang_radius_deg': moon_ang_radius,
        'sun_ang_diam_deg': sun_ang_radius * 2,
        'moon_ang_diam_deg': moon_ang_radius * 2,
        'moon_ecl_lat_deg': moon_ecl.lat.degree,
        'moon_ecl_lon_deg': moon_ecl.lon.degree % 360,
        'sun_moon_separation_deg': sun_moon_separation_deg,
        'antisolar_separation_deg': antisolar_separation_deg,
    }


def calculate_earth_shadow_cone(time_obj):
    """
    Calculate Earth's shadow cone at Moon distance (for lunar eclipses).

    Meeus Algorithm:
        umbral_radius = R_earth - (R_sun * d_moon) / d_sun
        penumbral_radius = R_earth + (R_sun * d_moon) / d_sun

    Args:
        time_obj: astropy Time object (should be at full moon)

    Returns:
        dict with umbral and penumbral radii (km and angular)
    """
    params = get_sun_moon_parameters(time_obj)
    sun_dist = params['sun_dist_km']
    moon_dist = params['moon_dist_km']

    # Umbral radius at Moon distance (dark shadow)
    umbral_radius_km = R_EARTH_KM - (R_SUN_KM * moon_dist) / sun_dist
    umbral_radius_ang = np.degrees(np.arctan(umbral_radius_km / moon_dist))

    # Penumbral radius at Moon distance (faint shadow)
    penumbral_radius_km = R_EARTH_KM + (R_SUN_KM * moon_dist) / sun_dist
    penumbral_radius_ang = np.degrees(np.arctan(penumbral_radius_km / moon_dist))

    return {
        'umbral_radius_km': umbral_radius_km,
        'penumbral_radius_km': penumbral_radius_km,
        'umbral_radius_ang': umbral_radius_ang,
        'penumbral_radius_ang': penumbral_radius_ang,
    }


def calculate_moon_shadow_cone(time_obj):
    """
    Calculate Moon's shadow cone at Earth distance (for solar eclipses).

    Meeus Algorithm:
        umbral_radius = R_moon - (R_sun * d_moon) / d_sun
        penumbral_radius = R_moon + (R_sun * d_moon) / d_sun

    Note: If umbral_radius < 0, the umbra doesn't reach Earth → ANNULAR eclipse

    Args:
        time_obj: astropy Time object (should be at new moon)

    Returns:
        dict with umbral/penumbral radii and umbral_exists flag
    """
    params = get_sun_moon_parameters(time_obj)
    sun_dist = params['sun_dist_km']
    moon_dist = params['moon_dist_km']

    # Umbral radius at Earth distance (dark shadow)
    umbral_radius_km = R_MOON_KM - (R_SUN_KM * moon_dist) / sun_dist
    umbral_radius_ang = np.degrees(np.arctan(abs(umbral_radius_km) / moon_dist))

    # Penumbral radius at Earth distance
    penumbral_radius_km = R_MOON_KM + (R_SUN_KM * moon_dist) / sun_dist
    penumbral_radius_ang = np.degrees(np.arctan(penumbral_radius_km / moon_dist))

    return {
        'umbral_radius_km': umbral_radius_km,
        'penumbral_radius_km': penumbral_radius_km,
        'umbral_radius_ang': umbral_radius_ang,
        'penumbral_radius_ang': penumbral_radius_ang,
        'umbral_exists': (umbral_radius_km > 0),
    }


def classify_lunar_eclipse_type(time_obj):
    """
    Classify lunar eclipse type using magnitude calculations.

    Magnitude = (shadow_radius + moon_radius - separation) / (2 * moon_radius)

    This is the standard astronomical definition: it properly accounts for the actual
    angular separation between the Moon and the shadow axis (antisolar point), rather
    than assuming the Moon passes exactly through the shadow axis (separation = 0), which
    would significantly overestimate the magnitude. Best accuracy requires time_obj to be
    the instant of greatest eclipse (see find_greatest_eclipse_time), not just any full
    moon instant.

    Classification:
        mag > 1.0  → TOTAL (moon fully in dark umbra)
        mag 0-1.0  → PARTIAL (moon partially in umbra)
        mag < 0, penumbral > 0 → PENUMBRAL (penumbra only)

    Phase 2.2 Optimization: Results are cached to avoid redundant parameter calculations
    and shadow-cone computations when the same lunar eclipse is analyzed multiple times.

    Args:
        time_obj: astropy Time object

    Returns:
        dict with eclipse type and magnitude values
    """
    # Cache key for lunar eclipse classification (Phase 2.2 optimization)
    cache_key = time_obj.iso
    
    # Check cache first
    if cache_key in _ECLIPSE_TYPE_CACHE_LUNAR:
        return _ECLIPSE_TYPE_CACHE_LUNAR[cache_key]
    
    params = get_sun_moon_parameters(time_obj)
    shadow = calculate_earth_shadow_cone(time_obj)

    moon_ang_radius = params['moon_ang_radius_deg']
    separation = params['antisolar_separation_deg']
    umbral_radius_ang = shadow['umbral_radius_ang']
    penumbral_radius_ang = shadow['penumbral_radius_ang']

    umbral_mag = (umbral_radius_ang + moon_ang_radius - separation) / (2 * moon_ang_radius)
    penumbral_mag = (penumbral_radius_ang + moon_ang_radius - separation) / (2 * moon_ang_radius)

    # Classification
    if umbral_mag > 1.0:
        eclipse_type = "TOTAL"
    elif umbral_mag > 0:
        eclipse_type = "PARTIAL"
    elif penumbral_mag > 0:
        eclipse_type = "PENUMBRAL"
    else:
        eclipse_type = "NONE"

    result = {
        'eclipse_type': eclipse_type,
        'umbral_magnitude': round(umbral_mag, 4),
        'penumbral_magnitude': round(penumbral_mag, 4),
        'angular_separation_deg': round(separation, 4),
    }
    
    # Cache the result (Phase 2.2 optimization)
    _ECLIPSE_TYPE_CACHE_LUNAR[cache_key] = result
    
    return result


def classify_solar_eclipse_type(time_obj):
    """
    Classify solar eclipse type.

    Unlike lunar eclipses (a purely geocentric phenomenon: whether the Moon passes
    through Earth's real, physically-sized shadow cone), solar eclipse visibility is
    inherently topocentric. An observer on Earth's surface sees the Moon shifted by up
    to ~1° of parallax relative to a hypothetical observer at Earth's center. Comparing
    simple Sun-Moon angular separation (as seen from Earth's center) against the sum of
    their angular radii would incorrectly rule out eclipses that are geocentrically "not
    overlapping" but are still visible from specific points on Earth's surface once
    parallax is taken into account.

    Correct approach: work in the shadow's fundamental plane (perpendicular to the
    Sun-Moon axis, at the Moon's distance). The perpendicular offset of Earth's center
    from that axis is approximately:
        offset_km = moon_dist_km * radians(sun_moon_separation_deg)
    An eclipse is visible from somewhere on Earth if this offset is less than the
    shadow radius (penumbral, for any eclipse; umbral/antumbral, for a central eclipse)
    plus Earth's own radius (a point on Earth's curved surface can be up to R_EARTH_KM
    closer to the shadow axis than Earth's center).

    Note: genuine hybrid eclipses (annular along part of the path, total along the rest,
    due to Earth's curvature) are rare (~3% of solar eclipses) and require full path
    analysis across Earth's curved surface, not just a single geocentric evaluation.
    They are not distinguished by this simplified model; they classify as TOTAL or
    ANNULAR depending on the sign of the geocentric umbral radius at greatest eclipse.

    Best accuracy requires time_obj to be the instant of greatest eclipse (see
    find_greatest_eclipse_time), not just any new moon instant.

    Phase 2.2 Optimization: Results are cached to avoid redundant parameter calculations
    and shadow-cone computations when the same solar eclipse is analyzed multiple times.

    Args:
        time_obj: astropy Time object

    Returns:
        dict with eclipse type and size characteristics
    """
    # Cache key for solar eclipse classification (Phase 2.2 optimization)
    cache_key = time_obj.iso
    
    # Check cache first
    if cache_key in _ECLIPSE_TYPE_CACHE_SOLAR:
        return _ECLIPSE_TYPE_CACHE_SOLAR[cache_key]
    
    params = get_sun_moon_parameters(time_obj)
    shadow = calculate_moon_shadow_cone(time_obj)

    moon_dist_km = params['moon_dist_km']
    separation_deg = params['sun_moon_separation_deg']
    sun_ang_radius = params['sun_ang_radius_deg']
    moon_ang_radius = params['moon_ang_radius_deg']
    size_ratio = moon_ang_radius / sun_ang_radius

    umbral_radius_km = shadow['umbral_radius_km']
    penumbral_radius_km = shadow['penumbral_radius_km']
    umbral_exists = shadow['umbral_exists']

    offset_km = moon_dist_km * np.radians(separation_deg)
    penumbral_threshold_km = penumbral_radius_km + R_EARTH_KM
    central_threshold_km = abs(umbral_radius_km) + R_EARTH_KM

    if offset_km >= penumbral_threshold_km:
        eclipse_type = "NONE"
    elif offset_km < central_threshold_km:
        eclipse_type = "TOTAL" if umbral_exists else "ANNULAR"
    else:
        eclipse_type = "PARTIAL"

    result = {
        'eclipse_type': eclipse_type,
        'size_ratio': round(size_ratio, 6),
        'moon_ang_diam_deg': round(moon_ang_radius * 2, 6),
        'sun_ang_diam_deg': round(sun_ang_radius * 2, 6),
        'umbral_exists': umbral_exists,
        'offset_km': round(offset_km, 1),
        'angular_separation_deg': round(separation_deg, 4),
    }
    
    # Cache the result (Phase 2.2 optimization)
    _ECLIPSE_TYPE_CACHE_SOLAR[cache_key] = result
    
    return result


def _check_lunar_eclipse_at_time(time_obj, moon_lat, moon_lon):
    """Check for lunar eclipse at given time (assumes syzygy/node pre-filter passed)."""
    greatest_time = find_greatest_eclipse_time(time_obj, is_lunar=True)
    type_info = classify_lunar_eclipse_type(greatest_time)
    eclipse_type = type_info['eclipse_type']
    magnitude = type_info['umbral_magnitude']

    return {
        'time': time_obj.iso,
        'greatest_eclipse_time': greatest_time.iso,
        'is_eclipse': eclipse_type != "NONE",
        'eclipse_type': eclipse_type,
        'phase': 'full',
        'moon_ecl_lat_deg': round(moon_lat, 4),
        'within_threshold': True,
        'umbral_magnitude': magnitude,
        'penumbral_magnitude': type_info.get('penumbral_magnitude'),
    }


def _check_solar_eclipse_at_time(time_obj, moon_lat):
    """Check for solar eclipse at given time (assumes syzygy/node pre-filter passed)."""
    greatest_time = find_greatest_eclipse_time(time_obj, is_lunar=False)
    type_info = classify_solar_eclipse_type(greatest_time)
    eclipse_type = type_info['eclipse_type']
    size_ratio = type_info['size_ratio']

    return {
        'time': time_obj.iso,
        'greatest_eclipse_time': greatest_time.iso,
        'is_eclipse': eclipse_type != "NONE",
        'eclipse_type': eclipse_type,
        'phase': 'new',
        'moon_ecl_lat_deg': round(moon_lat, 4),
        'within_threshold': True,
        'size_ratio': size_ratio,
        'umbral_exists': type_info.get('umbral_exists'),
    }


def _get_eclipse_pre_filter_result(time_obj, moon_lat, is_lunar):
    """Build result dict when eclipse pre-filter (syzygy/node distance) fails."""
    if is_lunar:
        return {
            'time': time_obj.iso,
            'greatest_eclipse_time': time_obj.iso,
            'is_eclipse': False,
            'eclipse_type': "NONE",
            'phase': 'full',
            'moon_ecl_lat_deg': round(moon_lat, 4),
            'within_threshold': False,
            'umbral_magnitude': None,
            'penumbral_magnitude': None,
        }
    else:
        return {
            'time': time_obj.iso,
            'greatest_eclipse_time': time_obj.iso,
            'is_eclipse': False,
            'eclipse_type': "NONE",
            'phase': 'new',
            'moon_ecl_lat_deg': round(moon_lat, 4),
            'within_threshold': False,
            'size_ratio': None,
            'umbral_exists': None,
        }


def clear_eclipse_caches():
    """
    Clear all eclipse detection caches (Phase 2.2 optimization).
    
    Useful for memory management in long-running processes or testing.
    Caches will be repopulated on demand.
    """
    global _GREATEST_ECLIPSE_CACHE, _ECLIPSE_TYPE_CACHE_LUNAR, _ECLIPSE_TYPE_CACHE_SOLAR
    _GREATEST_ECLIPSE_CACHE.clear()
    _ECLIPSE_TYPE_CACHE_LUNAR.clear()
    _ECLIPSE_TYPE_CACHE_SOLAR.clear()


def check_eclipse_at_time(time_obj, is_lunar=True):
    """
    Complete eclipse analysis: detection (ecliptic-limits pre-filter) + type
    classification (shadow geometry).

    Pre-filter: Checks whether the Sun (solar) or Moon (lunar) is within its
    "ecliptic limit" distance of a lunar node. If not, an eclipse is geometrically
    impossible and the function returns early without the expensive greatest-eclipse
    search or shadow geometry calculations. See SOLAR_ECLIPSE_NODE_LIMIT_DEG /
    LUNAR_ECLIPSE_NODE_LIMIT_DEG for the geometric rationale.

    Args:
        time_obj: astropy Time object
        is_lunar: bool, True for lunar eclipse check, False for solar

    Returns:
        dict with complete eclipse information
    """
    moon_lat, moon_lon = get_moon_ecliptic_coords(time_obj)
    is_full = is_full_moon(time_obj)
    is_new = is_new_moon(time_obj)

    if is_lunar:
        is_syzygy = is_full
        node_dist = node_distance_deg(moon_lon, time_obj)
        if node_dist > LUNAR_ECLIPSE_NODE_LIMIT_DEG or not is_syzygy:
            return _get_eclipse_pre_filter_result(time_obj, moon_lat, is_lunar=True)
        return _check_lunar_eclipse_at_time(time_obj, moon_lat, moon_lon)

    # Solar eclipse
    is_syzygy = is_new
    sun_lon = get_sun_ecliptic_longitude(time_obj)
    node_dist = node_distance_deg(sun_lon, time_obj)
    if node_dist > SOLAR_ECLIPSE_NODE_LIMIT_DEG or not is_syzygy:
        return _get_eclipse_pre_filter_result(time_obj, moon_lat, is_lunar=False)
    return _check_solar_eclipse_at_time(time_obj, moon_lat)
