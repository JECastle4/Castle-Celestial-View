"""Compute Venus rise and set times for a given location and date.

This module provides functions to calculate Venus rise and set times using
the Astropy library, following the same pattern as sunrise/sunset calculations.
"""
from astropy.time import Time
from astropy.coordinates import EarthLocation, AltAz, get_body
import astropy.units as u
import numpy as np


def _compute_venus_altitudes(
        midday: Time,
        location: EarthLocation,
        target_altitude: u.Quantity):
    """Compute Venus altitudes over a 24-hour period centered on midday.

    Parameters
    ----------
    midday : Time
        Reference midday UTC time.
    location : EarthLocation
        Observer location.
    target_altitude : u.Quantity
        Target altitude for comparison.

    Returns
    -------
    times : Time array
        Array of times spanning +/- 12 hours from midday.
    diffs : Quantity array
        Difference between actual altitude and target altitude at each time.
    peak_idx : int
        Index of peak altitude.
    """
    # build a coarse time grid over +/- 12 hours
    hours = np.linspace(-12, 12, 241)  # 0.1 hour steps (~6 minutes)
    times = midday + hours * u.hour

    # vectorized altitude computation
    venus_coords = get_body("venus", times, location)
    altaz = venus_coords.transform_to(AltAz(obstime=times, location=location))
    altitudes = altaz.alt.to(u.deg)

    # target difference
    diffs = altitudes - target_altitude.to(u.deg)

    # find peak altitude
    peak_idx = int(np.argmax(altitudes.value))

    return times, diffs, peak_idx


def _refine_crossing_time(
        left: Time,
        right: Time,
        location: EarthLocation,
        target_altitude: u.Quantity,
        tolerance: u.Quantity,
        *,
        ascending: bool = True):
    """Refine crossing time using bisection method.

    Parameters
    ----------
    left : Time
        Left bound of the interval.
    right : Time
        Right bound of the interval.
    location : EarthLocation
        Observer location.
    target_altitude : u.Quantity
        Target altitude.
    tolerance : u.Quantity
        Desired time accuracy.
    ascending : bool, optional
        True for Venus rise (ascending), False for Venus set (descending).

    Returns
    -------
    Time
        Refined crossing time.
    """
    tol_days = tolerance.to(u.s).value / 86400.0
    target_deg = target_altitude.to(u.deg).value

    while (right.jd - left.jd) > tol_days:
        mid_jd = 0.5 * (left.jd + right.jd)
        mid = Time(mid_jd, format='jd', scale='utc')
        mid_val = alt_at(mid, location) - target_deg

        if ascending:
            # For rise: move left if below target, right if above
            if mid_val < 0:
                left = mid
            else:
                right = mid
        else:
            # For set: move left if above target, right if below
            if mid_val > 0:
                left = mid
            else:
                right = mid

    return right


def venus_rise(
        location: EarthLocation,
        julianDate: float,
        target_altitude: u.Quantity = 0.0 * u.deg,
        tolerance: u.Quantity = 1 * u.second,
        debug: bool = False):
    """Estimate Venus rise time (UTC) for a given EarthLocation and Julian date.

    Parameters
    ----------
    location : EarthLocation
        Observer location.
    julianDate : float
        Any Julian date for the desired date (the function uses the date's
        noon UTC as a reference).
    target_altitude : astropy.units.Quantity, optional
        The altitude to consider "rise" (default 0.0 deg for horizon).
    tolerance : astropy.units.Quantity, optional
        Desired accuracy for the returned time (default 1 second).
    debug : bool, optional
        Enable debug output (default False).

    Returns
    -------
    astropy.time.Time or None
        The estimated UTC Time of Venus rise, or ``None`` if Venus does not
        rise on that date for the location.
    """
    # reference midday UTC for the given julianDate
    # Normalize to noon UTC of the given date (JD.0 = noon UTC, so floor gives us the right day)
    midday = Time(np.floor(julianDate), format='jd', scale='utc')

    # compute altitudes over the day
    times, diffs, peak_idx = _compute_venus_altitudes(
        midday, location, target_altitude)

    if debug:
        print(f"  [DEBUG RISE] Midday: {midday.iso}")
        min_alt = np.min(diffs)
        max_alt = np.max(diffs)
        print(f"  [DEBUG RISE] Min altitude: {min_alt:.2f}°, Max altitude: {max_alt:.2f}°")

    # Search ENTIRE 24-hour window for negative→positive crossings (RISE)
    # Look for indices where diffs transitions from negative to non-negative
    neg_to_pos = np.where((diffs[:-1] < 0) & (diffs[1:] >= 0))[0]
    
    if debug:
        print(f"  [DEBUG RISE] Negative→positive crossings at indices: {neg_to_pos}")
    
    if len(neg_to_pos) == 0:
        if debug:
            min_alt = np.min(diffs)
            visibility = "CIRCUMPOLAR (always above)" if min_alt > 0 else "NEVER_RISES (always below)"
            print(f"  [DEBUG RISE] No rise crossing found ({visibility})")
        return None
    
    # Use the FIRST crossing (chronologically)
    idx = int(neg_to_pos[0])
    left = times[idx]
    right = times[idx + 1]
    
    if debug:
        print(f"  [DEBUG RISE] First rise crossing between times {left.iso} and {right.iso}")
    
    # Refine the crossing time
    rise_time = _refine_crossing_time(
        left, right, location, target_altitude, tolerance, ascending=True)
    
    if debug:
        rise_alt = alt_at(rise_time, location)
        print(f"  [DEBUG RISE] Refined: {rise_time.iso}, altitude: {rise_alt:.2f}°")
    
    return rise_time


