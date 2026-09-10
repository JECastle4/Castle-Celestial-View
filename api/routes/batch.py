"""
API routes for batch celestial observations and streaming.
"""
import json
from fastapi import APIRouter, Query, Request, Body
from fastapi.responses import StreamingResponse
from api.cache import cache_response
from api.i18n import get_i18n
from api.rate_limiter import limiter, LIMIT_EXPENSIVE_BATCH
from api.models import (
    BatchEarthObservationsRequest,
    BatchEarthObservationsResponse,
    LocationModel,
    TimeRange,
)
from api.services.batch_earth_observations import calculate_batch_earth_observations
from .helpers import handle_route_errors, build_time_range, build_location_from_request


router = APIRouter(tags=["batch"])


def _build_time_range_from_batch_request(request: BatchEarthObservationsRequest) -> TimeRange:
    """Build TimeRange object from batch request parameters."""
    return build_time_range(
        request.start_date,
        request.start_time,
        request.end_date,
        request.end_time,
        request.frame_count
    )


def _build_location_from_batch_request(request: BatchEarthObservationsRequest) -> LocationModel:
    """Build LocationModel object from batch request parameters."""
    return build_location_from_request(
        request.latitude,
        request.longitude,
        request.elevation
    )


def _process_batch_frames_from_generator(gen, frame_count: int):
    """Extract frames and metadata from batch observations generator."""
    frames = []
    metadata = None
    for idx, item in enumerate(gen):
        if idx < frame_count:
            frames.append(item)
        else:
            metadata = item
    return frames, metadata


@router.get(
    "/batch-earth-observations-stream",
    tags=["sse"],
    summary="Stream batch celestial observations from Earth (SSE)",
    description="""
    Streams multiple frames of sun, moon, Venus positions and moon/Venus phase from an Earth location using Server-Sent Events (SSE).
    Each frame is sent as a separate SSE event.
    """
)
@limiter.limit(LIMIT_EXPENSIVE_BATCH)  # DDoS: 20 req/min per IP (POST batch limit)
@handle_route_errors("streaming batch observations")
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
    # Capture the locale now (ContextVar is not copied into the sync
    # streaming thread that StreamingResponse uses to iterate the generator)
    locale = get_i18n().locale

    time_range = build_time_range(
        start_date,
        start_time,
        end_date,
        end_time,
        frame_count
    )
    location = build_location_from_request(latitude, longitude, elevation)

    # pylint: disable=duplicate-code
    # Similar SSE streaming pattern in events.py is intentional:
    # Each endpoint has domain-specific generator logic (idx-based vs
    # content-based event type detection) coupled to its service function.
    # Extracting would reduce readability without practical benefit.
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


@router.post(
    "/batch-earth-observations",
    response_model=BatchEarthObservationsResponse,
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
@limiter.limit(LIMIT_EXPENSIVE_BATCH)  # DDoS protection: 20 req/min per IP
@cache_response(ttl=300)
@handle_route_errors("calculating batch observations")
async def get_batch_earth_observations(
    _request: Request,  # For SlowAPI rate limiter
    batch_request: BatchEarthObservationsRequest = Body(...),  # Request model
) -> BatchEarthObservationsResponse:
    """Calculate batch observations of celestial positions from Earth"""
    time_range = _build_time_range_from_batch_request(batch_request)
    location = _build_location_from_batch_request(batch_request)
    gen = calculate_batch_earth_observations(
        time_range=time_range,
        location=location,
        locale=get_i18n().locale
    )
    frames, metadata = _process_batch_frames_from_generator(gen, batch_request.frame_count)
    return BatchEarthObservationsResponse(frames=frames, metadata=metadata)
