"""
Common position calculation utilities for all celestial bodies.

This module provides generic position calculation logic used by all bodies
(Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune) to compute
altitude, azimuth, RA/Dec, and visibility from a given Earth location and time.

Position data is computed in topocentric coordinates (observer-dependent, includes
parallax correction for Earth location).
"""
from typing import Optional

from astropy.coordinates import get_body, AltAz, EarthLocation
from astropy.time import Time
import astropy.units as u
import numpy as np

from api.i18n import get_i18n
from api.models import ObservationDateTime, LocationModel


def _setup_coordinates(
    observation_time: ObservationDateTime,
    location: LocationModel,
    locale: Optional[str] = None
) -> tuple:
    """
    Setup and validate all coordinate objects needed for position calculation.

    Args:
        observation_time: Date and time of observation
        location: Observer location (latitude, longitude, elevation)
        locale: Language locale code for error messages

    Returns:
        Tuple of (obs_time, earth_location, altaz_frame, datetime_str)

    Raises:
        ValueError: If coordinates are out of valid range
    """
    i18n = get_i18n(locale)

    # Validate coordinates
    if not -90 <= location.latitude <= 90:
        raise ValueError(i18n.get('validation.latitudeRange', value=location.latitude))
    if not -180 <= location.longitude <= 180:
        raise ValueError(i18n.get('validation.longitudeRange', value=location.longitude))

    # Combine date and time (ISO 8601 format)
    datetime_str = f"{observation_time.date}T{observation_time.time}Z"

    # Convert to astropy Time (assumes UTC)
    obs_time = Time(datetime_str.rstrip('Z'), format='isot', scale='utc')

    # Create Earth location
    earth_location = EarthLocation(
        lat=location.latitude * u.deg,
        lon=location.longitude * u.deg,
        height=location.elevation * u.m
    )

    # Create AltAz frame (pressure=0 to ignore atmospheric refraction for simplicity)
    altaz_frame = AltAz(obstime=obs_time, location=earth_location, pressure=0.0)

    return obs_time, earth_location, altaz_frame, datetime_str


def get_body_position(
    observation_time: ObservationDateTime,
    location: LocationModel,
    body_name: str,
    locale: Optional[str] = None
) -> dict:
    """
    Calculate topocentric position (altitude, azimuth, RA/Dec, visibility) for any celestial body.

    This is a generic utility used by all body-specific position calculations.

    Args:
        observation_time: Date and time of observation
        location: Observer location (latitude, longitude, elevation)
        body_name: Name of celestial body ('moon', 'mercury', 'venus', 'mars', 'jupiter',
                   'saturn', 'uranus', 'neptune', or other astropy get_body() names)
        locale: Language locale code (e.g., 'en', 'en-US'); defaults to 'en'

    Returns:
        Dictionary containing:
            - altitude: Body's altitude in degrees (-90 to 90, negative = below horizon)
            - azimuth: Body's azimuth in degrees (0=North, 90=East, 180=South, 270=West)
            - is_visible: Boolean indicating if body is above horizon
            - ra_degrees: Body's right ascension in degrees (topocentric, observer-dependent)
            - dec_degrees: Body's declination in degrees (topocentric, observer-dependent)
            - julian_date: The JD for this calculation
            - input_datetime: The processed input string
            - location: Dictionary with lat, lon, elevation

    Raises:
        ValueError: If date/time format is invalid or coordinates out of range
    """
    obs_time, earth_location, altaz_frame, datetime_str = _setup_coordinates(
        observation_time, location, locale
    )

    # Get body position in topocentric GCRS coordinates (observer-dependent, includes parallax)
    body_with_loc = get_body(body_name, obs_time, earth_location)

    # Transform to AltAz frame
    body_altaz = body_with_loc.transform_to(altaz_frame)

    # Format and return position data using common processing function
    return _process_body_position(body_altaz, body_with_loc, obs_time, datetime_str, location)


def get_geocentric_body_coords(body_name: str, obs_time: Time):
    """
    Get geocentric GCRS coordinates for a celestial body.

    Used by outer planets and Mars for retrograde/phase calculations that require
    geocentric (not topocentric) coordinates.

    Args:
        body_name: Name of celestial body
        obs_time: Astropy Time object

    Returns:
        Coordinate object in GCRS frame at geocenter (not observer-dependent)
    """
    return get_body(body_name, obs_time)


