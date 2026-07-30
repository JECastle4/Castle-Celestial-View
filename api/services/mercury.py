"""
Mercury position calculation service.

This module provides Mercury position calculations using shared inferior_planets
utilities for phase angle, illumination, elongation, and naked-eye visibility.
"""
from typing import Optional

from api.models import ObservationDateTime, LocationModel
from api.services.inferior_planets import (
    calculate_inferior_planet_position,
    _process_inferior_planet_position,
)


def calculate_mercury_position(
    observation_time: ObservationDateTime,
    location: LocationModel,
    locale: Optional[str] = None
) -> dict:
    """
    Calculate Mercury's position and phase at a given time and location.

    Args:
        observation_time: Date and time of observation
        location: Observer location (latitude, longitude, elevation)
        locale: Language locale code (e.g., 'en', 'en-US'); defaults to 'en'

    Returns:
        Dictionary containing:
            - altitude: Mercury's altitude in degrees (negative = below horizon)
            - azimuth: Mercury's azimuth in degrees (0=North, 90=East, 180=South, 270=West)
            - is_visible: Boolean indicating if Mercury is above horizon
            - illumination: Fraction of Mercury's disk illuminated by the Sun (0.0 to 1.0),
              computed using Mercury-centric phase angle (IAU standard for inferior planets).
              Ranges from ~0% at inferior conjunction (closest to Earth) to ~100% at
              superior conjunction (behind the Sun).
            - phase_angle: Mercury's phase angle in ecliptic longitude (0 to 360 degrees),
              used to determine waxing vs waning
            - phase_name: Textual name of the phase based on illumination:
              New (0-10%), Crescent (10-35%), Quarter (35-50%),
              Gibbous (50-90%), Full (90%+)
            - sun_separation: Angular separation between Mercury and Sun in degrees (elongation)
            - naked_eye_visible: Boolean indicating if Mercury is observable to naked eye
              (requires altitude > 0° AND sun_separation > 14.5°; Mercury's minimum elongation)
            - julian_date: The JD for this calculation
            - input_datetime: The processed input string
            - location: Dictionary with lat, lon, elevation

    Raises:
        ValueError: If date/time format is invalid or coordinates out of range
    """
    return calculate_inferior_planet_position(observation_time, location, "mercury", locale)


def _process_mercury_position(
    mercury_with_loc,
    mercury_altaz,
    sun,
    mercury_gcrs,
    time,
    datetime_str: str,
    location: LocationModel,
    locale: Optional[str] = None
) -> dict:
    """
    Process Mercury position data into response format.
    Internal function used by calculate_mercury_position and batch operations.

    Args:
        mercury_with_loc: Mercury position in topocentric GCRS frame
            (observer-dependent, includes parallax)
        mercury_altaz: Mercury position in AltAz frame
        sun: Sun position (GCRS coordinates)
        mercury_gcrs: Mercury position (GCRS coordinates)
        time: Astropy Time object
        datetime_str: Input datetime string
        location: Observer location with latitude, longitude, elevation
        locale: Language locale code for phase names (defaults to 'en')

    Returns:
        Dictionary with Mercury position data
    """
    return _process_inferior_planet_position(
        mercury_with_loc, mercury_altaz, sun, mercury_gcrs, time, datetime_str, location,
        "mercury", locale=locale
    )
