"""
Mars position calculation services

PHASE STRATEGY ACROSS CELESTIAL BODIES:
========================================
Different celestial bodies have different phase characteristics based on their orbital
positions relative to Earth and the Sun. The API implements phases for bodies where they
are astronomically significant:

  Moon:
    - Type: Satellite (orbits Earth)
    - Phase range: 0% to 100% illumination
    - Phase names: New, Waxing Crescent, First Quarter, Waxing Gibbous, Full,
                   Waning Gibbous, Last Quarter, Waning Crescent (8 phases)
    - Always visible (no glare threshold)

  Venus (Inferior Planet):
    - Type: Inferior planet (orbit inside Earth's)
    - Max phase angle: 47° (max illumination variation: 14% to 100%)
    - Phase names: New, Crescent, Quarter, Gibbous, Full (5 phases)
    - Glare threshold: 10° elongation (disappears in solar glare)
    - Visible only as "Morning Star" or "Evening Star"

  Mercury (Inferior Planet):
    - Type: Inferior planet (orbit inside Earth's)
    - Max phase angle: 28° (max illumination variation: 28% to 100%)
    - Phase names: New, Crescent, Quarter, Gibbous, Full (5 phases)
    - Glare threshold: 18° elongation (disappears in solar glare)
    - Visible only as "Morning Star" or "Evening Star" (brief visibility)

  Mars (Superior Planet) - THIS FILE:
    - Type: Superior planet (orbit outside Earth's)
    - Max phase angle: 45° (max illumination variation: 50% to 100%)
    - Phase names: Crescent, Gibbous, Full (3 phases)
    - Always visible when above horizon (no glare threshold)
    - Can exhibit retrograde motion ~every 26 months when Earth overtakes it
    - Illumination formula: (1 + cos(phase_angle)) / 2

  Jupiter, Saturn, Uranus, Neptune (Superior Planets):
    - Type: Superior planets (orbits outside Earth's)
    - Max phase angle: ~11° (max illumination variation: 99.9% to 100%)
    - Phase names: None (always appears full) - not implemented
    - Always visible when above horizon
    - Illumination effectively constant at ~100%

KEY INSIGHTS:
- Inferior planets (Venus, Mercury) have larger phase variations and glare constraints
- Superior planets (Mars, Jupiter+) have smaller phase variations
- Mars bridges the gap: superior planet position but significant phase angle (45°)
- Only Moon, Venus, Mercury, and Mars need phase calculations for user interface
- Jupiter+ can be treated as always-full (illumination effectively 100%)

Mars Key Characteristics:
- Phase angle maximum: 45° (superior planet geometry)
- Phases are classified by phase angle:
  * Full (0-15°, ~100-96% illum)
  * Gibbous (15-30°, ~96-92% illum)
  * Crescent (30-45°, ~92-84% illum)
- No elongation threshold for visibility (unlike Mercury/Venus)
- Always visible when above horizon (doesn't disappear in solar glare)
- Retrograde motion possible: ~every 26 months when Earth overtakes Mars
"""
from typing import Optional
from astropy.coordinates import (
    get_body, get_sun, AltAz, EarthLocation, HeliocentricTrueEcliptic
)
from astropy.time import Time
import astropy.units as u
import numpy as np
from api.i18n import get_i18n
from api.models import ObservationDateTime, LocationModel


def calculate_mars_position(
    observation_time: ObservationDateTime,
    location: LocationModel,
    locale: Optional[str] = None
) -> dict:
    """
    Calculate Mars's position and phase at a given time and location.

    Args:
        observation_time: Date and time of observation
        location: Observer location (latitude, longitude, elevation)
        locale: Language locale code (e.g., 'en', 'en-US'); defaults to 'en'

    Returns:
        Dictionary containing:
            - altitude: Mars's altitude in degrees (negative = below horizon)
            - azimuth: Mars's azimuth in degrees (0=North, 90=East, 180=South, 270=West)
            - is_visible: Boolean indicating if Mars is above horizon
            - illumination: Fraction of Mars's disk illuminated (0.0 to 1.0),
              computed using Mars-centric phase angle (superior planet geometry).
              Ranges from ~84% to ~100%
              (Mars never reaches 50% due to max phase angle of 45°).
              Note: Mars never has 0% illumination from Earth (never passes directly
              behind Sun from our perspective).
            - phase_angle: Mars's phase angle in ecliptic longitude (0 to 360 degrees)
            - phase_name: Textual name of the phase based on phase angle:
              - Full (0-15°, ~100-96% illum)
              - Gibbous (15-30°, ~96-92% illum)
              - Crescent (30-45°, ~92-84% illum)
            - retrograde_status: Whether Mars is in retrograde motion from Earth's
              perspective ("prograde" or "retrograde"). Retrograde occurs ~every 26 months
              when Earth overtakes Mars, lasting ~2.5 months.
            - julian_date: The JD for this calculation
            - input_datetime: The processed input string
            - location: Dictionary with lat, lon, elevation

    Raises:
        ValueError: If date/time format is invalid or coordinates out of range
    """
    i18n = get_i18n(locale)

    # Validate coordinates
    if not -90 <= location.latitude <= 90:
        raise ValueError(i18n.get('validation.latitudeRange', value=location.latitude))
    if not -180 <= location.longitude <= 180:
        raise ValueError(i18n.get('validation.longitudeRange', value=location.longitude))

    # Combine date and time (ISO 8601 format)
    datetime_str = f"{observation_time.date}T{observation_time.time}Z"

    # Convert to astropy Time
    obs_time = Time(datetime_str.rstrip('Z'), format='isot', scale='utc')

    # Create Earth location
    earth_location = EarthLocation(
        lat=location.latitude * u.deg,
        lon=location.longitude * u.deg,
        height=location.elevation * u.m
    )

    # Create AltAz frame (pressure=0 to ignore atmospheric refraction for simplicity)
    altaz_frame = AltAz(obstime=obs_time, location=earth_location, pressure=0.0)

    # Get Mars position and transform to AltAz coordinates
    mars_with_loc = get_body("mars", obs_time, earth_location)
    mars_altaz = mars_with_loc.transform_to(altaz_frame)

    # Get Sun and Mars at geocenter for geocentric separation/phase calculations
    sun = get_sun(obs_time)
    mars_gcrs = get_body("mars", obs_time)

    return _process_mars_position(
        mars_with_loc, mars_altaz, sun, mars_gcrs, obs_time, datetime_str, location,
        locale=locale
    )


