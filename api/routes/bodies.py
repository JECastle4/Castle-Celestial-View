"""
API routes for celestial body positions (sun, moon, planets, phases).
"""
from fastapi import APIRouter
from api.cache import cache_response
from api.i18n import get_i18n
from api.models import (
    DateTimeRequest,
    DayOfWeekResponse,
    SunPositionRequest,
    SunPositionResponse,
    MoonPositionRequest,
    MoonPositionResponse,
    VenusPositionRequest,
    VenusPositionResponse,
    MercuryPositionRequest,
    MercuryPositionResponse,
    MarsPositionRequest,
    MarsPositionResponse,
    JupiterPositionRequest,
    JupiterPositionResponse,
    SaturnPositionRequest,
    SaturnPositionResponse,
    UranusPositionRequest,
    UranusPositionResponse,
    NeptunePositionRequest,
    NeptunePositionResponse,
    MoonPhaseRequest,
    MoonPhaseResponse,
)
from api.services.dates import calculate_day_of_week
from api.services.sun import calculate_sun_position
from api.services.moon import calculate_moon_position
from api.services.venus import calculate_venus_position
from api.services.mercury import calculate_mercury_position
from api.services.mars import calculate_mars_position
from api.services.jupiter import calculate_jupiter_position
from api.services.saturn import calculate_saturn_position
from api.services.uranus import calculate_uranus_position
from api.services.neptune import calculate_neptune_position
from api.services.moon_phase import calculate_moon_phase
from .helpers import handle_route_errors, build_observation_datetime, build_location_from_request


router = APIRouter(tags=["bodies"])


@router.post("/day-of-week", response_model=DayOfWeekResponse)
@handle_route_errors("calculating day of week")
async def get_day_of_week(request: DateTimeRequest):
    """
    Calculate the day of the week from a given date and time.

    Converts the input date/time to Julian Date (JD) using astropy,
    then calculates which day of the week it falls on.

    - **date**: Date in ISO format (YYYY-MM-DD)
    - **time**: Optional time in HH:MM:SS format (defaults to 00:00:00)

    Returns:
    - **julian_date**: The JD as a float
    - **day_of_week**: Integer 0-6 (0=Sunday)
    - **day_name**: Name of the day
    - **input_datetime**: The processed input
    """
    obs_time = build_observation_datetime(request.date, request.time)
    result = calculate_day_of_week(obs_time.date, obs_time.time)
    return DayOfWeekResponse(**result)


@router.post("/sun-position", response_model=SunPositionResponse)
@cache_response(ttl=300)
@handle_route_errors("calculating sun position")
async def get_sun_position(request: SunPositionRequest):
    """
    Calculate the sun's position at a given time and location.

    Returns altitude (angle above horizon) and azimuth (compass direction),
    along with visibility status.

    - **date**: Date in ISO format (YYYY-MM-DD)
    - **time**: Time in HH:MM:SS format
    - **latitude**: Latitude in degrees (-90 to 90)
    - **longitude**: Longitude in degrees (-180 to 180)
    - **elevation**: Elevation above sea level in meters (optional)

    Returns:
    - **altitude**: Sun's altitude in degrees (negative = below horizon)
    - **azimuth**: Sun's azimuth in degrees (0=North, 90=East)
    - **is_visible**: True if sun is above horizon
    - **julian_date**: JD for this calculation
    - **input_datetime**: The processed input
    - **location**: The location used for calculation
    """
    observation_time = build_observation_datetime(request.date, request.time)
    location = build_location_from_request(
        request.latitude,
        request.longitude,
        request.elevation
    )
    result = calculate_sun_position(observation_time, location)
    return SunPositionResponse(**result)


@router.post("/moon-position", response_model=MoonPositionResponse)
@cache_response(ttl=300)
@handle_route_errors("calculating moon position")
async def get_moon_position(request: MoonPositionRequest):
    """
    Calculate the moon's position at a given time and location.

    Returns altitude (angle above horizon) and azimuth (compass direction),
    along with visibility status.

    - **date**: Date in ISO format (YYYY-MM-DD)
    - **time**: Time in HH:MM:SS format
    - **latitude**: Latitude in degrees (-90 to 90)
    - **longitude**: Longitude in degrees (-180 to 180)
    - **elevation**: Elevation above sea level in meters (optional)

    Returns:
    - **altitude**: Moon's altitude in degrees (negative = below horizon)
    - **azimuth**: Moon's azimuth in degrees (0=North, 90=East)
    - **is_visible**: True if moon is above horizon
    - **julian_date**: JD for this calculation
    - **input_datetime**: The processed input
    - **location**: The location used for calculation
    """
    observation_time = build_observation_datetime(request.date, request.time)
    location = build_location_from_request(
        request.latitude,
        request.longitude,
        request.elevation
    )
    result = calculate_moon_position(observation_time, location)
    return MoonPositionResponse(**result)


