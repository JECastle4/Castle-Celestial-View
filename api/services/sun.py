"""
Sun position calculation services
"""
from astropy.coordinates import get_sun, AltAz, EarthLocation
from astropy.time import Time
import astropy.units as u
from api.i18n import t
from api.models import ObservationDateTime, LocationModel


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
    # Validate coordinates
    if not -90 <= location.latitude <= 90:
        raise ValueError(t('validation.latitudeRange', value=location.latitude))
    if not -180 <= location.longitude <= 180:
        raise ValueError(t('validation.longitudeRange', value=location.longitude))

    # Combine date and time (ISO 8601 format)
    datetime_str = f"{observation_time.date}T{observation_time.time}"

    # Convert to astropy Time
    obs_time = Time(datetime_str, format='isot', scale='utc')

    # Create Earth location
    earth_location = EarthLocation(
        lat=location.latitude * u.deg,
        lon=location.longitude * u.deg,
        height=location.elevation * u.m
    )

    # Create AltAz frame (pressure=0 to ignore atmospheric refraction for simplicity)
    altaz_frame = AltAz(obstime=obs_time, location=earth_location, pressure=0.0)

    # Get sun position and transform to AltAz coordinates
    sun_altaz = get_sun(obs_time).transform_to(altaz_frame)

    return _process_sun_position(sun_altaz, obs_time, datetime_str, location)


def _process_sun_position(
    sun_altaz,
    time: Time,
    datetime_str: str,
    location: LocationModel
) -> dict:
    """
    Process sun position data into response format.
    Internal function used by calculate_sun_position and batch operations.

    Args:
        sun_altaz: Sun position in AltAz frame
        time: Astropy Time object
        datetime_str: Input datetime string
        location: Observer location with latitude, longitude, elevation

    Returns:
        Dictionary with sun position data
    """
    # Extract altitude and azimuth
    altitude = sun_altaz.alt.degree
    azimuth = sun_altaz.az.degree

    # Sun is visible if altitude is positive (above horizon)
    # Convert to Python bool to avoid numpy bool type
    is_visible = bool(altitude > 0)

    return {
        "altitude": float(altitude),
        "azimuth": float(azimuth),
        "is_visible": is_visible,
        "julian_date": float(time.jd),
        "input_datetime": datetime_str,
        "location": {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "elevation": location.elevation
        }
    }
