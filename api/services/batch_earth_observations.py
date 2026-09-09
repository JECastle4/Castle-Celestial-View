"""Batch earth observations service for calculating multiple frames of celestial positions."""

from typing import Optional
from astropy.time import Time
from astropy.coordinates import (
    get_sun, get_body, AltAz, EarthLocation, HeliocentricTrueEcliptic
)
import astropy.units as u
from api.i18n import get_i18n
from api.models import TimeRange, LocationModel
from .sun import _process_sun_position
from .moon import _process_moon_position
from .venus import _process_venus_position
from .mercury import _process_mercury_position
from .mars import _process_mars_position, _get_retrograde_status_from_longitudes
from .moon_phase import _process_moon_phase
from .jupiter import _process_jupiter_position
from .saturn import _process_saturn_position
from .uranus import _process_uranus_position
from .neptune import _process_neptune_position


def _validate_batch_params(time_range: TimeRange, location: LocationModel, _t):
    """Validate frame count, coordinates, and time order."""
    if time_range.frame_count < 2:
        raise ValueError(_t('validation.frameCountMinimum', value=time_range.frame_count))
    if not -90 <= location.latitude <= 90:
        raise ValueError(_t('validation.latitudeRange', value=location.latitude))
    if not -180 <= location.longitude <= 180:
        raise ValueError(_t('validation.longitudeRange', value=location.longitude))


def _prepare_times_and_location(time_range: TimeRange, location: LocationModel, _t):
    """Create start/end Time objects and validate time order; create EarthLocation."""
    start_date = time_range.start.date
    start_time = time_range.start.time
    end_date = time_range.end.date
    end_time = time_range.end.time

    start_datetime_str = f"{start_date}T{start_time}Z"
    end_datetime_str = f"{end_date}T{end_time}Z"
    start_t = Time(start_datetime_str.rstrip('Z'), format="isot", scale="utc")
    end_t = Time(end_datetime_str.rstrip('Z'), format="isot", scale="utc")

    if end_t <= start_t:
        raise ValueError(_t('validation.endTimeAfterStart'))

    earth_location = EarthLocation(
        lat=location.latitude * u.deg,
        lon=location.longitude * u.deg,
        height=location.elevation * u.m
    )
    return start_t, end_t, start_datetime_str, end_datetime_str, earth_location


def _generate_frame_times(start_t: Time, end_t: Time, frame_count: int):
    """Generate evenly-spaced observation times."""
    time_delta = (end_t - start_t) / (frame_count - 1)
    times = [start_t + i * time_delta for i in range(frame_count)]
    time_span = end_t - start_t
    time_span_hours = float(time_span.to(u.hour).value)
    return times, time_span_hours


def _precalculate_mars_retrograde(frame_count: int, times):
    """Pre-calculate Mars heliocentric longitude for first two frames."""
    mars_longitudes = [None] * frame_count
    if frame_count >= 2:
        for idx in [0, 1]:
            mars_gcrs_temp = get_body("mars", times[idx])
            mars_helio_temp = mars_gcrs_temp.transform_to(
                HeliocentricTrueEcliptic(obstime=times[idx])
            )
            mars_longitudes[idx] = float(mars_helio_temp.lon.degree)
    return mars_longitudes


def _fetch_all_celestial_bodies(obs_time: Time, earth_location: EarthLocation):
    """Fetch all celestial bodies (with and without location) for a given time."""
    sun = get_sun(obs_time)
    moon = get_body("moon", obs_time, earth_location)
    venus_with_loc = get_body("venus", obs_time, earth_location)
    mercury_with_loc = get_body("mercury", obs_time, earth_location)
    mars_with_loc = get_body("mars", obs_time, earth_location)
    jupiter_with_loc = get_body("jupiter", obs_time, earth_location)
    saturn_with_loc = get_body("saturn", obs_time, earth_location)
    uranus_with_loc = get_body("uranus", obs_time, earth_location)
    neptune_with_loc = get_body("neptune", obs_time, earth_location)

    venus_gcrs = get_body("venus", obs_time)
    mercury_gcrs = get_body("mercury", obs_time)
    mars_gcrs = get_body("mars", obs_time)
    jupiter_gcrs = get_body("jupiter", obs_time)
    saturn_gcrs = get_body("saturn", obs_time)
    uranus_gcrs = get_body("uranus", obs_time)
    neptune_gcrs = get_body("neptune", obs_time)

    return {
        'sun': sun,
        'moon': moon,
        'venus_with_loc': venus_with_loc,
        'mercury_with_loc': mercury_with_loc,
        'mars_with_loc': mars_with_loc,
        'jupiter_with_loc': jupiter_with_loc,
        'saturn_with_loc': saturn_with_loc,
        'uranus_with_loc': uranus_with_loc,
        'neptune_with_loc': neptune_with_loc,
        'venus_gcrs': venus_gcrs,
        'mercury_gcrs': mercury_gcrs,
        'mars_gcrs': mars_gcrs,
        'jupiter_gcrs': jupiter_gcrs,
        'saturn_gcrs': saturn_gcrs,
        'uranus_gcrs': uranus_gcrs,
        'neptune_gcrs': neptune_gcrs,
    }


