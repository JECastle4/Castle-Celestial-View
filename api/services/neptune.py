"""
Neptune position calculation service.

This module provides Neptune position calculations using shared common_bodies
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


def calculate_neptune_position(
    observation_time: ObservationDateTime,
    location: LocationModel,
    locale: Optional[str] = None
) -> dict:
    """
    Calculate Neptune's position at a given time and location.

    Args:
        observation_time: Date and time of observation
        location: Observer location (latitude, longitude, elevation)
        locale: Language locale code (e.g., 'en', 'en-US'); defaults to 'en'

    Returns:
        Dictionary containing:
            - altitude: Neptune's altitude in degrees (negative = below horizon)
            - azimuth: Neptune's azimuth in degrees (0=North, 90=East, 180=South, 270=West)
            - is_visible: Boolean indicating if Neptune is above horizon
            - ra_degrees: Neptune's right ascension in degrees (topocentric, observer-dependent)
            - dec_degrees: Neptune's declination in degrees (topocentric, observer-dependent)
            - retrograde_status: Whether Neptune is in retrograde motion from Earth's
              perspective ("prograde" or "retrograde")
            - julian_date: The JD for this calculation
            - input_datetime: The processed input string
            - location: Dictionary with lat, lon, elevation

    Raises:
        ValueError: If date/time format is invalid or coordinates out of range
    """
    return calculate_outer_planet_position(observation_time, location, "neptune", locale)


def _process_neptune_position(
    neptune_with_loc,
    neptune_altaz,
    neptune_gcrs,
    time,
    datetime_str: str,
    location: LocationModel,
    retrograde_status: Optional[str] = None
) -> dict:
    """
    Process Neptune position data into response format.
    Internal function used by batch operations.

    Args:
        neptune_with_loc: Neptune position in topocentric GCRS frame
        neptune_altaz: Neptune position in AltAz frame
        neptune_gcrs: Neptune position (GCRS coordinates) - used for retrograde
        time: Astropy Time object
        datetime_str: Input datetime string
        location: Observer location
        retrograde_status: Optional pre-computed retrograde status (for batch ops)

    Returns:
        Dictionary with Neptune position data
    """
    # Format base position data
    position_dict = _process_body_position(
        neptune_altaz, neptune_with_loc, time, datetime_str, location
    )

    # Add retrograde status (pre-computed in batch, calculated on-demand)
    if retrograde_status is None:
        retrograde_status = get_retrograde_status(neptune_gcrs, time, "neptune")

    position_dict["retrograde_status"] = retrograde_status

    return position_dict