@router.post("/venus-position", response_model=VenusPositionResponse)
@cache_response(ttl=300)
@handle_route_errors("calculating Venus position")
async def get_venus_position(request: VenusPositionRequest):
    """
    Calculate Venus's position and phase at a given time and location.

    Returns altitude (angle above horizon), azimuth (compass direction), visibility status,
    sun separation (elongation), and phase information (illumination, phase angle, phase name).

    Venus visibility has two dimensions:
    - **Geometric visibility** (is_visible): Venus is above the horizon
    - **Observable visibility** (naked_eye_visible): Venus is above horizon AND sufficiently
      separated from the Sun (typically >10° elongation) to avoid being drowned out by solar glare

    Phase Calculation:
    Venus illumination is computed using Venus-centric phase angle
    (IAU standard for inferior planets). Illumination ranges from ~0% at inferior
    conjunction (closest to Earth) to ~100% at superior
    conjunction (behind the Sun). Phases are classified by illumination:
    - New: 0-10%, Crescent: 10-35%, Quarter: 35-50%, Gibbous: 50-90%, Full: 90%+

    Note: Venus phase requires a telescope to observe. The "phase angle" field (ecliptic
    longitude difference) is distinct from illumination and indicates waxing/waning direction.

    - **date**: Date in ISO format (YYYY-MM-DD)
    - **time**: Time in HH:MM:SS format
    - **latitude**: Latitude in degrees (-90 to 90)
    - **longitude**: Longitude in degrees (-180 to 180)
    - **elevation**: Elevation above sea level in meters (optional)

    Returns:
    - **altitude**: Venus's altitude in degrees (negative = below horizon)
    - **azimuth**: Venus's azimuth in degrees (0=North, 90=East)
    - **is_visible**: True if Venus is above horizon (altitude > 0°)
    - **sun_separation**: Angular separation between Venus and Sun in degrees (elongation)
    - **naked_eye_visible**: True if Venus is both above horizon AND far enough from Sun
    - **illumination**: Fraction of Venus illuminated (0.0 to 1.0),
      computed from Venus-centric phase angle
    - **phase_angle**: Venus's phase angle in ecliptic longitude (0 to 360
      degrees), for waxing/waning
    - **phase_name**: Textual phase name (New, Crescent, Quarter, Gibbous, Full)
    - **julian_date**: JD for this calculation
    - **input_datetime**: The processed input
    - **location**: The location used for calculation
    """
    observation_time = build_observation_datetime(request.date, request.time)
    location = build_location_from_request(
        request.latitude,
        request.longitude,
        request.elevation
    )
    result = calculate_venus_position(
        observation_time,
        location,
        locale=get_i18n().locale,
    )
    return VenusPositionResponse(**result)


@router.post("/mercury-position", response_model=MercuryPositionResponse)
@handle_route_errors("calculating Mercury position")
async def get_mercury_position(request: MercuryPositionRequest):
    """
    Calculate Mercury's position and phase at a given time and location.

    Returns altitude (angle above horizon), azimuth (compass direction), visibility status,
    sun separation (elongation), and phase information (illumination, phase angle, phase name).

    Mercury visibility has two dimensions:
    - **Geometric visibility** (is_visible): Mercury is above the horizon
    - **Observable visibility** (naked_eye_visible): Mercury is above horizon AND sufficiently
      separated from the Sun (typically >14.5° elongation due to Mercury's close orbit)

    Phase Calculation:
    Mercury illumination is computed using Mercury-centric phase angle
    (IAU standard for inferior planets). Illumination ranges from ~0% at inferior
    conjunction (closest to Earth) to ~100% at superior
    conjunction (behind the Sun). Phases are classified by illumination:
    - New: 0-10%, Crescent: 10-35%, Quarter: 35-50%, Gibbous: 50-90%, Full: 90%+

    Note: Mercury phase requires a telescope to observe. The "phase angle" field (ecliptic
    longitude difference) is distinct from illumination and indicates waxing/waning direction.
    Mercury is more difficult to observe than Venus due to its closer proximity to the Sun.

    - **date**: Date in ISO format (YYYY-MM-DD)
    - **time**: Time in HH:MM:SS format
    - **latitude**: Latitude in degrees (-90 to 90)
    - **longitude**: Longitude in degrees (-180 to 180)
    - **elevation**: Elevation above sea level in meters (optional)

    Returns:
    - **altitude**: Mercury's altitude in degrees (negative = below horizon)
    - **azimuth**: Mercury's azimuth in degrees (0=North, 90=East)
    - **is_visible**: True if Mercury is above horizon (altitude > 0°)
    - **sun_separation**: Angular separation between Mercury and Sun in degrees (elongation)
    - **naked_eye_visible**: True if Mercury is both above horizon AND far enough from Sun
    - **illumination**: Fraction of Mercury illuminated (0.0 to 1.0),
      computed from Mercury-centric phase angle
    - **phase_angle**: Mercury's phase angle in ecliptic longitude (0 to 360
      degrees), for waxing/waning
    - **phase_name**: Textual phase name (New, Crescent, Quarter, Gibbous, Full)
    - **julian_date**: JD for this calculation
    - **input_datetime**: The processed input
    - **location**: The location used for calculation
    """
    observation_time = build_observation_datetime(request.date, request.time)
    location = build_location_from_request(
        request.latitude,
        request.longitude,
        request.elevation
    )
    result = calculate_mercury_position(
        observation_time,
        location,
        locale=get_i18n().locale,
    )
    return MercuryPositionResponse(**result)


