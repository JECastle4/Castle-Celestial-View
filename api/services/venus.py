"""
Venus position calculation services
"""
from typing import Optional
from astropy.coordinates import get_body, get_sun, AltAz, EarthLocation
from astropy.time import Time
import astropy.units as u
import numpy as np
from api.i18n import get_i18n
from api.models import ObservationDateTime, LocationModel


def calculate_venus_position(
    observation_time: ObservationDateTime,
    location: LocationModel,
    locale: Optional[str] = None
) -> dict:
    """
    Calculate Venus's position and phase at a given time and location.

    Args:
        observation_time: Date and time of observation
        location: Observer location (latitude, longitude, elevation)
        locale: Language locale code (e.g., 'en', 'en-US'); defaults to 'en'

    Returns:
        Dictionary containing:
            - altitude: Venus's altitude in degrees (negative = below horizon)
            - azimuth: Venus's azimuth in degrees (0=North, 90=East, 180=South, 270=West)
            - is_visible: Boolean indicating if Venus is above horizon
            - illumination: Fraction of Venus's disk illuminated by the Sun (0.0 to 1.0),
              computed using Venus-centric phase angle (IAU standard for inferior planets).
              Ranges from ~0% at inferior conjunction (closest to Earth) to ~100% at
              superior conjunction (behind the Sun).
            - phase_angle: Venus's phase angle in ecliptic longitude (0 to 360 degrees),
              used to determine waxing vs waning
            - phase_name: Textual name of the phase based on illumination:
              New (0-10%), Crescent (10-35%), Quarter (35-50%),
              Gibbous (50-90%), Full (90%+)
            - sun_separation: Angular separation between Venus and Sun in degrees (elongation)
            - naked_eye_visible: Boolean indicating if Venus is observable to naked eye
              (requires altitude > 0° AND sun_separation > 10°)
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

    # Get Venus position and transform to AltAz coordinates
    venus_with_loc = get_body("venus", obs_time, earth_location)
    venus_altaz = venus_with_loc.transform_to(altaz_frame)

    # Get Sun and Venus at geocenter for geocentric separation/phase calculations
    sun = get_sun(obs_time)
    venus_gcrs = get_body("venus", obs_time)

    return _process_venus_position(
        venus_altaz, sun, venus_gcrs, obs_time, datetime_str, location,
        locale=locale
    )


def _process_venus_position(
    venus_altaz,
    sun,
    venus_gcrs,
    time: Time,
    datetime_str: str,
    location: LocationModel,
    locale: Optional[str] = None
) -> dict:
    """
    Process Venus position data into response format.
    Internal function used by calculate_venus_position and batch operations.

    Illumination Calculation:
    Uses Venus-centric phase angle (IAU standard for inferior planets).
    Phase angle is computed from 3D vectors: Sun direction from Venus and Earth
    direction from Venus. Illumination = (1 + cos(phase_angle)) / 2.

    Args:
        venus_altaz: Venus position in AltAz frame
        sun: Sun position (GCRS coordinates)
        venus_gcrs: Venus position (GCRS coordinates)
        time: Astropy Time object
        datetime_str: Input datetime string
        location: Observer location with latitude, longitude, elevation
        locale: Language locale code for phase names (defaults to 'en')

    Returns:
        Dictionary with Venus position data
    """
    i18n = get_i18n(locale)

    # Extract altitude and azimuth
    altitude = venus_altaz.alt.degree
    azimuth = venus_altaz.az.degree

    # Venus is visible if altitude is positive (above horizon)
    # Convert to Python bool to avoid numpy bool type
    is_visible = bool(altitude > 0)

    # Calculate Venus phase using Venus-centric geometry (IAU standard for inferior planets)
    # For an inferior planet, the phase angle must be computed from the planet's perspective
    # using 3D vectors, not from Earth's perspective using angular separation.
    # Get Cartesian positions (GCRS frame: Earth at origin)
    venus_pos = venus_gcrs.cartesian.xyz  # Vector from Earth to Venus
    sun_pos = sun.cartesian.xyz  # Vector from Earth to Sun

    # Vectors from Venus's perspective
    vec_venus_to_sun = sun_pos - venus_pos  # Sun direction from Venus
    vec_venus_to_earth = -venus_pos  # Earth direction from Venus

    # Compute angle between the two vectors
    dot_prod = np.dot(vec_venus_to_sun, vec_venus_to_earth)
    mag_sun = np.linalg.norm(vec_venus_to_sun)
    mag_earth = np.linalg.norm(vec_venus_to_earth)

    cos_phase_angle = dot_prod / (mag_sun * mag_earth)
    # Clamp to avoid numerical errors in arccos
    cos_phase_angle = np.clip(cos_phase_angle, -1.0, 1.0)

    # Illumination for an inferior planet: (1 + cos(phase_angle)) / 2
    illumination = float((1.0 + cos_phase_angle) / 2.0)

    # Compute elongation (angular separation between Venus and Sun from Earth)
    # This is still useful for determining naked-eye visibility
    elongation = sun.separation(venus_gcrs)
    sun_separation = float(elongation.deg)

    # Naked-eye visibility requires both altitude > 0° AND sufficient separation from Sun
    # Venus becomes lost in solar glare at elongations < ~8-10° even if geometrically visible
    # ~8° is the typical limit; use 10° for conservative safe margin
    min_elongation_for_visibility = 10.0  # degrees
    naked_eye_visible = bool(altitude > 0 and sun_separation > min_elongation_for_visibility)

    # Phase angle from ecliptic longitudes
    # 0-180° = waxing (new → full), 180-360° = waning (full → new)
    sun_lon = sun.geocentrictrueecliptic.lon.deg
    venus_lon = venus_gcrs.geocentrictrueecliptic.lon.deg
    phase_angle = float((venus_lon - sun_lon) % 360)

    # Determine phase name based on illumination and waxing/waning
    illum_pct = illumination * 100

    if phase_angle < 180:  # Waxing (new → full)
        if illum_pct < 10:
            phase_key = "new"
        elif illum_pct < 35:
            phase_key = "crescent"
        elif illum_pct < 50:
            phase_key = "quarter"
        elif illum_pct < 90:
            phase_key = "gibbous"
        else:  # 90%+
            phase_key = "full"
    else:  # Waning (full → new)
        if illum_pct > 90:
            phase_key = "full"
        elif illum_pct > 50:
            phase_key = "gibbous"
        elif illum_pct > 35:
            phase_key = "quarter"
        elif illum_pct > 10:
            phase_key = "crescent"
        else:  # <10%
            phase_key = "new"

    # Get localized phase name
    phase_name = i18n.get(f"venusPhases.{phase_key}")

    return {
        "altitude": float(altitude),
        "azimuth": float(azimuth),
        "is_visible": is_visible,
        "sun_separation": sun_separation,
        "naked_eye_visible": naked_eye_visible,
        "illumination": illumination,
        "phase_angle": phase_angle,
        "phase_name": phase_name,
        "julian_date": float(time.jd),
        "input_datetime": datetime_str,
        "location": {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "elevation": location.elevation
        }
    }
