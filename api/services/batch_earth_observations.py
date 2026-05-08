"""Batch earth observations service for calculating multiple frames of celestial positions."""

from typing import Optional
from astropy.time import Time
from astropy.coordinates import get_sun, get_body, AltAz, EarthLocation
import astropy.units as u
from .sun import _process_sun_position
from .moon import _process_moon_position
from .moon_phase import _process_moon_phase
from api.i18n import get_i18n


def calculate_batch_earth_observations(
    start_date: str,
    start_time: str,
    end_date: str,
    end_time: str,
    frame_count: int,
    latitude: float,
    longitude: float,
    elevation: float = 0.0,
    locale: Optional[str] = None,
):
    """
    Calculate batch observations of sun and moon positions from Earth.
    
    This function generates multiple frames of celestial observations between
    a start and end time. Each frame contains sun position, moon position,
    and moon phase information for that specific moment.
    
    Args:
        start_date: Start date in ISO format (YYYY-MM-DD)
        start_time: Start time in ISO format (HH:MM:SS)
        end_date: End date in ISO format (YYYY-MM-DD)
        end_time: End time in ISO format (HH:MM:SS)
        frame_count: Number of frames to generate (must be >= 2)
        latitude: Observer latitude in degrees (-90 to 90)
        longitude: Observer longitude in degrees (-180 to 180)
        elevation: Observer elevation in meters (default: 0.0)
        locale: BCP 47 locale tag (e.g. 'en', 'xx-reverse') used to translate
            validation error messages and moon phase names in each frame.
            Defaults to English when None.
    
    Yields:
        dict: Frame data for each observation
        dict: Metadata after all frames
    """
    _t = get_i18n(locale).get
    # Validate frame count
    if frame_count < 2:
        raise ValueError(_t('validation.frameCountMinimum', value=frame_count))
    # Max frame count is present in FE, but not required here since this is a backend function and designed to be scalable.
    # Validate coordinates
    if not -90 <= latitude <= 90:
        raise ValueError(_t('validation.latitudeRange', value=latitude))
    if not -180 <= longitude <= 180:
        raise ValueError(_t('validation.longitudeRange', value=longitude))
    # Create start and end times
    start_datetime_str = f"{start_date}T{start_time}"
    end_datetime_str = f"{end_date}T{end_time}"
    start_t = Time(start_datetime_str, format="isot", scale="utc")
    end_t = Time(end_datetime_str, format="isot", scale="utc")
    # Validate time order
    if end_t <= start_t:
        raise ValueError(_t('validation.endTimeAfterStart'))
    # Calculate time span
    time_span = end_t - start_t
    time_span_hours = float(time_span.to(u.hour).value)
    # Generate time steps
    time_delta = (end_t - start_t) / (frame_count - 1)
    times = [start_t + i * time_delta for i in range(frame_count)]
    # Create location once for all frames
    location = EarthLocation(
        lat=latitude * u.deg,
        lon=longitude * u.deg,
        height=elevation * u.m
    )
    for obs_time in times:
        iso_parts = obs_time.iso.split()
        date_part = iso_parts[0]
        time_part = iso_parts[1].split('.')[0]
        datetime_str = f"{date_part}T{time_part}"
        altaz_frame = AltAz(obstime=obs_time, location=location, pressure=0.0)
        sun = get_sun(obs_time)
        moon = get_body("moon", obs_time, location)
        sun_altaz = sun.transform_to(altaz_frame)
        moon_altaz = moon.transform_to(altaz_frame)
        sun_data = _process_sun_position(
            sun_altaz=sun_altaz,
            time=obs_time,
            datetime_str=datetime_str,
            latitude=latitude,
            longitude=longitude,
            elevation=elevation
        )
        moon_data = _process_moon_position(
            moon_altaz=moon_altaz,
            time=obs_time,
            datetime_str=datetime_str,
            latitude=latitude,
            longitude=longitude,
            elevation=elevation
        )
        phase_data = _process_moon_phase(
            sun=sun,
            moon=moon,
            time=obs_time,
            datetime_str=datetime_str,
            latitude=latitude,
            longitude=longitude,
            elevation=elevation,
            locale=locale,
        )
        frame = {
            "datetime": f"{date_part}T{time_part}",
            "sun": {
                "altitude": sun_data["altitude"],
                "azimuth": sun_data["azimuth"],
                "is_visible": sun_data["is_visible"]
            },
            "moon": {
                "altitude": moon_data["altitude"],
                "azimuth": moon_data["azimuth"],
                "is_visible": moon_data["is_visible"]
            },
            "moon_phase": {
                "illumination": phase_data["illumination"],
                "phase_angle": phase_data["phase_angle"],
                "phase_name": phase_data["phase_name"]
            }
        }
        yield frame
    metadata = {
        "location": {
            "latitude": latitude,
            "longitude": longitude,
            "elevation": elevation
        },
        "frame_count": frame_count,
        "start_datetime": start_datetime_str,
        "end_datetime": end_datetime_str,
        "time_span_hours": time_span_hours
    }
    yield metadata