@router.post("/mars-position", response_model=MarsPositionResponse)
@cache_response(ttl=300)
@handle_route_errors("calculating Mars position")
async def get_mars_position(request: MarsPositionRequest):
    """
    Calculate Mars's position and phase at a given time and location.

    Returns altitude (angle above horizon), azimuth (compass direction), visibility status,
    and phase information (illumination, phase angle, phase name, retrograde status).

    Mars Characteristics:
    Mars is a superior planet (orbit outside Earth's). Key differences from Mercury/Venus:
    - Phase angle maximum: 45° (vs Venus 47°, Mercury 28°)
    - Illumination ranges from ~84% to ~100% (never reaches 50% unlike inferior planets)
    - No elongation threshold for visibility (always visible when above horizon)
    - Exhibits retrograde motion ~every 26 months when Earth overtakes it (~2.5 month duration)

    Phase Calculation (Superior Planet):
    Mars illumination is computed using Mars-centric phase angle (IAU standard).
    The phase angle is determined by the angle at Mars between the Sun and Earth.
    Phases are classified by phase angle:
    - Full: 0-15° phase angle (~100-96% illumination, opposition region)
    - Gibbous: 15-30° phase angle (~96-92% illumination, near quadrature)
    - Crescent: 30-45° phase angle (~92-84% illumination, max elongation)

    Retrograde Motion:
    Retrograde motion occurs when Earth's faster orbital speed causes us to overtake Mars,
    making it appear to move backward against the stars. This is detected by calculating
    heliocentric longitude rate of change.

    Parameters:
    - **date**: Date in ISO format (YYYY-MM-DD)
    - **time**: Time in HH:MM:SS format
    - **latitude**: Latitude in degrees (-90 to 90)
    - **longitude**: Longitude in degrees (-180 to 180)
    - **elevation**: Elevation above sea level in meters (optional)

    Returns:
    - **altitude**: Mars's altitude in degrees (negative = below horizon)
    - **azimuth**: Mars's azimuth in degrees (0=North, 90=East)
    - **is_visible**: True if Mars is above horizon (altitude > 0°)
    - **illumination**: Fraction of Mars illuminated (0.0 to 1.0)
    - **phase_angle**: Mars's phase angle in ecliptic longitude (0 to 360 degrees)
    - **phase_name**: Textual phase name (Full, Gibbous, Crescent)
    - **retrograde_status**: Current retrograde motion status (prograde or retrograde)
    - **julian_date**: JD for this calculation
    - **input_datetime**: The processed input
    - **location**: The location used for calculation
    """
    observation_time = build_observation_datetime(request.date, request.time)
    location = build_location_from_request(
        request.latitude,
        request.longitude,
        request.elevation
    )
    result = calculate_mars_position(
        observation_time,
        location,
        locale=get_i18n().locale,
    )
    return MarsPositionResponse(**result)


