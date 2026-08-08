"""
Eclipse Detection Service - Issue 141
Provides eclipse detection and classification using ecliptic latitude thresholds
and shadow cone geometry for precise type determination.

Key Reference: research/verify_eclipse_approach.py (validated implementation)
"""

import numpy as np
from astropy.time import Time
from astropy.coordinates import get_body, get_sun, EarthLocation, SkyCoord
from astropy.coordinates import GeocentricMeanEcliptic
import astropy.units as u
import astropy.constants as const

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

# Ecliptic latitude thresholds (degrees)
LUNAR_ECLIPSE_THRESHOLD = 11.633              # 11° 38'
SOLAR_ECLIPSE_THRESHOLD = 17.417              # 17° 25'

# Draconic year (lunar node precession period)
DRACONIC_YEAR_DAYS = 6585.32
LUNAR_NODE_EPOCH = Time('2000-01-01')
LUNAR_NODE_EPOCH_LON = 280.47

# Golden ratio conjugate, used by the golden-section minimum-separation search below.
_INV_PHI = (np.sqrt(5) - 1) / 2


def get_moon_ecliptic_latitude(time_obj):
    """
    Calculate moon's ecliptic latitude at given time.

    Args:
        time_obj: astropy Time object

    Returns:
        Moon's ecliptic latitude in degrees
    """
    moon = get_body('moon', time_obj, location=GEOCENTRIC)
    moon_ecliptic = moon.transform_to(GeocentricMeanEcliptic(equinox=time_obj))
    return moon_ecliptic.lat.degree


def get_lunar_node_position(time_obj):
    """
    Get approximate ecliptic longitude of lunar ascending node.

    The lunar node precesses with an 18.6-year period (draconic year).

    Args:
        time_obj: astropy Time object

    Returns:
        Ecliptic longitude of ascending node in degrees (0-360)
    """
    days_since_epoch = time_obj.jd - LUNAR_NODE_EPOCH.jd
    node_lon = (LUNAR_NODE_EPOCH_LON - 360.0 * days_since_epoch / DRACONIC_YEAR_DAYS) % 360
    return node_lon


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

    Args:
        approx_time: astropy Time object, approximate new/full moon instant
        is_lunar: bool, True to minimize Moon-antisolar separation, False for Sun-Moon
        search_window_hours: half-width (hours) of the initial bracketing window
        iterations: number of golden-section iterations (40 narrows the interval to a
            small fraction of a second, far below any physically meaningful precision)

    Returns:
        astropy Time object at the (refined) instant of greatest eclipse
    """
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

    return a + (b - a) / 2


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
    if umbral_radius_km != 0:
        umbral_radius_ang = np.degrees(np.arctan(abs(umbral_radius_km) / moon_dist))
    else:
        umbral_radius_ang = 0

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

    Args:
        time_obj: astropy Time object

    Returns:
        dict with eclipse type and magnitude values
    """
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

    return {
        'eclipse_type': eclipse_type,
        'umbral_magnitude': round(umbral_mag, 4),
        'penumbral_magnitude': round(penumbral_mag, 4),
        'angular_separation_deg': round(separation, 4),
    }


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

    Args:
        time_obj: astropy Time object

    Returns:
        dict with eclipse type and size characteristics
    """
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

    return {
        'eclipse_type': eclipse_type,
        'size_ratio': round(size_ratio, 6),
        'moon_ang_diam_deg': round(moon_ang_radius * 2, 6),
        'sun_ang_diam_deg': round(sun_ang_radius * 2, 6),
        'umbral_exists': umbral_exists,
        'offset_km': round(offset_km, 1),
        'angular_separation_deg': round(separation_deg, 4),
    }


def check_eclipse_at_time(time_obj, is_lunar=True):
    """
    Complete eclipse analysis: detection (ecliptic latitude) + type
    classification (shadow geometry).

    Single-call API: processes eclipse in one astropy query for efficiency.

    Args:
        time_obj: astropy Time object
        is_lunar: bool, True for lunar eclipse check, False for solar

    Returns:
        dict with complete eclipse information
    """
    moon_lat = get_moon_ecliptic_latitude(time_obj)
    node_lon = get_lunar_node_position(time_obj)

    if is_lunar:
        threshold = LUNAR_ECLIPSE_THRESHOLD
        is_full = is_full_moon(time_obj)
        eclipse_occurs = (abs(moon_lat) < threshold) and is_full

        if eclipse_occurs:
            greatest_time = find_greatest_eclipse_time(time_obj, is_lunar=True)
            type_info = classify_lunar_eclipse_type(greatest_time)
            eclipse_type = type_info['eclipse_type']
            magnitude = type_info['umbral_magnitude']
        else:
            greatest_time = time_obj
            eclipse_type = "NONE"
            magnitude = None
            type_info = {'penumbral_magnitude': None}

        return {
            'time': time_obj.iso,
            'greatest_eclipse_time': greatest_time.iso,
            'is_eclipse': bool(eclipse_occurs),
            'eclipse_type': eclipse_type,
            'phase': 'full',
            'moon_ecl_lat_deg': round(moon_lat, 4),
            'node_ecl_lon_deg': round(node_lon, 2),
            'within_threshold': bool(abs(moon_lat) < threshold),
            'umbral_magnitude': magnitude,
            'penumbral_magnitude': type_info.get('penumbral_magnitude'),
        }

    # Solar eclipse
    threshold = SOLAR_ECLIPSE_THRESHOLD
    is_new = is_new_moon(time_obj)
    eclipse_occurs = (abs(moon_lat) < threshold) and is_new

    if eclipse_occurs:
        greatest_time = find_greatest_eclipse_time(time_obj, is_lunar=False)
        type_info = classify_solar_eclipse_type(greatest_time)
        eclipse_type = type_info['eclipse_type']
        size_ratio = type_info['size_ratio']
    else:
        greatest_time = time_obj
        eclipse_type = "NONE"
        size_ratio = None
        type_info = {'umbral_exists': None}

    return {
        'time': time_obj.iso,
        'greatest_eclipse_time': greatest_time.iso,
        'is_eclipse': bool(eclipse_occurs),
        'eclipse_type': eclipse_type,
        'phase': 'new',
        'moon_ecl_lat_deg': round(moon_lat, 4),
        'node_ecl_lon_deg': round(node_lon, 2),
        'within_threshold': bool(abs(moon_lat) < threshold),
        'size_ratio': size_ratio,
        'umbral_exists': type_info.get('umbral_exists'),
    }
