"""Moon phase calculation service."""

import warnings
from typing import Optional
from astropy.time import Time
from astropy.coordinates import get_sun, get_body, EarthLocation
from astropy.coordinates.baseframe import NonRotationTransformationWarning
import astropy.units as u
import numpy as np
from api.i18n import get_i18n
from api.models import ObservationDateTime, LocationModel


def calculate_moon_phase(
    observation_time: ObservationDateTime,
    location: LocationModel,
    locale: Optional[str] = None,
) -> dict:
    """
    Calculate the moon's phase information including illumination, phase angle, and name.

    Phase calculation requires both sun and moon positions to determine the
    elongation angle (angular separation) and ecliptic longitude difference.

    Args:
        observation_time: Date and time of observation
        location: Observer location (latitude, longitude, elevation)

    Returns:
        dict: Dictionary containing:
            - illumination: Fraction of moon illuminated (0.0 to 1.0)
            - phase_angle: Moon's phase angle in ecliptic longitude (0 to 360 degrees)
            - phase_name: Textual name of the phase (e.g., "Waxing Crescent")
            - julian_date: Julian Date of the observation
            - location: Dict with latitude, longitude, elevation
            - input_datetime: Original input datetime string

    Raises:
        ValueError: If date/time format is invalid or coordinates out of range
    """
    # Validate coordinates
    if not -90 <= location.latitude <= 90:
        msg = get_i18n(locale).get('validation.latitudeRange',
                                     value=location.latitude)
        raise ValueError(msg)
    if not -180 <= location.longitude <= 180:
        msg = get_i18n(locale).get('validation.longitudeRange',
                                    value=location.longitude)
        raise ValueError(msg)

    # Combine date and time (ISO 8601 format)
    datetime_str = f"{observation_time.date}T{observation_time.time}"

    # Convert to astropy Time (assumes UTC)
    time = Time(datetime_str, format="isot", scale="utc")

    # Create location
    earth_location = EarthLocation(
        lat=location.latitude * u.deg, lon=location.longitude * u.deg,
        height=location.elevation * u.m
    )

    # Get sun and moon positions
    sun = get_sun(time)
    moon = get_body("moon", time, location=earth_location)

    return _process_moon_phase(
        sun, moon, time, datetime_str, location,
        locale=locale
    )


def _process_moon_phase(
    sun,
    moon,
    time: Time,
    datetime_str: str,
    location: LocationModel,
    locale: Optional[str] = None,
) -> dict:
    """
    Process moon phase data from sun and moon positions.
    Internal function used by calculate_moon_phase and batch operations.

    Args:
        sun: Sun position (GCRS coordinates)
        moon: Moon position (GCRS coordinates)
        time: Astropy Time object
        datetime_str: Input datetime string
        latitude: Latitude in degrees
        longitude: Longitude in degrees
        elevation: Elevation in meters

    Returns:
        Dictionary with moon phase data
    """
    # Suppress the NonRotationTransformationWarning during coordinate transformations
    # This warning is informational and doesn't affect moon phase calculation accuracy
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", NonRotationTransformationWarning)

        # Calculate illumination fraction from elongation angle
        # Elongation is the angular separation between sun and moon as seen from Earth
        # elongation=0° → new moon (illum=0), elongation=180° → full moon (illum=1)
        elongation = sun.separation(moon)
        illumination = float(0.5 * (1 - np.cos(elongation.rad)))

        # Calculate phase angle from ecliptic longitudes
        # This tells us where the moon is relative to the sun in the ecliptic plane
        # 0-180° = waxing (new → full), 180-360° = waning (full → new)
        sun_lon = sun.geocentrictrueecliptic.lon.deg
        moon_lon = moon.geocentrictrueecliptic.lon.deg
        phase_angle = float((moon_lon - sun_lon) % 360)

    # Determine phase name based on illumination and whether waxing/waning
    illum_pct = illumination * 100
    _t = get_i18n(locale).get

    if phase_angle < 180:  # Waxing
        if illum_pct < 3:
            phase_name = _t('moonPhases.newMoon')
        elif illum_pct < 47:
            phase_name = _t('moonPhases.waxingCrescent')
        elif illum_pct < 53:
            phase_name = _t('moonPhases.firstQuarter')
        elif illum_pct < 97:
            phase_name = _t('moonPhases.waxingGibbous')
        else:
            phase_name = _t('moonPhases.fullMoon')
    else:  # Waning
        if illum_pct > 97:
            phase_name = _t('moonPhases.fullMoon')
        elif illum_pct > 53:
            phase_name = _t('moonPhases.waningGibbous')
        elif illum_pct > 47:
            phase_name = _t('moonPhases.lastQuarter')
        elif illum_pct > 3:
            phase_name = _t('moonPhases.waningCrescent')
        else:
            phase_name = _t('moonPhases.newMoon')

    return {
        "illumination": illumination,
        "phase_angle": phase_angle,
        "phase_name": phase_name,
        "julian_date": float(time.jd),
        "location": {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "elevation": location.elevation,
        },
        "input_datetime": datetime_str,
    }