def _process_mars_position(
    mars_with_loc,
    mars_altaz,
    sun,
    mars_gcrs,
    time: Time,
    datetime_str: str,
    location: LocationModel,
    locale: Optional[str] = None,  # pylint: disable=unused-argument
    retrograde_status: Optional[str] = None
) -> dict:
    """
    Process Mars position data into response format.
    Internal function used by calculate_mars_position and batch operations.

    Illumination Calculation (Superior Planet):
    Mars is a superior planet (orbit outside Earth's). The illumination varies based on
    the phase angle at Mars between the Sun and Earth.
    Phase angle = angle at Mars between Sun and Earth directions.
    Illumination = (1 + cos(phase_angle)) / 2 (same formula as inferior planets, different geometry)

    For Mars with max ~45° phase angle (never reaches quadrature/conjunction):
    - Opposition (0° phase angle): ~100% illuminated (closest to Earth, fully lit)
    - Maximum elongation (~45° phase angle): ~84% illuminated (gibbous phase)
    - Mars never reaches quadrature (90°) or conjunction (180°) due to orbital geometry

    Retrograde Motion Detection:
    Mars appears to move backward relative to the stars when Earth overtakes it in orbit.
    This is detected by calculating the heliocentric longitude rate of change:
    - If d_lon/dt < 0 (negative rate): retrograde motion
    - If d_lon/dt > 0 (positive rate): prograde motion

    Args:
        mars_with_loc: Mars position in topocentric GCRS frame
        mars_altaz: Mars position in AltAz frame
        sun: Sun position (GCRS coordinates)
        mars_gcrs: Mars position (GCRS coordinates)
        time: Astropy Time object
        datetime_str: Input datetime string
        location: Observer location with latitude, longitude, elevation
        locale: Language locale code for phase names (defaults to 'en')

    Returns:
        Dictionary with Mars position data
    """
    i18n = get_i18n(locale)

    # Extract altitude and azimuth
    altitude = mars_altaz.alt.degree
    azimuth = mars_altaz.az.degree

    # Mars is visible if altitude is positive (above horizon)
    # No elongation threshold needed (unlike Mercury/Venus)
    # Convert to Python bool to avoid numpy bool type
    is_visible = bool(altitude > 0)

    # Calculate Mars phase using Mars-centric geometry (superior planet)
    # For a superior planet, phase angle must be computed from Mars's perspective
    # Get Cartesian positions (GCRS frame: Earth at origin)
    mars_pos = mars_gcrs.cartesian.xyz  # Vector from Earth to Mars
    sun_pos = sun.cartesian.xyz  # Vector from Earth to Sun

    # Vectors from Mars's perspective
    vec_mars_to_sun = sun_pos - mars_pos  # Sun direction from Mars
    vec_mars_to_earth = -mars_pos  # Earth direction from Mars

    # Compute angle between the two vectors
    dot_prod = np.dot(vec_mars_to_sun, vec_mars_to_earth)
    mag_sun = np.linalg.norm(vec_mars_to_sun)
    mag_earth = np.linalg.norm(vec_mars_to_earth)

    cos_phase_angle = dot_prod / (mag_sun * mag_earth)
    # Clamp to avoid numerical errors in arccos
    cos_phase_angle = np.clip(cos_phase_angle, -1.0, 1.0)

    # Illumination for a superior planet: (1 + cos(phase_angle)) / 2
    illumination = float((1.0 + cos_phase_angle) / 2.0)

    # Phase angle from ecliptic longitudes
    sun_lon = sun.geocentrictrueecliptic.lon.deg
    mars_lon = mars_gcrs.geocentrictrueecliptic.lon.deg
    phase_angle = float((mars_lon - sun_lon) % 360)  # pylint: disable=line-too-long

    # Determine phase name based on Mars-centric phase angle
    # Mars max phase angle ~45° means illumination ranges ~84-100%, so
    # illumination thresholds are ineffective.
    # Instead, classify using the phase angle directly from cos_phase_angle:
    # - 0° (opposition): Full phase (~100% illuminated)
    # - ~15-30°: Gibbous phase (~96-92% illuminated)
    # - ~30-45° (max elongation): Crescent phase (~85-86% illuminated)
    # Convert cos_phase_angle to Python float (may be astropy Quantity) before
    # using with numpy
    cos_value = float(cos_phase_angle)
    phase_angle_deg = float(np.degrees(np.arccos(cos_value)))

    if phase_angle_deg <= 15:
        phase_key = "full"
    elif phase_angle_deg <= 30:
        phase_key = "gibbous"
    else:  # > 30° (up to ~45° max)
        phase_key = "crescent"

    # Get localized phase name
    phase_name = i18n.get(f"marsPhases.{phase_key}")

    # Determine retrograde status (pre-computed in batch mode, calculated on-demand in
    # single-frame mode)
    if retrograde_status is None:
        retrograde_status = _get_retrograde_status(mars_gcrs, sun, time)

    # Extract RA/Dec in GCRS frame (topocentric/apparent, observer-dependent)
    # Mars coordinates from get_body(..., earth_location) are topocentric coordinates
    # that account for parallax based on observer location and distance to Mars
    ra_degrees = float(mars_with_loc.ra.degree)
    dec_degrees = float(mars_with_loc.dec.degree)

    return {
        "altitude": float(altitude),
        "azimuth": float(azimuth),
        "is_visible": is_visible,
        "ra_degrees": ra_degrees,
        "dec_degrees": dec_degrees,
        "illumination": illumination,
        "phase_angle": phase_angle,
        "phase_name": phase_name,
        "retrograde_status": retrograde_status,
        "julian_date": float(time.jd),
        "input_datetime": datetime_str,
        "location": {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "elevation": location.elevation
        }
    }


