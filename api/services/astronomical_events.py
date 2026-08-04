"""
Astronomical Events Service - Issue 141

Finds new and full moons within a date range, classifies each as an eclipse
(TOTAL/PARTIAL/ANNULAR/PENUMBRAL/NONE) using api.services.eclipse_detection, and
optionally computes contact times using api.services.eclipse_contact_times.

Geocentric-only. This is the data source behind the /astronomical-events API route.
Supports pagination since a date range can span many lunations.
"""

import numpy as np
from astropy.time import Time
from astropy.coordinates import get_sun, get_body, GeocentricMeanEcliptic
import astropy.units as u

from api.i18n import get_i18n
from api.services.eclipse_detection import (
    GEOCENTRIC,
    get_moon_ecliptic_latitude,
    find_greatest_eclipse_time,
    classify_lunar_eclipse_type,
    classify_solar_eclipse_type,
    LUNAR_ECLIPSE_THRESHOLD,
    SOLAR_ECLIPSE_THRESHOLD,
)
from api.services.eclipse_contact_times import (
    calculate_lunar_contact_times,
    calculate_solar_contact_times,
)

# Coarse sampling interval (hours) used to bracket new/full moon crossings. The
# synodic month is ~29.5 days, so 12h sampling gives ~59 samples per lunation -
# far more than enough to catch every crossing without aliasing.
SAMPLE_INTERVAL_HOURS = 12

# Maximum requestable date range (days), bounding worst-case compute cost.
MAX_RANGE_DAYS = 3660  # ~10 years


def _phase_angle_deg(time_obj):
    """Moon's ecliptic longitude minus Sun's, wrapped into [0, 360)."""
    sun = get_sun(time_obj)
    moon = get_body('moon', time_obj, location=GEOCENTRIC)
    sun_lon = sun.transform_to(GeocentricMeanEcliptic(equinox=time_obj)).lon.degree
    moon_lon = moon.transform_to(GeocentricMeanEcliptic(equinox=time_obj)).lon.degree
    return (moon_lon - sun_lon) % 360


def _new_moon_signal(time_obj):
    """Signed function crossing zero exactly at new moon (phase_angle == 0/360)."""
    return ((_phase_angle_deg(time_obj) + 180) % 360) - 180


def _full_moon_signal(time_obj):
    """Signed function crossing zero exactly at full moon (phase_angle == 180)."""
    return _phase_angle_deg(time_obj) - 180


def _bisect_zero(fn, t_low, t_high, iterations=50):
    """Bisection root-finder for a scalar function of astropy Time, given a
    bracket [t_low, t_high] with opposite-signed endpoints."""
    f_low = fn(t_low)
    for _ in range(iterations):
        t_mid = t_low + (t_high - t_low) / 2
        f_mid = fn(t_mid)
        if (f_mid > 0) == (f_low > 0):
            t_low, f_low = t_mid, f_mid
        else:
            t_high = t_mid
    return t_low + (t_high - t_low) / 2


def find_new_full_moons(start_time, end_time, sample_interval_hours=SAMPLE_INTERVAL_HOURS):
    """
    Find all new and full moon instants within [start_time, end_time].

    Args:
        start_time, end_time: astropy Time objects
        sample_interval_hours: coarse sampling interval used to bracket crossings

    Returns:
        list of dicts {'time': astropy Time, 'phase': 'new' or 'full'}, sorted by time
    """
    n_samples = int(np.ceil((end_time - start_time).to(u.hour).value / sample_interval_hours)) + 2
    sample_times = start_time + np.arange(n_samples) * sample_interval_hours * u.hour

    # Vectorized astropy calls - much faster than looping per-sample.
    sun = get_sun(sample_times)
    moon = get_body('moon', sample_times, location=GEOCENTRIC)
    sun_lon = sun.transform_to(GeocentricMeanEcliptic(equinox=sample_times)).lon.degree
    moon_lon = moon.transform_to(GeocentricMeanEcliptic(equinox=sample_times)).lon.degree
    phase_angles = (moon_lon - sun_lon) % 360

    events = []
    for i in range(1, len(sample_times)):
        prev_angle, cur_angle = phase_angles[i - 1], phase_angles[i]
        diff = cur_angle - prev_angle

        if diff < -180:
            # Wrapped through 0/360 -> new moon crossing
            t_event = _bisect_zero(_new_moon_signal, sample_times[i - 1], sample_times[i])
            events.append({'time': t_event, 'phase': 'new'})
        elif prev_angle < 180 <= cur_angle:
            # Crossed 180 -> full moon crossing
            t_event = _bisect_zero(_full_moon_signal, sample_times[i - 1], sample_times[i])
            events.append({'time': t_event, 'phase': 'full'})

    events = [e for e in events if start_time <= e['time'] <= end_time]
    events.sort(key=lambda e: e['time'].jd)
    return events


