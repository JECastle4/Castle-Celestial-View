"""Batch earth observations service for calculating multiple frames of celestial positions."""

from typing import Optional
from astropy.time import Time
from astropy.coordinates import get_sun, get_body, AltAz, EarthLocation
import astropy.units as u
from api.i18n import get_i18n
from api.models import TimeRange, LocationModel
from .sun import _process_sun_position
from .moon import _process_moon_position
from .venus import _process_venus_position
from .moon_phase import _process_moon_phase


def calculate_batch_earth_observations(
    time_range: TimeRange,
    location: LocationModel,
    locale: Optional[str] = None,
):
    """
    Calculate batch observations of sun, moon, and Venus positions from Earth.

    This function generates multiple frames of celestial observations between
    a start and end time. Each frame contains sun position, moon position,
    moon phase, and Venus position with phase information for that specific moment.

    Args:
        time_range: TimeRange object containing:
            - start: ObservationDateTime with start date and time
            - end: ObservationDateTime with end date and time
            - frame_count: Number of frames to generate (must be >= 2)
        location: LocationModel with observer position (latitude, longitude, elevation)
        locale: BCP 47 locale tag (e.g. 'en', 'xx-reverse') used to translate
            validation error messages and moon/Venus phase names in each frame.
            Defaults to English when None.

    Yields:
        dict: Frame data for each observation
        dict: Metadata after all frames
    """
    _t = get_i18n(locale).get

    # Extract time range components
    start_date = time_range.start.date
    start_time = time_range.start.time
    end_date = time_range.end.date
    end_time = time_range.end.time
    frame_count = time_range.frame_count

    # Validate frame count
    if frame_count < 2:
        raise ValueError(_t('validation.frameCountMinimum', value=frame_count))
    # Max frame count is present in FE, but not required here since this is
    # a backend function and designed to be scalable.
    # Validate coordinates
    if not -90 <= location.latitude <= 90:
        raise ValueError(_t('validation.latitudeRange', value=location.latitude))
    if not -180 <= location.longitude <= 180:
        raise ValueError(_t('validation.longitudeRange', value=location.longitude))
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
    # Create Earth location once for all frames
    earth_location = EarthLocation(
        lat=location.latitude * u.deg,
        lon=location.longitude * u.deg,
        height=location.elevation * u.m
    )
    for obs_time in times:
        iso_parts = obs_time.iso.split()
        date_part = iso_parts[0]
        time_part = iso_parts[1].split('.')[0]
        datetime_str = f"{date_part}T{time_part}"
        altaz_frame = AltAz(obstime=obs_time, location=earth_location, pressure=0.0)
        sun = get_sun(obs_time)
        moon = get_body("moon", obs_time, earth_location)
        venus_with_loc = get_body("venus", obs_time, earth_location)
        # Get Venus at geocenter for geocentric separation/phase calculations (no location)
        venus_gcrs = get_body("venus", obs_time)
        sun_altaz = sun.transform_to(altaz_frame)
        moon_altaz = moon.transform_to(altaz_frame)
        venus_altaz = venus_with_loc.transform_to(altaz_frame)
        sun_data = _process_sun_position(
            sun_altaz=sun_altaz,
            time=obs_time,
            datetime_str=datetime_str,
            location=location
        )
        moon_data = _process_moon_position(
            moon_altaz=moon_altaz,
            time=obs_time,
            datetime_str=datetime_str,
            location=location
        )
        venus_data = _process_venus_position(
            venus_altaz=venus_altaz,
            sun=sun,
            venus_gcrs=venus_gcrs,
            time=obs_time,
            datetime_str=datetime_str,
            location=location,
            locale=locale
        )
        phase_data = _process_moon_phase(
            sun=sun,
            moon=moon,
            time=obs_time,
            datetime_str=datetime_str,
            location=location,
            locale=locale,
        )
        frame = {
            "datetime": f"{date_part}T{time_part}",
            "sun": {
                "altitude": sun_data["altitude"],
                "azimuth": sun_data["azimuth"],
                "is_visible": sun_data["is_visible"],
                "ra_degrees": sun_data["ra_degrees"],
                "dec_degrees": sun_data["dec_degrees"]
            },
            "moon": {
                "altitude": moon_data["altitude"],
                "azimuth": moon_data["azimuth"],
                "is_visible": moon_data["is_visible"],
                "ra_degrees": moon_data["ra_degrees"],
                "dec_degrees": moon_data["dec_degrees"]
            },
            "moon_phase": {
                "illumination": phase_data["illumination"],
                "phase_angle": phase_data["phase_angle"],
                "phase_name": phase_data["phase_name"]
            },
            "venus": {
                "altitude": venus_data["altitude"],
                "azimuth": venus_data["azimuth"],
                "is_visible": venus_data["is_visible"],
                "ra_degrees": venus_data["ra_degrees"],
                "dec_degrees": venus_data["dec_degrees"]
            },
            "venus_phase": {
                "illumination": venus_data["illumination"],
                "phase_angle": venus_data["phase_angle"],
                "phase_name": venus_data["phase_name"],
                "naked_eye_visible": venus_data["naked_eye_visible"]
            }
        }
        yield frame
    metadata = {
        "location": {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "elevation": location.elevation
        },
        "frame_count": frame_count,
        "start_datetime": start_datetime_str,
        "end_datetime": end_datetime_str,
        "time_span_hours": time_span_hours
    }
    yield metadata
