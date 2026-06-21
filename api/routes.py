"""
API routes for astronomy calculations
"""
import json
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
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
    MoonPhaseRequest,
    MoonPhaseResponse,
    BatchEarthObservationsRequest,
    BatchEarthObservationsResponse,
    ObservationDateTime,
    LocationModel,
    TimeRange,
)
from api.services.dates import calculate_day_of_week
from api.services.sun import calculate_sun_position
from api.services.moon import calculate_moon_position
from api.services.venus import calculate_venus_position
from api.services.mercury import calculate_mercury_position
from api.services.mars import calculate_mars_position
from api.services.moon_phase import calculate_moon_phase
from api.services.batch_earth_observations import calculate_batch_earth_observations


router = APIRouter()


@router.get(
    "/batch-earth-observations-stream",
    tags=["batch", "sse"],
    summary="Stream batch celestial observations from Earth (SSE)",
    description="""
    Streams multiple frames of sun, moon, Venus positions and moon/Venus phase from an Earth location using Server-Sent Events (SSE).
    Each frame is sent as a separate SSE event.
    """
)
async def stream_batch_earth_observations(
    start_date: str = Query(...),
    start_time: str = Query(...),
    end_date: str = Query(...),
    end_time: str = Query(...),
    frame_count: int = Query(..., ge=2, le=10000),
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0),
    elevation: float = Query(0.0)
):
    """Stream batch celestial observations including sun, moon, and Venus
    data via Server-Sent Events."""
    try:
        # Capture the locale now (ContextVar is not copied into the sync
        # streaming thread that StreamingResponse uses to iterate the generator)
        locale = get_i18n().locale

        time_range = TimeRange(
            start=ObservationDateTime(date=start_date, time=start_time),
            end=ObservationDateTime(date=end_date, time=end_time),
            frame_count=frame_count
        )
        location = LocationModel(
            latitude=latitude,
            longitude=longitude,
            elevation=elevation
        )

        def event_generator():
            gen = calculate_batch_earth_observations(
                time_range=time_range,
                location=location,
                locale=locale
            )
            for idx, item in enumerate(gen):
                if idx < frame_count:
                    yield f"event: frame\nid: {idx}\ndata: {json.dumps(item)}\n\n"
                else:
                    yield f"event: metadata\ndata: {json.dumps(item)}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",  # Disable buffering in nginx / proxy layers
            },
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid input: {str(e)}"
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error streaming batch observations: {str(e)}"
        ) from e


@router.post("/day-of-week", response_model=DayOfWeekResponse)
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
    try:
        result = calculate_day_of_week(request.date, request.time)
        return DayOfWeekResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date/time format: {str(e)}"
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating day of week: {str(e)}"
        ) from e


@router.post("/sun-position", response_model=SunPositionResponse)
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
    try:
        observation_time = ObservationDateTime(date=request.date, time=request.time)
        location = LocationModel(
            latitude=request.latitude,
            longitude=request.longitude,
            elevation=request.elevation
        )
        result = calculate_sun_position(observation_time, location)
        return SunPositionResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid input: {str(e)}"
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating sun position: {str(e)}"
        ) from e


@router.post("/moon-position", response_model=MoonPositionResponse)
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
    try:
        observation_time = ObservationDateTime(date=request.date, time=request.time)
        location = LocationModel(
            latitude=request.latitude,
            longitude=request.longitude,
            elevation=request.elevation
        )
        result = calculate_moon_position(observation_time, location)
        return MoonPositionResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid input: {str(e)}"
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating moon position: {str(e)}"
        ) from e


@router.post("/venus-position", response_model=VenusPositionResponse)
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
    try:
        observation_time = ObservationDateTime(date=request.date, time=request.time)
        location = LocationModel(
            latitude=request.latitude,
            longitude=request.longitude,
            elevation=request.elevation
        )
        result = calculate_venus_position(
            observation_time,
            location,
            locale=get_i18n().locale,
        )
        return VenusPositionResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid input: {str(e)}"
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating Venus position: {str(e)}"
        ) from e


@router.post("/mercury-position", response_model=MercuryPositionResponse)
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
    try:
        observation_time = ObservationDateTime(date=request.date, time=request.time)
        location = LocationModel(
            latitude=request.latitude,
            longitude=request.longitude,
            elevation=request.elevation
        )
        result = calculate_mercury_position(
            observation_time,
            location,
            locale=get_i18n().locale,
        )
        return MercuryPositionResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid input: {str(e)}"
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating Mercury position: {str(e)}"
        ) from e


@router.post("/mars-position", response_model=MarsPositionResponse)
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
    try:
        observation_time = ObservationDateTime(date=request.date, time=request.time)
        location = LocationModel(
            latitude=request.latitude,
            longitude=request.longitude,
            elevation=request.elevation
        )
        result = calculate_mars_position(
            observation_time,
            location,
            locale=get_i18n().locale,
        )
        return MarsPositionResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid input: {str(e)}"
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating Mars position: {str(e)}"
        ) from e


@router.post("/moon-phase", response_model=MoonPhaseResponse)
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
    try:
        observation_time = ObservationDateTime(date=request.date, time=request.time)
        location = LocationModel(
            latitude=request.latitude,
            longitude=request.longitude,
            elevation=request.elevation
        )
        result = calculate_moon_phase(
            observation_time,
            location,
            locale=get_i18n().locale,
        )
        return MoonPhaseResponse(**result)

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid input: {str(e)}"
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating moon phase: {str(e)}"
        ) from e


@router.post(
    "/batch-earth-observations",
    response_model=BatchEarthObservationsResponse,
    tags=["batch"],
    summary="Get batch celestial observations from Earth",
    description="""
    Calculate multiple frames of sun, moon, and Venus positions with moon and Venus phase from an Earth location.

    This endpoint generates a series of observations between start and end times,
    perfect for animations or time-series visualizations. Each frame contains:
    - Sun position (altitude, azimuth, visibility)
    - Moon position (altitude, azimuth, visibility)
    - Moon phase (illumination, angle, name)
    - Venus position (altitude, azimuth, visibility)
    - Venus phase (illumination, angle, name, naked-eye visibility)

    **Note:** For large frame counts, this may take several seconds to compute.
    Current implementation calls position services for each frame.
    """
)
async def get_batch_earth_observations(request: BatchEarthObservationsRequest):
    """Calculate batch observations of celestial positions from Earth"""
    try:
        time_range = TimeRange(
            start=ObservationDateTime(date=request.start_date, time=request.start_time),
            end=ObservationDateTime(date=request.end_date, time=request.end_time),
            frame_count=request.frame_count
        )
        location = LocationModel(
            latitude=request.latitude,
            longitude=request.longitude,
            elevation=request.elevation
        )
        gen = calculate_batch_earth_observations(
            time_range=time_range,
            location=location,
            locale=get_i18n().locale
        )
        frames = []
        metadata = None
        for idx, item in enumerate(gen):
            if idx < request.frame_count:
                frames.append(item)
            else:
                metadata = item
        return BatchEarthObservationsResponse(frames=frames, metadata=metadata)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid input: {str(e)}"
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating batch observations: {str(e)}"
        ) from e