def build_astronomical_event(event, include_contact_times=True, locale=None):
    """
    Given a {'time', 'phase'} entry from find_new_full_moons, build the full event
    dict: moon ecliptic latitude/threshold check, eclipse classification (if any),
    optionally contact times, and translate event_type/eclipse_type using locale.
    """
    time_obj = event['time']
    phase = event['phase']
    is_lunar = phase == 'full'
    threshold = LUNAR_ECLIPSE_THRESHOLD if is_lunar else SOLAR_ECLIPSE_THRESHOLD

    moon_lat = get_moon_ecliptic_latitude(time_obj)
    within_threshold = abs(moon_lat) < threshold

    _t = get_i18n(locale).get

    result = {
        'event_type': (
            _t('events.eventTypes.fullMoon')
            if is_lunar
            else _t('events.eventTypes.newMoon')
        ),
        'date': time_obj.iso,
        'julian_date': float(time_obj.jd),
        'moon_ecl_lat_deg': round(float(moon_lat), 4),
        'eclipse_occurs': False,
        'eclipse_type': _t('events.eclipseTypes.NONE'),
        'greatest_eclipse_time': None,
        'umbral_magnitude': None,
        'penumbral_magnitude': None,
        'size_ratio': None,
        'contact_times': None,
    }

    if not within_threshold:
        return result

    greatest_time = find_greatest_eclipse_time(time_obj, is_lunar=is_lunar)
    result['greatest_eclipse_time'] = greatest_time.iso

    if is_lunar:
        type_info = classify_lunar_eclipse_type(greatest_time)
        eclipse_type_code = type_info['eclipse_type']
        result['eclipse_type'] = _t(f'events.eclipseTypes.{eclipse_type_code}')
        result['umbral_magnitude'] = type_info['umbral_magnitude']
        result['penumbral_magnitude'] = type_info['penumbral_magnitude']
        result['eclipse_occurs'] = type_info['eclipse_type'] != 'NONE'
        if result['eclipse_occurs']:
            # Set event_type to combined semantic type (e.g., "Lunar Total")
            eclipse_type_name = eclipse_type_code[0].upper() + eclipse_type_code[1:].lower()
            result['event_type'] = _t(f'events.eventTypes.lunar{eclipse_type_name}')
            if include_contact_times:
                result['contact_times'] = calculate_lunar_contact_times(greatest_time)
    else:
        type_info = classify_solar_eclipse_type(greatest_time)
        eclipse_type_code = type_info['eclipse_type']
        result['eclipse_type'] = _t(f'events.eclipseTypes.{eclipse_type_code}')
        result['size_ratio'] = type_info['size_ratio']
        result['eclipse_occurs'] = type_info['eclipse_type'] != 'NONE'
        if result['eclipse_occurs']:
            # Set event_type to combined semantic type (e.g., "Solar Total")
            eclipse_type_name = eclipse_type_code[0].upper() + eclipse_type_code[1:].lower()
            result['event_type'] = _t(f'events.eventTypes.solar{eclipse_type_name}')
            if include_contact_times:
                result['contact_times'] = calculate_solar_contact_times(greatest_time)

    return result


