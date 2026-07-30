"""
Venus position calculation service.

This module provides Venus position calculations using shared inferior_planets
utilities for phase angle, illumination, elongation, and naked-eye visibility.
"""
from typing import Optional

from api.models import ObservationDateTime, LocationModel
from api.services.inferior_planets import (
    calculate_inferior_planet_position,
    _process_inferior_planet_position,
)


def calculate_venus_position(
    observation_time: ObservationDateTime,
    location: LocationModel,
    locale: Optional[str] = None
) -> dict:
    """
    Calculate Venus's position and phase at a given time and location.

    Args:
        observation_time: Date and time of observation
        location: Observer location (latitude, longitude, elevation)
        locale: Language locale code (e.g., 'en', 'en-US'); defaults to 'en'

    Returns:
        Dictionary containing:
            - altitude: Venus's altitude in degrees (negative = below horizon)
            - azimuth: Venus's azimuth in degrees (0=North, 90=East, 180=South, 270=West)
            - is_visible: Boolean indicating if Venus is above horizon
            - illumination: Fraction of Venus's disk illuminated by the Sun (0.0 to 1.0),
              computed using Venus-centric phase angle (IAU standard for inferior planets).
              Ranges from ~0% at inferior conjunction (closest to Earth) to ~100% at
              superior conjunction (behind the Sun).
            - phase_angle: Venus's phase angle in ecliptic longitude (0 to 360 degrees),
              used to determine waxing vs waning
            - phase_name: Textual name of the phase based on illumination:
              New (0-10%), Crescent (10-35%), Quarter (35-50%),
              Gibbous (50-90%), Full (90%+)
            - sun_separation: Angular separation between Venus and Sun in degrees (elongation)
            - naked_eye_visible: Boolean indicating if Venus is observable to naked eye
              (requires altitude > 0° AND sun_separation > 10°)
            - julian_date: The JD for this calculation
            - input_datetime: The processed input string
            - location: Dictionary with lat, lon, elevation

    Raises:
        ValueError: If date/time format is invalid or coordinates out of range
    """
    return calculate_inferior_planet_position(observation_time, location, "venus", locale)


def _process_venus_position(
    venus_with_loc,
    venus_altaz,
    sun,
    venus_gcrs,
    time,
    datetime_str: str,
    location: LocationModel,
    locale: Optional[str] = None
) -> dict:
    """
    Process Venus position data into response format.
    Internal function used by calculate_venus_position and batch operations.

    Args:
        venus_with_loc: Venus position in topocentric GCRS frame
            (observer-dependent, includes parallax)
        venus_altaz: Venus position in AltAz frame
        sun: Sun position (GCRS coordinates)
        venus_gcrs: Venus position (GCRS coordinates)
        time: Astropy Time object
        datetime_str: Input datetime string
        location: Observer location with latitude, longitude, elevation
        locale: Language locale code for phase names (defaults to 'en')

    Returns:
        Dictionary with Venus position data
    """
    return _process_inferior_planet_position(
        venus_with_loc, venus_altaz, sun, venus_gcrs, time, datetime_str, location,
        "venus", locale=locale
    )
