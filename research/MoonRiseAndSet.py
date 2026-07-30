"""Compute moonrise and moonset times for a given location and date.

This module provides functions to calculate moonrise and moonset times using
astronomical algorithms and the Astropy library.
"""
from typing import List, Tuple, Literal

from astropy.time import Time
from astropy.coordinates import EarthLocation, AltAz, get_body
import astropy.units as u
import numpy as np


def _compute_moon_altitudes(
        midday: Time,
        location: EarthLocation,
        target_altitude: u.Quantity):
    """Compute Moon altitudes over a 24-hour period centered on midday.

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
    noon_idx : int
        Index of lunar noon (maximum altitude).
    """
    # build a coarse time grid over +/- 12 hours
    hours = np.linspace(-12, 12, 241)  # 0.1 hour steps (~6 minutes)
    times = midday + hours * u.hour

    # vectorized altitude computation
    mooncoords = get_body("moon", times)
    altaz = mooncoords.transform_to(AltAz(obstime=times, location=location))
    altitudes = altaz.alt.to(u.deg)

    # target difference
    diffs = altitudes - target_altitude.to(u.deg)

    # find lunar noon (time of maximum altitude)
    noon_idx = int(np.argmax(altitudes.value))

    return times, diffs, noon_idx


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
        True for moonrise (ascending), False for moonset (descending).

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
            # For moonrise: move left if below target, right if above
            if mid_val < 0:
                left = mid
            else:
                right = mid
        else:
            # For moonset: move left if above target, right if below
            if mid_val > 0:
                left = mid
            else:
                right = mid

    return right


def moonrise(
        location: EarthLocation,
        julianDate: float,
        target_altitude: u.Quantity = -0.816 * u.deg,
        tolerance: u.Quantity = 1 * u.second):
    """Estimate moonrise time (UTC) for a given EarthLocation and Julian date.

    Parameters
    ----------
    location : EarthLocation
        Observer location.
    julianDate : float
        Any Julian date for the desired date (the function uses the
        date's noon UTC as a reference).
    target_altitude : astropy.units.Quantity, optional
        The geometric altitude to consider "rise" (default -0.833 deg
        accounts for refraction and Moon radius).
    tolerance : astropy.units.Quantity, optional
        Desired accuracy for the returned time (default 1 second).

    Returns
    -------
    astropy.time.Time or None
        The estimated UTC Time of moonrise, or ``None`` if the Moon does
        not rise on that date for the location (e.g., polar day/night).
    """
    # reference midday UTC for the given julianDate
    midday = Time(julianDate, format='jd', scale='utc') + 0.5 * u.day

    # compute altitudes over the day
    times, diffs, noon_idx = _compute_moon_altitudes(
        midday, location, target_altitude)

    # find the first index (from start up to noon) where altitude >= target
    # (morning crossing)
    morning_zone = diffs[: noon_idx + 1]
    nonneg = np.where(morning_zone >= 0)[0]
    if nonneg.size == 0:
        # no crossing before noon: moon either always above (polar day) or
        # always below (polar night)
        return None if np.all(diffs > 0) else None

    idx = int(nonneg[0])
    if idx == 0:
        left = times[0]
        right = times[1]
    else:
        left = times[idx - 1]
        right = times[idx]

    # Defensive check: ensure we have a proper crossing
    left_val = alt_at(left, location) - target_altitude.to(u.deg).value
    if left_val > 0:
        # Step left to find sign change
        j = idx - 1
        while j >= 0 and left_val > 0:
            left = times[j]
            left_val = alt_at(left, location) - target_altitude.to(u.deg).value
            j -= 1
        if left_val > 0:
            return None  # Circumpolar: moon stays above target all day

    # refine the crossing time
    return _refine_crossing_time(
        left, right, location, target_altitude, tolerance, ascending=True)

