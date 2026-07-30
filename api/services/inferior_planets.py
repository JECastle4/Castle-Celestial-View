"""
Inferior planets (Venus, Mercury) position and phase calculation utilities.

This module provides shared position and phase calculations for the inferior planets
(planets that orbit inside Earth's orbit). Venus and Mercury share identical phase
mechanics; they differ only in the minimum solar elongation required for naked-eye
visibility (Venus ~10°, Mercury ~14.5°, due to Mercury's closer orbit to the Sun).

Phase Calculation:
Uses planet-centric phase angle (IAU standard for inferior planets), computed via
api.services.common_bodies.calculate_planetary_phase_angle. Illumination ranges from
~0% at inferior conjunction (closest to Earth) to ~100% at superior conjunction
(behind the Sun).
"""
from typing import Optional

from astropy.coordinates import get_body, get_sun
from astropy.time import Time

from api.i18n import get_i18n
from api.models import ObservationDateTime, LocationModel
from api.services.common_bodies import (
    _setup_coordinates,
    _process_body_position,
    calculate_planetary_phase_angle,
)


# Minimum elongation (degrees) required for naked-eye visibility, per inferior planet.
# Below this threshold the planet is lost in solar glare even when geometrically
# above the horizon.
INFERIOR_PLANETS = {
    "venus": {"min_elongation_for_visibility": 10.0},
    "mercury": {"min_elongation_for_visibility": 14.5},
}


def calculate_inferior_planet_position(
    observation_time: ObservationDateTime,
    location: LocationModel,
    planet_name: str,
    locale: Optional[str] = None
) -> dict:
    """
    Calculate an inferior planet's position and phase at a given time and location.

    Handles Venus and Mercury.

    Args:
        observation_time: Date and time of observation
        location: Observer location (latitude, longitude, elevation)
        planet_name: Name of the planet ("venus" or "mercury")
        locale: Language locale code (e.g., 'en', 'en-US'); defaults to 'en'

    Returns:
        Dictionary containing:
            - altitude: Planet's altitude in degrees (negative = below horizon)
            - azimuth: Planet's azimuth in degrees (0=North, 90=East, 180=South, 270=West)
            - is_visible: Boolean indicating if planet is above horizon
            - illumination: Fraction of the planet's disk illuminated by the Sun
              (0.0 to 1.0), computed using planet-centric phase angle
            - phase_angle: Planet's phase angle in ecliptic longitude (0 to 360 degrees),
              used to determine waxing vs waning
            - phase_name: Textual name of the phase based on illumination:
              New (0-10%), Crescent (10-35%), Quarter (35-50%),
              Gibbous (50-90%), Full (90%+)
            - sun_separation: Angular separation between the planet and Sun in degrees
              (elongation)
            - naked_eye_visible: Boolean indicating if the planet is observable to
              naked eye (requires altitude > 0° AND sufficient sun_separation)
            - julian_date: The JD for this calculation
            - input_datetime: The processed input string
            - location: Dictionary with lat, lon, elevation

    Raises:
        ValueError: If date/time format is invalid or coordinates out of range
    """
    obs_time, earth_location, altaz_frame, datetime_str = _setup_coordinates(
        observation_time, location, locale
    )

    # Get planet position and transform to AltAz coordinates
    planet_with_loc = get_body(planet_name, obs_time, earth_location)
    planet_altaz = planet_with_loc.transform_to(altaz_frame)

    # Get Sun and planet at geocenter for geocentric separation/phase calculations
    sun = get_sun(obs_time)
    planet_gcrs = get_body(planet_name, obs_time)

    return _process_inferior_planet_position(
        planet_with_loc, planet_altaz, sun, planet_gcrs, obs_time, datetime_str, location,
        planet_name, locale=locale
    )


def _process_inferior_planet_position(
    planet_with_loc,
    planet_altaz,
    sun,
    planet_gcrs,
    time: Time,
    datetime_str: str,
    location: LocationModel,
    planet_name: str,
    locale: Optional[str] = None
) -> dict:
    """
    Process inferior planet position data into response format.
    Internal function shared by Venus and Mercury (single-frame and batch operations).

    Args:
        planet_with_loc: Planet position in topocentric GCRS frame
            (observer-dependent, includes parallax)
        planet_altaz: Planet position in AltAz frame
        sun: Sun position (GCRS coordinates)
        planet_gcrs: Planet position (GCRS coordinates)
        time: Astropy Time object
        datetime_str: Input datetime string
        location: Observer location with latitude, longitude, elevation
        planet_name: Name of the planet ("venus" or "mercury"), used for the
            naked-eye visibility threshold and localized phase name lookup
        locale: Language locale code for phase names (defaults to 'en')

    Returns:
        Dictionary with the planet's position and phase data
    """
    i18n = get_i18n(locale)

    # Format base position data (altitude, azimuth, is_visible, RA/Dec, etc.)
    position_dict = _process_body_position(
        planet_altaz, planet_with_loc, time, datetime_str, location
    )

    # Calculate phase using shared planet-centric geometry
    phase = calculate_planetary_phase_angle(planet_gcrs, sun)
    illumination = phase["illumination"]
    phase_angle = phase["phase_angle_ecliptic"]

    # Compute elongation (angular separation between planet and Sun from Earth)
    # Used to determine naked-eye visibility
    elongation = sun.separation(planet_gcrs)
    sun_separation = float(elongation.deg)

    # Naked-eye visibility requires both altitude > 0° AND sufficient separation from
    # Sun; the planet becomes lost in solar glare below its elongation threshold
    min_elongation = INFERIOR_PLANETS[planet_name]["min_elongation_for_visibility"]
    naked_eye_visible = bool(
        position_dict["altitude"] > 0 and sun_separation > min_elongation
    )

    # Determine phase name based on illumination and waxing/waning
    phase_key = _classify_inferior_planet_phase(illumination * 100, phase_angle)
    phase_name = i18n.get(f"{planet_name}Phases.{phase_key}")

    position_dict.update({
        "sun_separation": sun_separation,
        "naked_eye_visible": naked_eye_visible,
        "illumination": illumination,
        "phase_angle": phase_angle,
        "phase_name": phase_name,
    })

    return position_dict


def _classify_inferior_planet_phase(illum_pct: float, phase_angle: float) -> str:
    """
    Classify an inferior planet's phase key from illumination percentage and
    waxing/waning direction.

    Args:
        illum_pct: Illumination percentage (0-100)
        phase_angle: Phase angle in ecliptic longitude (0-360 degrees);
            0-180° = waxing (new -> full), 180-360° = waning (full -> new)

    Returns:
        Phase key: "new", "crescent", "quarter", "gibbous", or "full"
    """
    if phase_angle < 180:  # Waxing (new → full)
        for threshold, phase_key in (
            (10, "new"), (35, "crescent"), (50, "quarter"), (90, "gibbous")
        ):
            if illum_pct < threshold:
                return phase_key
        return "full"  # 90%+

    # Waning (full → new)
    for threshold, phase_key in (
        (90, "full"), (50, "gibbous"), (35, "quarter"), (10, "crescent")
    ):
        if illum_pct > threshold:
            return phase_key
    return "new"  # <10%