def validate_date_range(start_date_str, end_date_str):
    """
    Parse and validate a requested date range.

    Args:
        start_date_str, end_date_str: 'YYYY-MM-DD' date strings

    Returns:
        tuple: (start_time, end_time) as astropy Time objects; end_time is
        end_date_str + 1 day so it is inclusive of the whole end_date.

    Raises:
        ValueError: if the date range is invalid or too large
    """
    start_time = Time(start_date_str, scale='utc')
    end_time = Time(end_date_str, scale='utc') + 1 * u.day  # inclusive of end_date

    if end_time <= start_time:
        raise ValueError("end_date must be after start_date")

    if (end_time - start_time).to(u.day).value > MAX_RANGE_DAYS:
        raise ValueError(f"Date range too large (max {MAX_RANGE_DAYS} days)")

    return start_time, end_time


def _filter_by_event_types(raw_events, event_types):
    """Filter raw {'time', 'phase'} events down to the requested event_types."""
    if not event_types:
        return raw_events
    wanted_phase = {'new_moon': 'new', 'full_moon': 'full'}
    allowed_phases = {wanted_phase[et] for et in event_types if et in wanted_phase}
    return [e for e in raw_events if e['phase'] in allowed_phases]


def get_astronomical_events(
    start_date_str,
    end_date_str,
    page=1,
    page_size=10,
    include_contact_times=True,
    event_types=None,
    locale=None,
):
    """
    Find and classify all new/full moon events (with eclipse detection) within a date
    range, returning a paginated result.

    Args:
        start_date_str, end_date_str: 'YYYY-MM-DD' date strings
        page: 1-based page number
        page_size: number of events per page
        include_contact_times: whether to compute contact times for eclipse events
        event_types: optional iterable of {'new_moon', 'full_moon'} to filter by;
            None/empty means all types
        locale: BCP 47 locale tag for translating event_type and eclipse_type strings

    Returns:
        dict: {'events': [...], 'pagination': {...}}

    Raises:
        ValueError: if the date range is invalid or too large
    """
    start_time, end_time = validate_date_range(start_date_str, end_date_str)

    raw_events = find_new_full_moons(start_time, end_time)
    raw_events = _filter_by_event_types(raw_events, event_types)

    total = len(raw_events)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_events = raw_events[start_idx:end_idx]

    events = [
        build_astronomical_event(e, include_contact_times=include_contact_times, locale=locale)
        for e in page_events
    ]

    total_pages = max(1, (total + page_size - 1) // page_size)

    return {
        'events': events,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total_events': total,
            'total_pages': total_pages,
        },
    }


def stream_astronomical_events(
    start_date_str,
    end_date_str,
    page_size=10,
    include_contact_times=True,
    event_types=None,
    locale=None,
):
    """
    Generator variant of get_astronomical_events for SSE streaming.

    The new/full moon search (find_new_full_moons) runs once up front - it is
    vectorized and comparatively fast. The expensive per-event work (eclipse
    classification, contact times) is then done page by page, yielding each
    page as soon as it is ready so a client can display progress instead of
    waiting for the entire date range to be processed.

    Args:
        start_date_str, end_date_str: 'YYYY-MM-DD' date strings
        page_size: number of events per page
        include_contact_times: whether to compute contact times for eclipse events
        event_types: optional iterable of {'new_moon', 'full_moon'} to filter by;
            None/empty means all types
        locale: BCP 47 locale tag for translating event_type and eclipse_type strings

    Yields:
        dict: {'page': int, 'events': [...]} for each page, in order
        dict: {'page_size': int, 'total_events': int, 'total_pages': int} once, last

    Raises:
        ValueError: if the date range is invalid or too large
    """
    start_time, end_time = validate_date_range(start_date_str, end_date_str)

    raw_events = find_new_full_moons(start_time, end_time)
    raw_events = _filter_by_event_types(raw_events, event_types)

    total = len(raw_events)
    total_pages = max(1, (total + page_size - 1) // page_size)

    for page in range(1, total_pages + 1):
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_events = [
            build_astronomical_event(e, include_contact_times=include_contact_times, locale=locale)
            for e in raw_events[start_idx:end_idx]
        ]
        yield {'page': page, 'events': page_events}

    yield {
        'page_size': page_size,
        'total_events': total,
        'total_pages': total_pages,
    }
