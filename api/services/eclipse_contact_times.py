"""
Eclipse Contact Times Service - Issue 141

Computes the contact times (penumbral/umbral boundary crossings for lunar eclipses;
global penumbral/central shadow boundary crossings for solar eclipses) around an
already-known instant of greatest eclipse.

All searches are anchored at `greatest_eclipse_time` (see
api.services.eclipse_detection.find_greatest_eclipse_time), since the raw new/full
moon instant can differ from the true greatest-eclipse instant by hours.

Geocentric-only (not observer-specific), consistent with the rest of this API.
"""

import numpy as np
import astropy.units as u

from api.services.eclipse_detection import (
    R_EARTH_KM,
    get_sun_moon_parameters,
    calculate_earth_shadow_cone,
    calculate_moon_shadow_cone,
)


def _bisect_crossing(margin_fn, t_low, t_high, iterations=50):
    """
    Find the time at which margin_fn(t) crosses zero, given margin_fn(t_low) and
    margin_fn(t_high) have opposite signs (bracketing the root). Uses bisection.

    Args:
        margin_fn: callable(astropy Time) -> float
        t_low, t_high: astropy Time objects bracketing a sign change
        iterations: number of bisection steps (50 narrows to sub-millisecond precision)

    Returns:
        astropy Time object at the approximate crossing instant
    """
    f_low = margin_fn(t_low)
    for _ in range(iterations):
        t_mid = t_low + (t_high - t_low) / 2
        f_mid = margin_fn(t_mid)
        if (f_mid > 0) == (f_low > 0):
            t_low = t_mid
            f_low = f_mid
        else:
            t_high = t_mid
    return t_low + (t_high - t_low) / 2


def _find_crossing_before(margin_fn, t0, window):
    """Search backward from t0 (where margin_fn(t0) > 0) for a zero-crossing."""
    if margin_fn(t0) <= 0:
        return None
    t_search = t0 - window
    if margin_fn(t_search) > 0:
        return None
    return _bisect_crossing(margin_fn, t_search, t0)


def _find_crossing_after(margin_fn, t0, window):
    """Search forward from t0 (where margin_fn(t0) > 0) for a zero-crossing."""
    if margin_fn(t0) <= 0:
        return None
    t_search = t0 + window
    if margin_fn(t_search) > 0:
        return None
    return _bisect_crossing(margin_fn, t0, t_search)


def calculate_lunar_contact_times(greatest_eclipse_time, search_window_hours=6):
    """
    Compute penumbral/umbral contact times for a lunar eclipse.

    Args:
        greatest_eclipse_time: astropy Time at the instant of greatest eclipse
        search_window_hours: half-width (hours) to search for each contact,
            outward from greatest_eclipse_time

    Returns:
        dict with ISO datetime strings for p1, u1, u2, u3, u4, p4 (None if that
        contact does not occur, e.g. u2/u3 are None unless the eclipse is TOTAL)
    """
    def shadow_params(t):
        params = get_sun_moon_parameters(t)
        shadow = calculate_earth_shadow_cone(t)
        return (
            params['moon_ang_radius_deg'],
            params['antisolar_separation_deg'],
            shadow['umbral_radius_ang'],
            shadow['penumbral_radius_ang'],
        )

    def penumbral_margin(t):
        moon_r, sep, _umbral_r, penumbral_r = shadow_params(t)
        return (penumbral_r + moon_r) - sep

    def umbral_margin(t):
        moon_r, sep, umbral_r, _penumbral_r = shadow_params(t)
        return (umbral_r + moon_r) - sep

    def total_margin(t):
        moon_r, sep, umbral_r, _penumbral_r = shadow_params(t)
        return (umbral_r - moon_r) - sep

    t0 = greatest_eclipse_time
    window = search_window_hours * u.hour

    p1 = _find_crossing_before(penumbral_margin, t0, window)
    p4 = _find_crossing_after(penumbral_margin, t0, window)
    u1 = _find_crossing_before(umbral_margin, t0, window)
    u4 = _find_crossing_after(umbral_margin, t0, window)
    u2 = _find_crossing_before(total_margin, t0, window)
    u3 = _find_crossing_after(total_margin, t0, window)

    return {
        'p1': p1.iso if p1 is not None else None,
        'u1': u1.iso if u1 is not None else None,
        'u2': u2.iso if u2 is not None else None,
        'u3': u3.iso if u3 is not None else None,
        'u4': u4.iso if u4 is not None else None,
        'p4': p4.iso if p4 is not None else None,
    }


def calculate_solar_contact_times(greatest_eclipse_time, search_window_hours=3):
    """
    Compute global contact times for a solar eclipse: the instants when the
    penumbral/central (umbral or antumbral) shadow first/last touches Earth's
    surface ANYWHERE. This is geocentric-only (not observer-specific) -
    consistent with the rest of this API. It answers "when does the eclipse
    begin/end as seen from somewhere on Earth", not "when does it begin/end at
    a specific location".

    Args:
        greatest_eclipse_time: astropy Time at the instant of greatest eclipse
        search_window_hours: half-width (hours) to search for each contact,
            outward from greatest_eclipse_time

    Returns:
        dict with ISO datetime strings for eclipse_begins, central_phase_begins,
        central_phase_ends, eclipse_ends (central_phase_* are None unless the
        eclipse is TOTAL or ANNULAR somewhere)
    """
    def offset_and_thresholds(t):
        params = get_sun_moon_parameters(t)
        shadow = calculate_moon_shadow_cone(t)
        offset_km = params['moon_dist_km'] * np.radians(params['sun_moon_separation_deg'])
        penumbral_threshold_km = shadow['penumbral_radius_km'] + R_EARTH_KM
        central_threshold_km = abs(shadow['umbral_radius_km']) + R_EARTH_KM
        return offset_km, penumbral_threshold_km, central_threshold_km

    def penumbral_margin(t):
        offset_km, penumbral_thr, _central_thr = offset_and_thresholds(t)
        return penumbral_thr - offset_km

    def central_margin(t):
        offset_km, _penumbral_thr, central_thr = offset_and_thresholds(t)
        return central_thr - offset_km

    t0 = greatest_eclipse_time
    window = search_window_hours * u.hour

    eclipse_begins = _find_crossing_before(penumbral_margin, t0, window)
    eclipse_ends = _find_crossing_after(penumbral_margin, t0, window)
    central_begins = _find_crossing_before(central_margin, t0, window)
    central_ends = _find_crossing_after(central_margin, t0, window)

    return {
        'eclipse_begins': eclipse_begins.iso if eclipse_begins is not None else None,
        'central_phase_begins': central_begins.iso if central_begins is not None else None,
        'central_phase_ends': central_ends.iso if central_ends is not None else None,
        'eclipse_ends': eclipse_ends.iso if eclipse_ends is not None else None,
    }
