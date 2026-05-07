"""Moon position calculation service."""

from astropy.time import Time
from astropy.coordinates import get_body, AltAz, EarthLocation
import astropy.units as u
from api.i18n import t


def calculate_moon_position(
    date_str: str,
    time_str: str,
    latitude: float,
    longitude: float,
    elevation: float = 0.0,
) -> dict:
    """
    Calculate the moon's position (altitude and azimuth) from a given location on Earth.

    Args:
        date_str: Date in ISO format (YYYY-MM-DD)
        time_str: Time in ISO format (HH:MM:SS)
        latitude: Latitude in degrees (-90 to 90)
        longitude: Longitude in degrees (-180 to 180)
        elevation: Elevation in meters (default: 0.0)

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
    if not -90 <= latitude <= 90:
        raise ValueError(t('validation.latitudeRange', value=latitude))
    if not -180 <= longitude <= 180:
        raise ValueError(t('validation.longitudeRange', value=longitude))
    
    # Combine date and time (ISO 8601 format)
    datetime_str = f"{date_str}T{time_str}"

    # Convert to astropy Time (assumes UTC)
    time = Time(datetime_str, format="isot", scale="utc")

    # Create location
    location = EarthLocation(
        lat=latitude * u.deg, lon=longitude * u.deg, height=elevation * u.m
    )

    # Get moon position
    moon = get_body("moon", time, location)

    # Convert to AltAz frame for the given location and time
    # (pressure=0 to ignore atmospheric refraction for simplicity)
    altaz_frame = AltAz(obstime=time, location=location, pressure=0.0)
    moon_altaz = moon.transform_to(altaz_frame)

    return _process_moon_position(moon_altaz, time, datetime_str, latitude, longitude, elevation)


def _process_moon_position(
    moon_altaz,
    time: Time,
    datetime_str: str,
    latitude: float,
    longitude: float,
    elevation: float
) -> dict:
    """
    Process moon position data into response format.
    Internal function used by calculate_moon_position and batch operations.
    
    Args:
        moon_altaz: Moon position in AltAz frame
        time: Astropy Time object
        datetime_str: Input datetime string
        latitude: Latitude in degrees
        longitude: Longitude in degrees
        elevation: Elevation in meters
    
    Returns:
        Dictionary with moon position data
    """
    # Extract altitude and azimuth
    altitude = float(moon_altaz.alt.deg)
    azimuth = float(moon_altaz.az.deg)

    # Determine visibility (above horizon means altitude > 0)
    is_visible = bool(altitude > 0)

    return {
        "altitude": altitude,
        "azimuth": azimuth,
        "is_visible": is_visible,
        "julian_date": float(time.jd),
        "location": {
            "latitude": latitude,
            "longitude": longitude,
            "elevation": elevation,
        },
        "input_datetime": datetime_str,
    }