def _process_body_position(
    body_altaz,
    body_with_loc,
    obs_time: Time,
    datetime_str: str,
    location: LocationModel
) -> dict:
    """
    Format celestial body position data into response dictionary.

    Common utility used by all body-specific position processing functions.
    Handles coordinate extraction and response formatting.

    Args:
        body_altaz: Body position in AltAz frame (for altitude/azimuth)
        body_with_loc: Body position in topocentric GCRS frame (for RA/Dec)
        obs_time: Astropy Time object
        datetime_str: Input datetime string
        location: Observer location with latitude, longitude, elevation

    Returns:
        Dictionary with formatted position data
    """
    # Extract altitude and azimuth
    altitude = float(body_altaz.alt.degree)
    azimuth = float(body_altaz.az.degree)

    # Determine visibility (above horizon means altitude > 0)
    is_visible = bool(altitude > 0)

    # Extract RA/Dec in GCRS frame (topocentric, observer-dependent)
    ra_degrees = float(body_with_loc.ra.degree)
    dec_degrees = float(body_with_loc.dec.degree)

    return {
        "altitude": altitude,
        "azimuth": azimuth,
        "is_visible": is_visible,
        "ra_degrees": ra_degrees,
        "dec_degrees": dec_degrees,
        "julian_date": float(obs_time.jd),
        "input_datetime": datetime_str,
        "location": {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "elevation": location.elevation
        }
    }


def calculate_planetary_phase_angle(planet_gcrs, sun) -> dict:
    """
    Calculate phase angle and illumination for a planet using planet-centric geometry.

    Shared by inferior planets (Venus, Mercury) and Mars (superior planet): all three
    use identical 3D-vector geometry and the same illumination formula. Only the
    interpretation/classification of the resulting phase differs by planet type
    (handled by each caller).

    Illumination Calculation:
    Phase angle is computed from 3D vectors: Sun direction from the planet and Earth
    direction from the planet. Illumination = (1 + cos(phase_angle)) / 2.

    Args:
        planet_gcrs: Planet position in GCRS coordinates (geocentric, from
            get_body(planet_name, time))
        sun: Sun position in GCRS coordinates (from get_sun(time))

    Returns:
        Dictionary containing:
            - illumination: Fraction of the planet's disk illuminated (0.0 to 1.0)
            - cos_phase_angle: Cosine of the planet-centric phase angle (float),
              useful for callers that classify phases directly from the phase angle
              (e.g. Mars)
            - phase_angle_ecliptic: Phase angle from ecliptic longitude difference
              (0 to 360 degrees), used to determine waxing/waning for inferior planets
    """
    # Get Cartesian positions (GCRS frame: Earth at origin)
    planet_pos = planet_gcrs.cartesian.xyz  # Vector from Earth to planet
    sun_pos = sun.cartesian.xyz  # Vector from Earth to Sun

    # Vectors from the planet's perspective
    vec_planet_to_sun = sun_pos - planet_pos  # Sun direction from planet
    vec_planet_to_earth = -planet_pos  # Earth direction from planet

    # Compute angle between the two vectors
    dot_prod = np.dot(vec_planet_to_sun, vec_planet_to_earth)
    mag_sun = np.linalg.norm(vec_planet_to_sun)
    mag_earth = np.linalg.norm(vec_planet_to_earth)

    cos_phase_angle = dot_prod / (mag_sun * mag_earth)
    # Clamp to avoid numerical errors in arccos
    cos_phase_angle = float(np.clip(cos_phase_angle, -1.0, 1.0))

    # Illumination: (1 + cos(phase_angle)) / 2
    illumination = float((1.0 + cos_phase_angle) / 2.0)

    # Phase angle from ecliptic longitudes (0-180° = waxing, 180-360° = waning)
    sun_lon = sun.geocentrictrueecliptic.lon.deg
    planet_lon = planet_gcrs.geocentrictrueecliptic.lon.deg
    phase_angle_ecliptic = float((planet_lon - sun_lon) % 360)

    return {
        "illumination": illumination,
        "cos_phase_angle": cos_phase_angle,
        "phase_angle_ecliptic": phase_angle_ecliptic,
    }