def _get_retrograde_status_from_longitudes(lon_before: float, lon_after: float) -> str:
    """
    Determine retrograde status from two heliocentric longitudes (finite differences).

    Optimized for batch processing: uses pre-computed heliocentric longitudes from
    adjacent frames instead of making additional ephemeris lookups.

    Args:
        lon_before: Mars heliocentric ecliptic longitude at earlier time (degrees)
        lon_after: Mars heliocentric ecliptic longitude at later time (degrees)

    Returns:
        "retrograde" if longitude is decreasing, else "prograde"
    """
    # Calculate longitude rate
    # Handle wraparound at 360°
    dlon = (lon_after - lon_before) % 360
    if dlon > 180:
        dlon -= 360

    # If longitude is decreasing (negative rate), Mars is in retrograde motion
    if dlon < 0:
        return "retrograde"
    return "prograde"


def _get_retrograde_status(_mars_gcrs, _sun, obs_time: Time) -> str:
    """
    Determine if Mars is in retrograde motion by calculating heliocentric longitude rate.

    Retrograde motion occurs when Earth overtakes Mars in their orbits, causing Mars
    to appear to move backward against the stars from Earth's perspective. This happens
    ~every 26 months and lasts ~2.5 months.

    Method: Calculate Mars's heliocentric longitude at current time and nearby time,
    then check if longitude is increasing (prograde) or decreasing (retrograde).

    NOTE: This function is optimized for single-frame calculations. For batch processing,
    use _get_retrograde_status_from_longitudes() with pre-computed heliocentric longitudes
    to avoid redundant ephemeris lookups.

    Args:
        _mars_gcrs: Mars position at current time (GCRS frame) [unused, kept for API]
        _sun: Sun position at current time (GCRS frame) [unused, kept for API]
        obs_time: Astropy Time object

    Returns:
        "retrograde" if Mars is moving backward relative to Sun, else "prograde"
    """
    # Time step for numerical derivative (1 day in both directions)
    time_step = 1.0 * u.day

    # Get times for derivative calculation
    t_minus = obs_time - time_step
    t_plus = obs_time + time_step

    # Get Mars positions at ±1 day
    mars_minus = get_body("mars", t_minus)
    mars_plus = get_body("mars", t_plus)

    # Transform to heliocentric ecliptic frame
    mars_minus_heliocentric = mars_minus.transform_to(
        HeliocentricTrueEcliptic(obstime=t_minus)
    )
    mars_plus_heliocentric = mars_plus.transform_to(
        HeliocentricTrueEcliptic(obstime=t_plus)
    )

    # Extract heliocentric ecliptic longitudes
    lon_minus = mars_minus_heliocentric.lon.degree
    lon_plus = mars_plus_heliocentric.lon.degree

    return _get_retrograde_status_from_longitudes(lon_minus, lon_plus)