def venus_set(
        location: EarthLocation,
        julianDate: float,
        target_altitude: u.Quantity = 0.0 * u.deg,
        tolerance: u.Quantity = 1 * u.second,
        debug: bool = False):
    """Estimate Venus set time (UTC) for a given EarthLocation and Julian date.

    This searches *after* peak altitude for the time Venus descends through
    the `target_altitude`.

    Parameters
    ----------
    location : EarthLocation
        Observer location.
    julianDate : float
        Any Julian date for the desired date (the function uses the date's
        noon UTC as a reference).
    target_altitude : astropy.units.Quantity, optional
        The altitude to consider "set" (default 0.0 deg for horizon).
    tolerance : astropy.units.Quantity, optional
        Desired accuracy for the returned time (default 1 second).
    debug : bool, optional
        Enable debug output (default False).

    Returns
    -------
    astropy.time.Time or None
        The estimated UTC Time of Venus set, or ``None`` if Venus does not
        set on that date for the location.
    """
    # reference midday UTC for the given julianDate
    # Normalize to noon UTC of the given date (JD.0 = noon UTC, so floor gives us the right day)
    midday = Time(np.floor(julianDate), format='jd', scale='utc')

    # compute altitudes over the day
    times, diffs, peak_idx = _compute_venus_altitudes(
        midday, location, target_altitude)

    if debug:
        print(f"  [DEBUG SET] Midday: {midday.iso}")
        min_alt = np.min(diffs)
        max_alt = np.max(diffs)
        print(f"  [DEBUG SET] Min altitude: {min_alt:.2f}°, Max altitude: {max_alt:.2f}°")

    # Search ENTIRE 24-hour window for positive→negative crossings (SET)
    # Look for indices where diffs transitions from non-negative to negative
    pos_to_neg = np.where((diffs[:-1] >= 0) & (diffs[1:] < 0))[0]
    
    if debug:
        print(f"  [DEBUG SET] Positive→negative crossings at indices: {pos_to_neg}")
    
    if len(pos_to_neg) == 0:
        if debug:
            min_alt = np.min(diffs)
            visibility = "CIRCUMPOLAR (always above)" if min_alt > 0 else "NEVER_RISES (always below)"
            print(f"  [DEBUG SET] No set crossing found ({visibility})")
        return None
    
    # Use the FIRST crossing (chronologically)
    idx = int(pos_to_neg[0])
    left = times[idx]
    right = times[idx + 1]
    
    if debug:
        print(f"  [DEBUG SET] First set crossing between times {left.iso} and {right.iso}")
    
    # Refine the crossing time
    set_time = _refine_crossing_time(
        left, right, location, target_altitude, tolerance, ascending=False)
    
    if debug:
        set_alt = alt_at(set_time, location)
        print(f"  [DEBUG SET] Refined: {set_time.iso}, altitude: {set_alt:.2f}°")
    
    return set_time


def _classify_visibility(midday: Time, location: EarthLocation, target_altitude: u.Quantity) -> str:
    """Determine why Venus does not cross the target altitude.

    Parameters
    ----------
    midday : Time
        Reference midday UTC time.
    location : EarthLocation
        Observer location.
    target_altitude : u.Quantity
        Target altitude for comparison.

    Returns
    -------
    str
        Either "CIRCUMPOLAR" (always above target) or "NEVER_RISES" (always below target).
    """
    times, diffs, _ = _compute_venus_altitudes(midday, location, target_altitude)
    
    min_alt = np.min(diffs)
    max_alt = np.max(diffs)
    
    if min_alt > 0:
        return "CIRCUMPOLAR"  # Venus never dips below target altitude
    else:
        return "NEVER_RISES"  # Venus never reaches target altitude


def alt_at(t: Time, location: EarthLocation) -> float:
    """Compute Venus altitude at a scalar Time for a given location.

    Parameters
    ----------
    t : Time
        The time at which to compute the altitude.
    location : EarthLocation
        Observer location.

    Returns
    -------
    float
        Venus altitude in degrees.
    """
    venus_altaz = get_body("venus", t, location).transform_to(
        AltAz(obstime=t, location=location))
    return venus_altaz.alt.to(u.deg).value
