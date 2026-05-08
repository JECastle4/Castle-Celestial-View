"""
Sun position calculation services
"""
from astropy.coordinates import get_sun, AltAz, EarthLocation
from astropy.time import Time
import astropy.units as u
from api.i18n import t


def calculate_sun_position(
    date_str: str, 
    time_str: str,
    latitude: float,
    longitude: float,
    elevation: float = 0.0
) -> dict:
    """
    Calculate the sun's position at a given time and location.
    
    Args:
        date_str: Date in ISO format (YYYY-MM-DD)
        time_str: Time in HH:MM:SS format
        latitude: Latitude in degrees (-90 to 90)
        longitude: Longitude in degrees (-180 to 180)
        elevation: Elevation above sea level in meters (defaults to 0.0)
    
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
    if not -90 <= latitude <= 90:
        raise ValueError(t('validation.latitudeRange', value=latitude))
    if not -180 <= longitude <= 180:
        raise ValueError(t('validation.longitudeRange', value=longitude))
    
    # Combine date and time (ISO 8601 format)
    datetime_str = f"{date_str}T{time_str}"
    
    # Convert to astropy Time
    obs_time = Time(datetime_str, format='isot', scale='utc')
    
    # Create Earth location
    location = EarthLocation(
        lat=latitude * u.deg,
        lon=longitude * u.deg,
        height=elevation * u.m
    )
    
    # Create AltAz frame (pressure=0 to ignore atmospheric refraction for simplicity)
    altaz_frame = AltAz(obstime=obs_time, location=location, pressure=0.0)
    
    # Get sun position and transform to AltAz coordinates
    sun_altaz = get_sun(obs_time).transform_to(altaz_frame)
    
    return _process_sun_position(sun_altaz, obs_time, datetime_str, latitude, longitude, elevation)


def _process_sun_position(
    sun_altaz,
    time: Time,
    datetime_str: str,
    latitude: float,
    longitude: float,
    elevation: float
) -> dict:
    """
    Process sun position data into response format.
    Internal function used by calculate_sun_position and batch operations.
    
    Args:
        sun_altaz: Sun position in AltAz frame
        time: Astropy Time object
        datetime_str: Input datetime string
        latitude: Latitude in degrees
        longitude: Longitude in degrees
        elevation: Elevation in meters
    
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
            "latitude": latitude,
            "longitude": longitude,
            "elevation": elevation
        }
    }
