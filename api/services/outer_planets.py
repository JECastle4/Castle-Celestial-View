"""
Outer planets (Jupiter, Saturn, Uranus, Neptune) utilities and retrograde motion detection.

This module provides retrograde motion detection for the outer planets (superior planets that
orbit outside Earth's orbit). All outer planets share identical retrograde detection logic based
on heliocentric longitude rate of change.

Retrograde motion occurs annually for all outer planets when Earth overtakes them in their
orbits. Duration and cadence vary by planet distance.
"""
from typing import Optional

from astropy.coordinates import get_body, HeliocentricTrueEcliptic
from astropy.time import Time
import astropy.units as u

from api.models import ObservationDateTime, LocationModel
from api.services.common_bodies import (
    get_body_position,
    get_geocentric_body_coords,
    _setup_coordinates
)


OUTER_PLANETS = {"jupiter", "saturn", "uranus", "neptune"}


def get_retrograde_status(planet_gcrs, time: Time, planet_name: str) -> str:
    """
    Determine retrograde motion status for an outer planet.

    Uses heliocentric longitude rate of change: if the rate is negative (planet's
    heliocentric longitude is decreasing), the planet is in retrograde motion.

    This logic is identical across all outer planets and uses only the planet's
    geocentric coordinates and time (not observer-dependent).

    Args:
        planet_gcrs: Planet position in GCRS coordinates (geocentric coordinates
            from get_body(planet_name, time))
        time: Astropy Time object
        planet_name: Name of the planet ("jupiter", "saturn", "uranus", "neptune")
                     Used to fetch updated position at time + dt for rate calculation

    Returns:
        String: "retrograde" or "prograde"
    """
    # Validate planet name
    if planet_name.lower() not in OUTER_PLANETS:
        return "prograde"  # Fallback for non-outer planets

    # Use heliocentric true ecliptic coordinates for longitude calculation
    try:
        planet_hce = planet_gcrs.transform_to(HeliocentricTrueEcliptic(obstime=time))
        planet_lon = planet_hce.lon.degree

        # Small time step to compute rate of change (0.1 days ≈ 2.4 hours)
        dt_days = 0.1
        time_plus = time + dt_days * u.day
        planet_gcrs_plus = get_body(planet_name, time_plus)
        planet_hce_plus = planet_gcrs_plus.transform_to(HeliocentricTrueEcliptic(obstime=time_plus))
        planet_lon_plus = planet_hce_plus.lon.degree

        # Compute rate (degrees per day)
        # Handle wraparound at 0°/360° boundary
        d_lon = (planet_lon_plus - planet_lon) % 360
        if d_lon > 180:
            d_lon -= 360

        rate = d_lon / dt_days

        # Retrograde if rate is negative (longitude decreasing)
        return "retrograde" if rate < 0 else "prograde"
    except (ValueError, AttributeError):
        # Fallback if coordinate transformation fails; default to prograde
        return "prograde"


def calculate_outer_planet_position(
    observation_time: ObservationDateTime,
    location: LocationModel,
    planet_name: str,
    locale: Optional[str] = None
) -> dict:
    """
    Calculate position and retrograde status for an outer planet.

    Handles Jupiter, Saturn, Uranus, and Neptune.

    Combines generic topocentric position calculation (altitude, azimuth, RA/Dec)
    with outer-planet-specific retrograde motion detection.

    Args:
        observation_time: Date and time of observation
        location: Observer location (latitude, longitude, elevation)
        planet_name: Name of the planet ("jupiter", "saturn", "uranus", "neptune")
        locale: Language locale code (e.g., 'en', 'en-US'); defaults to 'en'

    Returns:
        Dictionary containing:
            - altitude: Planet's altitude in degrees (negative = below horizon)
            - azimuth: Planet's azimuth in degrees (0=North, 90=East, 180=South, 270=West)
            - is_visible: Boolean indicating if planet is above horizon
            - ra_degrees: Planet's right ascension in degrees (topocentric, observer-dependent)
            - dec_degrees: Planet's declination in degrees (topocentric, observer-dependent)
            - retrograde_status: Whether planet is in retrograde motion ("prograde" or "retrograde")
            - julian_date: The JD for this calculation
            - input_datetime: The processed input string
            - location: Dictionary with lat, lon, elevation

    Raises:
        ValueError: If date/time format is invalid or coordinates out of range
    """
    # Get topocentric position using common utility
    position_dict = get_body_position(observation_time, location, planet_name, locale)

    # Get geocentric coordinates needed for retrograde calculation
    obs_time, _, _, _ = _setup_coordinates(observation_time, location, locale)
    planet_gcrs = get_geocentric_body_coords(planet_name, obs_time)

    # Compute and add retrograde status
    position_dict['retrograde_status'] = get_retrograde_status(planet_gcrs, obs_time, planet_name)

    return position_dict
