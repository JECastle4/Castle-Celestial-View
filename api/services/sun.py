"""
Sun position calculation services
"""
from astropy.coordinates import get_sun
from astropy.time import Time
from api.models import ObservationDateTime, LocationModel
from api.services.common_bodies import _setup_coordinates, _process_body_position


def calculate_sun_position(
    observation_time: ObservationDateTime,
    location: LocationModel
) -> dict:
    """
    Calculate the sun's position at a given time and location.

    Args:
        observation_time: Date and time of observation
        location: Observer location (latitude, longitude, elevation)

    Returns:
        Dictionary containing:
            - altitude: Sun's altitude in degrees (negative = below horizon)
            - azimuth: Sun's azimuth in degrees (0=North, 90=East, 180=South, 270=West)
            - is_visible: Boolean indicating if sun is above horizon
            - julian_date: The JD for this calculation
            - input_datetime: The processed input string
            - location: Dictionary with lat, lon, elevation

    Raises:
        ValueError: If date/time format is invalid or coordinates out of range
    """
    obs_time, _, altaz_frame, datetime_str = _setup_coordinates(observation_time, location)

    # Get sun position in geocentric (GCRS) and AltAz coordinates
    sun_gcrs = get_sun(obs_time)
    sun_altaz = sun_gcrs.transform_to(altaz_frame)

    return _process_sun_position(sun_gcrs, sun_altaz, obs_time, datetime_str, location)


def _process_sun_position(
    sun_gcrs,
    sun_altaz,
    time: Time,
    datetime_str: str,
    location: LocationModel
) -> dict:
    """
    Process sun position data into response format.
    Internal function used by calculate_sun_position and batch operations.

    Args:
        sun_gcrs: Sun position in geocentric GCRS frame (for accurate RA/Dec)
        sun_altaz: Sun position in AltAz frame (for altitude/azimuth)
        time: Astropy Time object
        datetime_str: Input datetime string
        location: Observer location with latitude, longitude, elevation

    Returns:
        Dictionary with sun position data
    """
    # sun_gcrs is geocentric (observer-independent); passed as the "with_loc" arg
    # here since the Sun's RA/Dec are the same to within sub-arcsecond precision
    # regardless of observer location.
    return _process_body_position(sun_altaz, sun_gcrs, time, datetime_str, location)
