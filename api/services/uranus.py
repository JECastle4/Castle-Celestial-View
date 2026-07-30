"""
Uranus position calculation service.

This module provides Uranus position calculations using shared common_bodies
utilities for topocentric position and outer_planets utilities for retrograde
motion detection.
"""
from typing import Optional

from api.models import ObservationDateTime, LocationModel
from api.services.common_bodies import _process_body_position
from api.services.outer_planets import (
    calculate_outer_planet_position,
    get_retrograde_status
)


def calculate_uranus_position(
    observation_time: ObservationDateTime,
    location: LocationModel,
    locale: Optional[str] = None
) -> dict:
    """
    Calculate Uranus's position at a given time and location.

    Args:
        observation_time: Date and time of observation
        location: Observer location (latitude, longitude, elevation)
        locale: Language locale code (e.g., 'en', 'en-US'); defaults to 'en'

    Returns:
        Dictionary containing:
            - altitude: Uranus's altitude in degrees (negative = below horizon)
            - azimuth: Uranus's azimuth in degrees (0=North, 90=East, 180=South, 270=West)
            - is_visible: Boolean indicating if Uranus is above horizon
            - ra_degrees: Uranus's right ascension in degrees (topocentric, observer-dependent)
            - dec_degrees: Uranus's declination in degrees (topocentric, observer-dependent)
            - retrograde_status: Whether Uranus is in retrograde motion from Earth's
              perspective ("prograde" or "retrograde")
            - julian_date: The JD for this calculation
            - input_datetime: The processed input string
            - location: Dictionary with lat, lon, elevation

    Raises:
        ValueError: If date/time format is invalid or coordinates out of range
    """
    return calculate_outer_planet_position(observation_time, location, "uranus", locale)


def _process_uranus_position(
    uranus_with_loc,
    uranus_altaz,
    uranus_gcrs,
    time,
    datetime_str: str,
    location: LocationModel,
    retrograde_status: Optional[str] = None
) -> dict:
    """
    Process Uranus position data into response format.
    Internal function used by batch operations.

    Args:
        uranus_with_loc: Uranus position in topocentric GCRS frame
        uranus_altaz: Uranus position in AltAz frame
        uranus_gcrs: Uranus position (GCRS coordinates) - used for retrograde
        time: Astropy Time object
        datetime_str: Input datetime string
        location: Observer location
        retrograde_status: Optional pre-computed retrograde status (for batch ops)

    Returns:
        Dictionary with Uranus position data
    """
    # Format base position data
    position_dict = _process_body_position(
        uranus_altaz, uranus_with_loc, time, datetime_str, location
    )

    # Add retrograde status (pre-computed in batch, calculated on-demand)
    if retrograde_status is None:
        retrograde_status = get_retrograde_status(uranus_gcrs, time, "uranus")

    position_dict["retrograde_status"] = retrograde_status

    return position_dict
