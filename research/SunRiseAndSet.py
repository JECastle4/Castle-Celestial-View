"""Compute sunrise and sunset times for a given location and date.

This module provides functions to calculate sunrise and sunset times using
astronomical algorithms and the Astropy library.
"""
from astropy.time import Time
from astropy.coordinates import EarthLocation, AltAz, get_sun
import astropy.units as u
import numpy as np


def _compute_sun_altitudes(
        midday: Time,
        location: EarthLocation,
        target_altitude: u.Quantity):
    """Compute Sun altitudes over a 24-hour period centered on midday.

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
        Index of solar noon (maximum altitude).
    """
    # build a coarse time grid over +/- 12 hours
    hours = np.linspace(-12, 12, 241)  # 0.1 hour steps (~6 minutes)
    times = midday + hours * u.hour

    # vectorized altitude computation
    suncoords = get_sun(times)
    altaz = suncoords.transform_to(AltAz(obstime=times, location=location))
    altitudes = altaz.alt.to(u.deg)

    # target difference
    diffs = altitudes - target_altitude.to(u.deg)

    # find solar noon (time of maximum altitude)
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
        True for sunrise (ascending), False for sunset (descending).

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
            # For sunrise: move left if below target, right if above
            if mid_val < 0:
                left = mid
            else:
                right = mid
        else:
            # For sunset: move left if above target, right if below
            if mid_val > 0:
                left = mid
            else:
                right = mid

    return right


def sunrise(
        location: EarthLocation,
        julianDate: float,
        target_altitude: u.Quantity = -0.833 * u.deg,
        tolerance: u.Quantity = 1 * u.second):
    """Estimate sunrise time (UTC) for a given EarthLocation and Julian date.

    Parameters
    ----------
    location : EarthLocation
        Observer location.
    julianDate : float
        Any Julian date for the desired date (the function uses the date's
        noon UTC as a reference).
    target_altitude : astropy.units.Quantity, optional
        The geometric altitude to consider "rise" (default -0.833 deg
        accounts for refraction and Sun radius).
    tolerance : astropy.units.Quantity, optional
        Desired accuracy for the returned time (default 1 second).

    Returns
    -------
    astropy.time.Time or None
        The estimated UTC Time of sunrise, or ``None`` if the Sun does not
        rise on that date for the location (e.g., polar day/night).
    """
    # reference midday UTC for the given julianDate
    midday = Time(julianDate, format='jd', scale='utc') + 0.5 * u.day

    # compute altitudes over the day
    times, diffs, noon_idx = _compute_sun_altitudes(
        midday, location, target_altitude)

    # find the first index (from start up to noon) where altitude >= target
    # (morning crossing)
    morning_zone = diffs[: noon_idx + 1]
    nonneg = np.where(morning_zone >= 0)[0]
    if nonneg.size == 0:
        # no crossing before noon: sun either always above (polar day) or
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
            return None  # Circumpolar: sun stays above target all day

    # refine the crossing time
    return _refine_crossing_time(
        left, right, location, target_altitude, tolerance, ascending=True)


def sunset(
        location: EarthLocation,
        julianDate: float,
        target_altitude: u.Quantity = -0.833 * u.deg,
        tolerance: u.Quantity = 1 * u.second):
    """Estimate sunset time (UTC) for a given EarthLocation and Julian date.

    This searches *after* solar noon for the time the Sun descends through
    the `target_altitude`.

    Parameters
    ----------
    location : EarthLocation
        Observer location.
    julianDate : float
        Any Julian date for the desired date (the function uses the date's
        noon UTC as a reference).
    target_altitude : astropy.units.Quantity, optional
        The geometric altitude to consider "set" (default -0.833 deg
        accounts for refraction and Sun radius).
    tolerance : astropy.units.Quantity, optional
        Desired accuracy for the returned time (default 1 second).

    Returns
    -------
    astropy.time.Time or None
        The estimated UTC Time of sunset, or ``None`` if the Sun does not
        set on that date for the location (e.g., polar day/night).
    """
    # reference midday UTC for the given julianDate
    midday = Time(julianDate, format='jd', scale='utc') + 0.5 * u.day

    # compute altitudes over the day
    times, diffs, noon_idx = _compute_sun_altitudes(
        midday, location, target_altitude)

    # look for the first time after (or at) noon where altitude goes
    # below or equal to target
    evening_zone = diffs[noon_idx:]
    leq = np.where(evening_zone <= 0)[0]
    if leq.size == 0:
        # no crossing after noon: sun either always above (polar day) or
        # always below (polar night)
        return None if np.all(diffs > 0) else None

    rel_idx = int(leq[0])
    if rel_idx == 0:
        # already below (or at) target at noon -> no sunset later
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
            return None  # Sun never rises above target

    if right_val > 0:
        # Step right to find sign change
        j = abs_idx + 1
        while j < len(times) and right_val > 0:
            right = times[j]
            right_val = alt_at(right, location) - target_deg
            j += 1
        if right_val > 0:
            return None  # Sun stays above target (circumpolar)

    # refine the crossing time
    return _refine_crossing_time(
        left, right, location, target_altitude, tolerance, ascending=False)


def alt_at(t: Time, location) -> float:
    """Compute Sun altitude at a scalar Time for a given location.

    Parameters
    ----------
    t : Time
        The time at which to compute the altitude.
    location : EarthLocation
        Observer location.

    Returns
    -------
    float
        Sun altitude in degrees.
    """
    sun_altaz = get_sun(t).transform_to(
        AltAz(obstime=t, location=location))
    return sun_altaz.alt.to(u.deg).value