@router.post("/jupiter-position", response_model=JupiterPositionResponse)
@handle_route_errors("calculating Jupiter position")
async def get_jupiter_position(request: JupiterPositionRequest):
    """
    Calculate Jupiter's position at a given time and location.

    Returns altitude (angle above horizon), azimuth (compass direction), visibility status,
    and retrograde motion status.

    Jupiter Characteristics:
    Jupiter is a superior planet (orbit outside Earth's). As a distant outer planet:
    - Phase angle maximum: ~11° (negligible variation in illumination, always ~99.9%+ lit)
    - Always visible when above horizon (no elongation threshold)
    - Exhibits retrograde motion annually (~4 months retrograde per synodic period ~13 months)
    - Appears as a non-varying bright disk; no meaningful phases for observation

    Parameters:
    - **date**: Date in ISO format (YYYY-MM-DD)
    - **time**: Time in HH:MM:SS format
    - **latitude**: Latitude in degrees (-90 to 90)
    - **longitude**: Longitude in degrees (-180 to 180)
    - **elevation**: Elevation above sea level in meters (optional)

    Returns:
    - **altitude**: Jupiter's altitude in degrees (negative = below horizon)
    - **azimuth**: Jupiter's azimuth in degrees (0=North, 90=East)
    - **is_visible**: True if Jupiter is above horizon
    - **retrograde_status**: Current retrograde motion status (prograde or retrograde)
    - **ra_degrees**: Right ascension in degrees
    - **dec_degrees**: Declination in degrees
    - **julian_date**: JD for this calculation
    - **input_datetime**: The processed input
    - **location**: The location used for calculation
    """
    observation_time = build_observation_datetime(request.date, request.time)
    location = build_location_from_request(
        request.latitude,
        request.longitude,
        request.elevation
    )
    result = calculate_jupiter_position(
        observation_time,
        location,
        locale=get_i18n().locale,
    )
    return JupiterPositionResponse(**result)


@router.post("/saturn-position", response_model=SaturnPositionResponse)
@handle_route_errors("calculating Saturn position")
async def get_saturn_position(request: SaturnPositionRequest):
    """
    Calculate Saturn's position at a given time and location.

    Returns altitude (angle above horizon), azimuth (compass direction), visibility status,
    and retrograde motion status.

    Saturn Characteristics:
    Saturn is a superior planet (orbit outside Earth's). As a distant outer planet:
    - Phase angle maximum: ~5° (negligible variation in illumination, always ~99.95%+ lit)
    - Always visible when above horizon (no elongation threshold)
    - Exhibits retrograde motion annually (~4.5 months retrograde per synodic period ~12.4 months)
    - Appears as a non-varying bright disk; no meaningful phases for observation
    - Rings visible to telescopes but not relevant for positional astronomy

    Parameters:
    - **date**: Date in ISO format (YYYY-MM-DD)
    - **time**: Time in HH:MM:SS format
    - **latitude**: Latitude in degrees (-90 to 90)
    - **longitude**: Longitude in degrees (-180 to 180)
    - **elevation**: Elevation above sea level in meters (optional)

    Returns:
    - **altitude**: Saturn's altitude in degrees (negative = below horizon)
    - **azimuth**: Saturn's azimuth in degrees (0=North, 90=East)
    - **is_visible**: True if Saturn is above horizon
    - **retrograde_status**: Current retrograde motion status (prograde or retrograde)
    - **ra_degrees**: Right ascension in degrees
    - **dec_degrees**: Declination in degrees
    - **julian_date**: JD for this calculation
    - **input_datetime**: The processed input
    - **location**: The location used for calculation
    """
    observation_time = build_observation_datetime(request.date, request.time)
    location = build_location_from_request(
        request.latitude,
        request.longitude,
        request.elevation
    )
    result = calculate_saturn_position(
        observation_time,
        location,
        locale=get_i18n().locale,
    )
    return SaturnPositionResponse(**result)


