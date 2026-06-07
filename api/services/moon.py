"""Moon position calculation service."""

from astropy.time import Time
from astropy.coordinates import get_body, AltAz, EarthLocation
import astropy.units as u
from api.i18n import t
from api.models import ObservationDateTime, LocationModel


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
    # Validate coordinates
    if not -90 <= location.latitude <= 90:
        raise ValueError(t('validation.latitudeRange', value=location.latitude))
    if not -180 <= location.longitude <= 180:
        raise ValueError(t('validation.longitudeRange', value=location.longitude))

    # Combine date and time (ISO 8601 format)
    datetime_str = f"{observation_time.date}T{observation_time.time}Z"

    # Convert to astropy Time (assumes UTC)
    time = Time(datetime_str.rstrip('Z'), format="isot", scale="utc")

    # Create Earth location
    earth_location = EarthLocation(
        lat=location.latitude * u.deg, lon=location.longitude * u.deg,
        height=location.elevation * u.m
    )

    # Get moon position in topocentric (observer-dependent) GCRS coordinates
    # Since earth_location is provided, this includes parallax based on observer location
    moon_gcrs = get_body("moon", time, earth_location)

    # Convert to AltAz frame for the given location and time
    # (pressure=0 to ignore atmospheric refraction for simplicity)
    altaz_frame = AltAz(obstime=time, location=earth_location, pressure=0.0)
    moon_altaz = moon_gcrs.transform_to(altaz_frame)

    return _process_moon_position(moon_gcrs, moon_altaz, time, datetime_str, location)


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
    # Extract altitude and azimuth
    altitude = float(moon_altaz.alt.deg)
    azimuth = float(moon_altaz.az.deg)

    # Determine visibility (above horizon means altitude > 0)
    is_visible = bool(altitude > 0)

    # Extract RA/Dec in GCRS frame (topocentric, observer-dependent)
    # Moon coordinates from get_body('moon', obstime, location=earth_location) are
    # topocentric and account for parallax based on observer location.
    # GCRS is the standard celestial reference frame used by astropy
    ra_degrees = float(moon_gcrs.ra.degree)
    dec_degrees = float(moon_gcrs.dec.degree)

    return {
        "altitude": altitude,
        "azimuth": azimuth,
        "is_visible": is_visible,
        "ra_degrees": ra_degrees,
        "dec_degrees": dec_degrees,
        "julian_date": float(time.jd),
        "location": {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "elevation": location.elevation,
        },
        "input_datetime": datetime_str,
    }
