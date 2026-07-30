"""Moon position calculation service."""

from astropy.time import Time
from astropy.coordinates import get_body
from api.models import ObservationDateTime, LocationModel
from api.services.common_bodies import _setup_coordinates, _process_body_position


def calculate_moon_position(
    observation_time: ObservationDateTime,
    location: LocationModel,
) -> dict:
    """
    Calculate the moon's position (altitude and azimuth) from a given location on Earth.

    Args:
        observation_time: Date and time of observation
        location: Observer location (latitude, longitude, elevation)

    Returns:
        dict: Dictionary containing:
            - altitude: Moon's altitude in degrees (-90 to 90)
            - azimuth: Moon's azimuth in degrees (0 to 360)
            - is_visible: Boolean indicating if moon is above horizon
            - julian_date: Julian Date of the observation
            - location: Dict with latitude, longitude, elevation
            - input_datetime: Original input datetime string

    Raises:
        ValueError: If date/time format is invalid or coordinates out of range
    """
    obs_time, earth_location, altaz_frame, datetime_str = _setup_coordinates(
        observation_time, location
    )

    # Get moon position in topocentric (observer-dependent) GCRS coordinates
    # Since earth_location is provided, this includes parallax based on observer location
    moon_gcrs = get_body("moon", obs_time, earth_location)

    # Convert to AltAz frame for the given location and time
    moon_altaz = moon_gcrs.transform_to(altaz_frame)

    return _process_moon_position(moon_gcrs, moon_altaz, obs_time, datetime_str, location)


def _process_moon_position(
    moon_gcrs,
    moon_altaz,
    time: Time,
    datetime_str: str,
    location: LocationModel
) -> dict:
    """
    Process moon position data into response format.
    Internal function used by calculate_moon_position and batch operations.

    Args:
        moon_gcrs: Moon position in topocentric GCRS frame (observer-dependent, includes parallax)
        moon_altaz: Moon position in AltAz frame (for altitude/azimuth)
        time: Astropy Time object
        datetime_str: Input datetime string
        location: Observer location with latitude, longitude, elevation

    Returns:
        Dictionary with moon position data
    """
    return _process_body_position(moon_altaz, moon_gcrs, time, datetime_str, location)