def _fetch_all_celestial_bodies_batch(times: list, earth_location: EarthLocation):
    """
    Fetch all celestial bodies for a list of times (vectorized for performance).
    
    For frame_count N, this makes N get_body calls instead of N*18 individual calls.
    Astropy is optimized for array inputs and transforms.
    
    Args:
        times: List of astropy Time objects (one per frame)
        earth_location: Observer location (EarthLocation)
    
    Returns:
        Dict of arrays: {body_name: array_of_positions_for_all_times}
    """
    # Convert list to Time array for vectorized operations
    times_array = Time(times)
    
    # Vectorized astropy calls (one call per body type, not per frame)
    sun = get_sun(times_array)
    moon = get_body("moon", times_array, earth_location)
    venus_with_loc = get_body("venus", times_array, earth_location)
    mercury_with_loc = get_body("mercury", times_array, earth_location)
    mars_with_loc = get_body("mars", times_array, earth_location)
    jupiter_with_loc = get_body("jupiter", times_array, earth_location)
    saturn_with_loc = get_body("saturn", times_array, earth_location)
    uranus_with_loc = get_body("uranus", times_array, earth_location)
    neptune_with_loc = get_body("neptune", times_array, earth_location)

    venus_gcrs = get_body("venus", times_array)
    mercury_gcrs = get_body("mercury", times_array)
    mars_gcrs = get_body("mars", times_array)
    jupiter_gcrs = get_body("jupiter", times_array)
    saturn_gcrs = get_body("saturn", times_array)
    uranus_gcrs = get_body("uranus", times_array)
    neptune_gcrs = get_body("neptune", times_array)

    return {
        'sun': sun,
        'moon': moon,
        'venus_with_loc': venus_with_loc,
        'mercury_with_loc': mercury_with_loc,
        'mars_with_loc': mars_with_loc,
        'jupiter_with_loc': jupiter_with_loc,
        'saturn_with_loc': saturn_with_loc,
        'uranus_with_loc': uranus_with_loc,
        'neptune_with_loc': neptune_with_loc,
        'venus_gcrs': venus_gcrs,
        'mercury_gcrs': mercury_gcrs,
        'mars_gcrs': mars_gcrs,
        'jupiter_gcrs': jupiter_gcrs,
        'saturn_gcrs': saturn_gcrs,
        'uranus_gcrs': uranus_gcrs,
        'neptune_gcrs': neptune_gcrs,
    }


def _calculate_mars_retrograde_status(frame_idx: int, frame_count: int, mars_gcrs: Time,
                                      obs_time: Time, mars_longitudes):
    """Calculate Mars retrograde status for current frame."""
    mars_heliocentric = mars_gcrs.transform_to(
        HeliocentricTrueEcliptic(obstime=obs_time)
    )
    current_mars_longitude = float(mars_heliocentric.lon.degree)
    mars_longitudes[frame_idx] = current_mars_longitude

    if frame_idx == 0 and frame_count >= 2:
        mars_retrograde_status = _get_retrograde_status_from_longitudes(
            current_mars_longitude, mars_longitudes[1]
        )
    else:
        mars_retrograde_status = _get_retrograde_status_from_longitudes(
            mars_longitudes[frame_idx - 1], current_mars_longitude
        )
    return mars_retrograde_status, current_mars_longitude