@router.post("/uranus-position", response_model=UranusPositionResponse)
@handle_route_errors("calculating Uranus position")
async def get_uranus_position(request: UranusPositionRequest):
    """
    Calculate Uranus's position at a given time and location.

    Returns altitude (angle above horizon), azimuth (compass direction), visibility status,
    and retrograde motion status.

    Uranus Characteristics:
    Uranus is a superior planet (orbit outside Earth's). As a distant outer planet:
    - Phase angle maximum: ~3° (negligible variation in illumination, always ~99.98%+ lit)
    - Always visible when above horizon (no elongation threshold)
    - Exhibits retrograde motion annually (~5 months retrograde per synodic period ~12 months)
    - Appears as a non-varying bright disk; no meaningful phases for observation
    - Difficult to observe without binoculars or telescopes due to distance/faintness

    Parameters:
    - **date**: Date in ISO format (YYYY-MM-DD)
    - **time**: Time in HH:MM:SS format
    - **latitude**: Latitude in degrees (-90 to 90)
    - **longitude**: Longitude in degrees (-180 to 180)
    - **elevation**: Elevation above sea level in meters (optional)

    Returns:
    - **altitude**: Uranus's altitude in degrees (negative = below horizon)
    - **azimuth**: Uranus's azimuth in degrees (0=North, 90=East)
    - **is_visible**: True if Uranus is above horizon
    - **retrograde_status**: Current retrograde motion status (prograde or retrograde)
    - **ra_degrees**: Right ascension in degrees
    - **dec_degrees**: Declination in degrees
    - **julian_date**: JD for this calculation
    - **input_datetime**: The processed input
    - **location**: The location used for calculation
    """
    observation_time = build_observation_datetime(request.date, request.time)
    location = build_location_from_request(
        request.latitude,
        request.longitude,
        request.elevation
    )
    result = calculate_uranus_position(
        observation_time,
        location,
        locale=get_i18n().locale,
    )
    return UranusPositionResponse(**result)


@router.post("/neptune-position", response_model=NeptunePositionResponse)
@handle_route_errors("calculating Neptune position")
async def get_neptune_position(request: NeptunePositionRequest):
    """
    Calculate Neptune's position at a given time and location.

    Returns altitude (angle above horizon), azimuth (compass direction), visibility status,
    and retrograde motion status.

    Neptune Characteristics:
    Neptune is a superior planet (orbit outside Earth's). As the most distant outer planet:
    - Phase angle maximum: ~2° (negligible variation in illumination, always ~99.99%+ lit)
    - Always visible when above horizon (no elongation threshold)
    - Exhibits retrograde motion annually (~5.5 months retrograde per synodic period ~12 months)
    - Appears as a non-varying bright disk; no meaningful phases for observation
    - Extremely difficult to observe without telescopes due to distance/extreme faintness

    Parameters:
    - **date**: Date in ISO format (YYYY-MM-DD)
    - **time**: Time in HH:MM:SS format
    - **latitude**: Latitude in degrees (-90 to 90)
    - **longitude**: Longitude in degrees (-180 to 180)
    - **elevation**: Elevation above sea level in meters (optional)

    Returns:
    - **altitude**: Neptune's altitude in degrees (negative = below horizon)
    - **azimuth**: Neptune's azimuth in degrees (0=North, 90=East)
    - **is_visible**: True if Neptune is above horizon
    - **retrograde_status**: Current retrograde motion status (prograde or retrograde)
    - **ra_degrees**: Right ascension in degrees
    - **dec_degrees**: Declination in degrees
    - **julian_date**: JD for this calculation
    - **input_datetime**: The processed input
    - **location**: The location used for calculation
    """
    observation_time = build_observation_datetime(request.date, request.time)
    location = build_location_from_request(
        request.latitude,
        request.longitude,
        request.elevation
    )
    result = calculate_neptune_position(
        observation_time,
        location,
        locale=get_i18n().locale,
    )
    return NeptunePositionResponse(**result)


@router.post("/moon-phase", response_model=MoonPhaseResponse)
@cache_response(ttl=300)
@handle_route_errors("calculating moon phase")
async def get_moon_phase(request: MoonPhaseRequest):
    """
    Calculate the moon's phase information at a given time and location.

    Returns illumination fraction (0=new, 1=full), phase angle in ecliptic
    longitude (0-180°=waxing, 180-360°=waning), and textual phase name.

    Note: Phase calculation requires both sun and moon positions to determine
    the angular separation and ecliptic longitude difference.

    - **date**: Date in ISO format (YYYY-MM-DD)
    - **time**: Time in HH:MM:SS format
    - **latitude**: Latitude in degrees (-90 to 90)
    - **longitude**: Longitude in degrees (-180 to 180)
    - **elevation**: Elevation above sea level in meters (optional)

    Returns:
    - **illumination**: Fraction illuminated (0.0 to 1.0)
    - **phase_angle**: Angle in ecliptic (0-360°)
    - **phase_name**: E.g., "Waxing Crescent", "Full Moon"
    - **julian_date**: JD for this calculation
    - **input_datetime**: The processed input
    - **location**: The location used for calculation
    """
    observation_time = build_observation_datetime(request.date, request.time)
    location = build_location_from_request(
        request.latitude,
        request.longitude,
        request.elevation
    )
    result = calculate_moon_phase(
        observation_time,
        location,
        locale=get_i18n().locale,
    )
    return MoonPhaseResponse(**result)