def moonset(
        location: EarthLocation,
        julianDate: float,
        target_altitude: u.Quantity = -0.833 * u.deg,
        tolerance: u.Quantity = 1 * u.second):
    """Estimate moonset time (UTC) for a given EarthLocation and Julian date.

    This searches *after* solar noon for the time the Moon descends
    through the `target_altitude`.

    Parameters
    ----------
    location : EarthLocation
        Observer location.
    julianDate : float
        Any Julian date for the desired date (the function uses the
        date's noon UTC as a reference).
    target_altitude : astropy.units.Quantity, optional
        The geometric altitude to consider "set" (default -0.833 deg
        accounts for refraction and Moon radius).
    tolerance : astropy.units.Quantity, optional
        Desired accuracy for the returned time (default 1 second).

    Returns
    -------
    astropy.time.Time or None
        The estimated UTC Time of moonset, or ``None`` if the Moon does
        not set on that date for the location (e.g., polar day/night).
    """
    # reference midday UTC for the given julianDate
    midday = Time(julianDate, format='jd', scale='utc') + 0.5 * u.day

    # compute altitudes over the day
    times, diffs, noon_idx = _compute_moon_altitudes(
        midday, location, target_altitude)

    # look for the first time after (or at) noon where altitude goes
    # below or equal to target
    evening_zone = diffs[noon_idx:]
    leq = np.where(evening_zone <= 0)[0]
    if leq.size == 0:
        # no crossing after noon: moon either always above (polar day) or
        # always below (polar night)
        return None if np.all(diffs > 0) else None

    rel_idx = int(leq[0])
    if rel_idx == 0:
        # already below (or at) target at noon -> no moonset later
        return None

    abs_idx = noon_idx + rel_idx
    left = times[abs_idx - 1]
    right = times[abs_idx]

    # Defensive checks: ensure we have a proper crossing
    left_val = alt_at(left, location) - target_altitude.to(u.deg).value
    right_val = alt_at(right, location) - target_altitude.to(u.deg).value
    target_deg = target_altitude.to(u.deg).value

    if left_val < 0:
        # Step left to find sign change
        j = abs_idx - 2
        while j >= 0 and left_val < 0:  # pylint: disable=chained-comparison
            left = times[j]
            left_val = alt_at(left, location) - target_deg
            j -= 1
        if left_val < 0:
            return None  # Moon never rises above target

    if right_val > 0:
        # Step right to find sign change
        j = abs_idx + 1
        while j < len(times) and right_val > 0:
            right = times[j]
            right_val = alt_at(right, location) - target_deg
            j += 1
        if right_val > 0:
            return None  # Moon stays above target (circumpolar)

    # refine the crossing time
    return _refine_crossing_time(
        left, right, location, target_altitude, tolerance, ascending=False)


def alt_at(t: Time, location) -> float:
    """Compute Moon altitude at a scalar Time for a given location.

    Parameters
    ----------
    t : Time
        The time at which to compute the altitude.
    location : EarthLocation
        Observer location.

    Returns
    -------
    float
        Moon altitude in degrees.
    """
    moon_altaz = get_body("moon", t).transform_to(
        AltAz(obstime=t, location=location))
    return moon_altaz.alt.to(u.deg).value


def moon_semidiameter(moon_distance: u.Quantity) -> u.Quantity:
    """Compute the Moon's angular semidiameter given its distance.

    Parameters
    ----------
    moon_distance : astropy.units.Quantity
        Distance from observer to Moon center (typically in km or m).

    Returns
    -------
    astropy.units.Quantity
        Angular semidiameter in degrees.
    """
    r_moon = 1737.4 * u.km  # Moon's mean radius
    semidiameter_rad = np.arcsin(
        (r_moon / moon_distance).to(u.dimensionless_unscaled).value)
    return (semidiameter_rad * u.rad).to(u.deg)


def moon_target_altitude(
        location: EarthLocation,
        time: Time,
        refraction: u.Quantity = 0.566 * u.deg) -> u.Quantity:
    """Compute a recommended target altitude for moonrise/moonset at a given time.

    Combines atmospheric refraction and the Moon's instantaneous semidiameter.

    Parameters
    ----------
    location : EarthLocation
        Observer location.
    time : Time
        Reference time (typically near the expected rise/set event).
    refraction : astropy.units.Quantity, optional
        Atmospheric refraction at the horizon (default 0.566 deg ≈ 34 arcmin).

    Returns
    -------
    astropy.units.Quantity
        Target altitude = -(refraction + semidiameter), in degrees.
    """
    moon = get_body("moon", time, location=location)
    distance = moon.distance
    semidiam = moon_semidiameter(distance)
    return -(refraction + semidiam)