def _build_frame_observation_data(frame_idx: int, obs_time: Time, earth_location: EarthLocation,
                                  altaz_frame: AltAz, location: LocationModel, locale: Optional[str],
                                  bodies, mars_retrograde_status, altaz_frames=None):
    """
    Build complete observation data for a single frame.
    
    Args:
        frame_idx: Index of this frame in the batch
        obs_time: Single Time object for this frame
        earth_location: Observer location
        altaz_frame: Single AltAz frame for this time/location
        location: Observer LocationModel
        locale: Locale for translations
        bodies: Dict of body arrays (from _fetch_all_celestial_bodies_batch)
        mars_retrograde_status: Pre-computed retrograde status for this frame
        altaz_frames: Optional pre-computed AltAz frame array for this frame
    """
    iso_parts = obs_time.iso.split()
    date_part = iso_parts[0]
    time_part = iso_parts[1].split('.')[0]
    datetime_str = f"{date_part}T{time_part}Z"

    # Extract single-frame data from arrays by indexing
    sun_frame = bodies['sun'][frame_idx] if hasattr(bodies['sun'], '__len__') else bodies['sun']
    moon_frame = bodies['moon'][frame_idx] if hasattr(bodies['moon'], '__len__') else bodies['moon']
    venus_with_loc_frame = bodies['venus_with_loc'][frame_idx] if hasattr(bodies['venus_with_loc'], '__len__') else bodies['venus_with_loc']
    mercury_with_loc_frame = bodies['mercury_with_loc'][frame_idx] if hasattr(bodies['mercury_with_loc'], '__len__') else bodies['mercury_with_loc']
    mars_with_loc_frame = bodies['mars_with_loc'][frame_idx] if hasattr(bodies['mars_with_loc'], '__len__') else bodies['mars_with_loc']
    jupiter_with_loc_frame = bodies['jupiter_with_loc'][frame_idx] if hasattr(bodies['jupiter_with_loc'], '__len__') else bodies['jupiter_with_loc']
    saturn_with_loc_frame = bodies['saturn_with_loc'][frame_idx] if hasattr(bodies['saturn_with_loc'], '__len__') else bodies['saturn_with_loc']
    uranus_with_loc_frame = bodies['uranus_with_loc'][frame_idx] if hasattr(bodies['uranus_with_loc'], '__len__') else bodies['uranus_with_loc']
    neptune_with_loc_frame = bodies['neptune_with_loc'][frame_idx] if hasattr(bodies['neptune_with_loc'], '__len__') else bodies['neptune_with_loc']
    
    venus_gcrs_frame = bodies['venus_gcrs'][frame_idx] if hasattr(bodies['venus_gcrs'], '__len__') else bodies['venus_gcrs']
    mercury_gcrs_frame = bodies['mercury_gcrs'][frame_idx] if hasattr(bodies['mercury_gcrs'], '__len__') else bodies['mercury_gcrs']
    mars_gcrs_frame = bodies['mars_gcrs'][frame_idx] if hasattr(bodies['mars_gcrs'], '__len__') else bodies['mars_gcrs']
    jupiter_gcrs_frame = bodies['jupiter_gcrs'][frame_idx] if hasattr(bodies['jupiter_gcrs'], '__len__') else bodies['jupiter_gcrs']
    saturn_gcrs_frame = bodies['saturn_gcrs'][frame_idx] if hasattr(bodies['saturn_gcrs'], '__len__') else bodies['saturn_gcrs']
    uranus_gcrs_frame = bodies['uranus_gcrs'][frame_idx] if hasattr(bodies['uranus_gcrs'], '__len__') else bodies['uranus_gcrs']
    neptune_gcrs_frame = bodies['neptune_gcrs'][frame_idx] if hasattr(bodies['neptune_gcrs'], '__len__') else bodies['neptune_gcrs']

    # Transform indexed positions to AltAz
    sun_altaz = sun_frame.transform_to(altaz_frame)
    moon_altaz = moon_frame.transform_to(altaz_frame)
    venus_altaz = venus_with_loc_frame.transform_to(altaz_frame)
    mercury_altaz = mercury_with_loc_frame.transform_to(altaz_frame)
    mars_altaz = mars_with_loc_frame.transform_to(altaz_frame)
    jupiter_altaz = jupiter_with_loc_frame.transform_to(altaz_frame)
    saturn_altaz = saturn_with_loc_frame.transform_to(altaz_frame)
    uranus_altaz = uranus_with_loc_frame.transform_to(altaz_frame)
    neptune_altaz = neptune_with_loc_frame.transform_to(altaz_frame)

    sun_data = _process_sun_position(
        sun_gcrs=sun_frame,
        sun_altaz=sun_altaz,
        time=obs_time,
        datetime_str=datetime_str,
        location=location
    )
    moon_data = _process_moon_position(
        moon_gcrs=moon_frame,
        moon_altaz=moon_altaz,
        time=obs_time,
        datetime_str=datetime_str,
        location=location
    )
    venus_data = _process_venus_position(
        venus_with_loc=venus_with_loc_frame,
        venus_altaz=venus_altaz,
        sun=sun_frame,
        venus_gcrs=venus_gcrs_frame,
        time=obs_time,
        datetime_str=datetime_str,
        location=location,
        locale=locale
    )
    mercury_data = _process_mercury_position(
        mercury_with_loc=mercury_with_loc_frame,
        mercury_altaz=mercury_altaz,
        sun=sun_frame,
        mercury_gcrs=mercury_gcrs_frame,
        time=obs_time,
        datetime_str=datetime_str,
        location=location,
        locale=locale
    )
    mars_data = _process_mars_position(
        mars_with_loc=mars_with_loc_frame,
        mars_altaz=mars_altaz,
        sun=sun_frame,
        mars_gcrs=mars_gcrs_frame,
        time=obs_time,
        datetime_str=datetime_str,
        location=location,
        locale=locale,
        retrograde_status=mars_retrograde_status
    )
    jupiter_data = _process_jupiter_position(
        jupiter_with_loc=jupiter_with_loc_frame,
        jupiter_altaz=jupiter_altaz,
        jupiter_gcrs=jupiter_gcrs_frame,
        time=obs_time,
        datetime_str=datetime_str,
        location=location
    )
    saturn_data = _process_saturn_position(
        saturn_with_loc=saturn_with_loc_frame,
        saturn_altaz=saturn_altaz,
        saturn_gcrs=saturn_gcrs_frame,
        time=obs_time,
        datetime_str=datetime_str,
        location=location
    )
    uranus_data = _process_uranus_position(
        uranus_with_loc=uranus_with_loc_frame,
        uranus_altaz=uranus_altaz,
        uranus_gcrs=uranus_gcrs_frame,
        time=obs_time,
        datetime_str=datetime_str,
        location=location
    )
    neptune_data = _process_neptune_position(
        neptune_with_loc=neptune_with_loc_frame,
        neptune_altaz=neptune_altaz,
        neptune_gcrs=neptune_gcrs_frame,
        time=obs_time,
        datetime_str=datetime_str,
        location=location
    )
    phase_data = _process_moon_phase(
        sun=sun_frame,
        moon=moon_frame,
        time=obs_time,
        datetime_str=datetime_str,
        location=location,
        locale=locale,
    )

    frame = {
        "datetime": f"{date_part}T{time_part}Z",
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
        },
        "mercury": {
            "altitude": mercury_data["altitude"],
            "azimuth": mercury_data["azimuth"],
            "is_visible": mercury_data["is_visible"],
            "ra_degrees": mercury_data["ra_degrees"],
            "dec_degrees": mercury_data["dec_degrees"]
        },
        "mercury_phase": {
            "illumination": mercury_data["illumination"],
            "phase_angle": mercury_data["phase_angle"],
            "phase_name": mercury_data["phase_name"],
            "naked_eye_visible": mercury_data["naked_eye_visible"]
        },
        "mars": {
            "altitude": mars_data["altitude"],
            "azimuth": mars_data["azimuth"],
            "is_visible": mars_data["is_visible"],
            "ra_degrees": mars_data["ra_degrees"],
            "dec_degrees": mars_data["dec_degrees"]
        },
        "mars_phase": {
            "illumination": mars_data["illumination"],
            "phase_angle": mars_data["phase_angle"],
            "phase_name": mars_data["phase_name"],
            "retrograde_status": mars_data["retrograde_status"]
        },
        "jupiter": {
            "altitude": jupiter_data["altitude"],
            "azimuth": jupiter_data["azimuth"],
            "is_visible": jupiter_data["is_visible"],
            "ra_degrees": jupiter_data["ra_degrees"],
            "dec_degrees": jupiter_data["dec_degrees"]
        },
        "jupiter_data": {
            "retrograde_status": jupiter_data["retrograde_status"]
        },
        "saturn": {
            "altitude": saturn_data["altitude"],
            "azimuth": saturn_data["azimuth"],
            "is_visible": saturn_data["is_visible"],
            "ra_degrees": saturn_data["ra_degrees"],
            "dec_degrees": saturn_data["dec_degrees"]
        },
        "saturn_data": {
            "retrograde_status": saturn_data["retrograde_status"]
        },
        "uranus": {
            "altitude": uranus_data["altitude"],
            "azimuth": uranus_data["azimuth"],
            "is_visible": uranus_data["is_visible"],
            "ra_degrees": uranus_data["ra_degrees"],
            "dec_degrees": uranus_data["dec_degrees"]
        },
        "uranus_data": {
            "retrograde_status": uranus_data["retrograde_status"]
        },
        "neptune": {
            "altitude": neptune_data["altitude"],
            "azimuth": neptune_data["azimuth"],
            "is_visible": neptune_data["is_visible"],
            "ra_degrees": neptune_data["ra_degrees"],
            "dec_degrees": neptune_data["dec_degrees"]
        },
        "neptune_data": {
            "retrograde_status": neptune_data["retrograde_status"]
        }
    }
    return frame