def find_altitude_crossings(
    position_func,
    location: EarthLocation,
    start_time: Time,
    end_time: Time,
    target_altitude: u.Quantity,
    coarse_step: u.Quantity = 5 * u.minute,
    tolerance: u.Quantity = 1 * u.second,
) -> List[Tuple[Time, Literal['rise', 'set']]]:
    """Find all altitude crossings of a celestial body within a time interval.

    Parameters
    ----------
    position_func : callable
        Function accepting Time (scalar or array) and returning SkyCoord for the body.
    location : EarthLocation
        Observer location.
    start_time : Time
        Start of search interval (UTC).
    end_time : Time
        End of search interval (UTC).
    target_altitude : astropy.units.Quantity
        The altitude threshold to detect crossings.
    coarse_step : astropy.units.Quantity, optional
        Coarse sampling interval (default 5 minutes).
    tolerance : astropy.units.Quantity, optional
        Desired accuracy for refined crossing times (default 1 second).

    Returns
    -------
    list of (Time, str)
        List of (crossing_time, event_type) tuples, where event_type is 'rise' or 'set'.
        Sorted chronologically.
    """
    # Build coarse time grid
    duration = (end_time - start_time).to(u.second)
    n_steps = int(np.ceil((duration / coarse_step).to(u.dimensionless_unscaled).value)) + 1
    times = start_time + np.linspace(0, duration.value, n_steps) * u.second

    # Vectorized altitude computation
    coords = position_func(times)
    altaz = coords.transform_to(AltAz(obstime=times, location=location))
    altitudes = altaz.alt.to(u.deg).value
    target_val = target_altitude.to(u.deg).value

    diffs = altitudes - target_val

    # Detect sign changes
    signs = np.sign(diffs)
    sign_changes = np.where(np.diff(signs) != 0)[0]

    if sign_changes.size == 0:
        return []

    # Helper: compute altitude at a single Time
    def alt_at_time(t: Time) -> float:
        c = position_func(t)
        return c.transform_to(AltAz(obstime=t, location=location)).alt.to(u.deg).value

    # Refine each bracket by bisection and determine rise/set
    crossings = []
    tol_days = tolerance.to(u.second).value / 86400.0

    for idx in sign_changes:
        left = times[idx]
        right = times[idx + 1]
        right_val = diffs[idx + 1]

        # Bisection refinement
        while (right.jd - left.jd) > tol_days:
            mid_jd = 0.5 * (left.jd + right.jd)
            mid = Time(mid_jd, format='jd', scale='utc')
            mid_val = alt_at_time(mid) - target_val
            if mid_val < 0:
                left = mid
            else:
                right = mid
                right_val = mid_val

        # Crossing time is the boundary where altitude transitions to >= target
        crossing_time = right if right_val >= 0 else left

        # Determine rise vs set by checking slope
        epsilon = 1 * u.minute
        t_before = crossing_time - epsilon
        t_after = crossing_time + epsilon
        alt_before = alt_at_time(t_before)
        alt_after = alt_at_time(t_after)
        slope = alt_after - alt_before

        event_type = 'rise' if slope > 0 else 'set'
        crossings.append((crossing_time, event_type))

    return crossings


def moon_rise_set(
    location: EarthLocation,
    julian_date: float,
    target_altitude: u.Quantity = -0.816 * u.deg,
    coarse_step: u.Quantity = 5 * u.minute,
    tolerance: u.Quantity = 1 * u.second,
) -> List[Tuple[Time, Literal['rise', 'set']]]:
    """Find all moonrise and moonset events for a given date and location.

    Searches a 24-hour window starting at local midnight (approximated as
    00:00 UTC on the given date). Uses topocentric Moon positions to
    account for parallax.

    Parameters
    ----------
    location : EarthLocation
        Observer location.
    date : Time
        Reference date (any time on the desired date; the function uses midnight UTC).
    target_altitude : astropy.units.Quantity, optional
        Altitude threshold for rise/set (default -0.816 deg includes refraction + semidiameter).
    coarse_step : astropy.units.Quantity, optional
        Sampling interval for coarse search (default 5 minutes).
    tolerance : astropy.units.Quantity, optional
        Time accuracy for refined crossing (default 1 second).

    Returns
    -------
    list of (Time, str)
        Chronologically sorted list of (time, event_type) where event_type is 'rise' or 'set'.
        May be empty if no crossings occur (e.g., Moon always above or below horizon).
    """
    # Define 24-hour search window starting at midnight UTC
    midnight = Time(julian_date, format='jd', scale='utc')
    start = midnight
    end = midnight + 24 * u.hour

    # Topocentric Moon position function
    def moon_position(times):
        return get_body('moon', times, location=location)

    return find_altitude_crossings(
        position_func=moon_position,
        location=location,
        start_time=start,
        end_time=end,
        target_altitude=target_altitude,
        coarse_step=coarse_step,
        tolerance=tolerance,
    )