def calculate_batch_earth_observations(
    time_range: TimeRange,
    location: LocationModel,
    locale: Optional[str] = None,
):
    """
    Calculate batch observations of sun, moon, Venus, Mercury, Mars, and outer planets.

    This function generates multiple frames of celestial observations between
    a start and end time. Each frame contains sun position, moon position,
    moon phase, Venus position with phase information, Mercury position with phase,
    Mars position with phase data, and Jupiter/Saturn/Uranus/Neptune positions with
    retrograde motion status for that specific moment.

    Args:
        time_range: TimeRange object containing:
            - start: ObservationDateTime with start date and time
            - end: ObservationDateTime with end date and time
            - frame_count: Number of frames to generate (must be >= 2)
        location: LocationModel with observer position (latitude, longitude, elevation)
        locale: BCP 47 locale tag (e.g. 'en', 'xx-reverse') used to translate
            validation error messages and phase names in each frame.
            Defaults to English when None.

    Yields:
        dict: Frame data for each observation
        dict: Metadata after all frames
    """
    _t = get_i18n(locale).get

    # Validate inputs
    _validate_batch_params(time_range, location, _t)

    # Prepare times and location
    start_t, end_t, start_datetime_str, end_datetime_str, earth_location = (
        _prepare_times_and_location(time_range, location, _t)
    )

    # Generate frame times
    frame_count = time_range.frame_count
    times, time_span_hours = _generate_frame_times(start_t, end_t, frame_count)

    # Pre-calculate Mars retrograde for frame 0/1 comparison
    mars_longitudes = _precalculate_mars_retrograde(frame_count, times)

    # Vectorized batch call: fetch all bodies for all times at once (performance optimization)
    # This single call replaces frame_count individual calls to _fetch_all_celestial_bodies
    bodies = _fetch_all_celestial_bodies_batch(times, earth_location)

    # Process each frame (now just indexes into pre-computed arrays)
    for frame_idx, obs_time in enumerate(times):
        # Calculate Mars retrograde status (uses pre-computed mars_gcrs array)
        mars_retrograde_status, _ = _calculate_mars_retrograde_status(
            frame_idx, frame_count, bodies['mars_gcrs'][frame_idx], obs_time, mars_longitudes
        )

        # Build Alt/Az frame for this observation
        altaz_frame = AltAz(obstime=obs_time, location=earth_location, pressure=0.0)

        # Build and yield frame data
        frame = _build_frame_observation_data(
            frame_idx, obs_time, earth_location, altaz_frame, location, locale,
            bodies, mars_retrograde_status
        )
        yield frame

    # Yield metadata after all frames
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
