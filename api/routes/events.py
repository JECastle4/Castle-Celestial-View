"""
API routes for eclipse and astronomical event predictions.
"""
import json
from typing import Optional

from fastapi import APIRouter, Body, Query, Request
from fastapi.responses import StreamingResponse

from api.cache import cache_response
from api.models import (
    AstronomicalEventsRequest,
    AstronomicalEventsResponse,
    EclipseContactTimesRequest,
    EclipseContactTimesResponse,
)
from api.rate_limiter import (
    LIMIT_CONTACT_TIMES,
    LIMIT_EXPENSIVE_EVENTS,
    LIMIT_STREAM_EVENTS,
    limiter,
)
from api.services.astronomical_events import (
    get_astronomical_events,
    get_contact_times_for_event,
    stream_astronomical_events,
    validate_date_range,
)

from .helpers import handle_route_errors


router = APIRouter(tags=["astronomical-events"])


@router.post(
    "/astronomical-events",
    response_model=AstronomicalEventsResponse,
    summary="Find new/full moons and eclipses in a date range",
    description="""
    Finds all new and full moons within a date range and classifies each as an
    eclipse (TOTAL, PARTIAL, ANNULAR, or PENUMBRAL) where applicable, using the
    Moon's ecliptic latitude at conjunction/opposition as a fast pre-filter and
    precise shadow-cone geometry (refined to the instant of greatest eclipse) for
    classification.

    Geocentric-only (not observer-specific). Eclipse contact times, when computed,
    describe when the eclipse begins/ends as seen from somewhere on Earth (solar)
    or the penumbral/umbral shadow boundary crossings (lunar) - not times for a
    specific observer location.

    - **start_date** / **end_date**: Date range (YYYY-MM-DD), inclusive
    - **page** / **page_size**: Pagination controls
    - **include_contact_times**: Whether to compute eclipse contact times
    - **event_types**: Optional filter - 'new_moon', 'full_moon', or omit for both
    """
)
@limiter.limit(LIMIT_EXPENSIVE_EVENTS)  # DDoS protection: 15 req/min per IP
@cache_response(ttl=600)
@handle_route_errors("calculating astronomical events")
def get_astronomical_events_route(
    request: Request,  # pylint: disable=unused-argument
    events_request: AstronomicalEventsRequest = Body(...),  # For caching and validation
    lang: Optional[str] = Query(None)
) -> AstronomicalEventsResponse:
    """Find new/full moons and classify eclipses within a date range."""
    result = get_astronomical_events(
        start_date_str=events_request.start_date,
        end_date_str=events_request.end_date,
        page=events_request.page,
        page_size=events_request.page_size,
        include_contact_times=events_request.include_contact_times,
        event_types=events_request.event_types,
        locale=lang,
    )
    return AstronomicalEventsResponse(**result)


@router.get(
    "/astronomical-events-stream",
    tags=["sse"],
    summary="Stream new/full moons and eclipses in a date range (SSE)",
    description="""
    Streams the same search as POST /astronomical-events using Server-Sent Events
    (SSE), so a client can show live progress instead of waiting for the entire
    date range to be processed. Results are paginated as in the POST endpoint;
    each page is sent as a separate 'page' SSE event, followed by a final
    'metadata' event with pagination totals.

    - **start_date** / **end_date**: Date range (YYYY-MM-DD), inclusive
    - **page_size**: Number of events per page (1-100)
    - **include_contact_times**: Whether to compute eclipse contact times
    - **event_types**: Optional filter - 'new_moon', 'full_moon', repeat param for both
    """
)
@limiter.limit(LIMIT_STREAM_EVENTS)  # DDoS protection: 10 req/min per IP
@handle_route_errors("streaming astronomical events")
def stream_astronomical_events_route(
    request: Request,  # pylint: disable=unused-argument
    start_date: str = Query(...),
    end_date: str = Query(...),
    page_size: int = Query(10, ge=1, le=100),
    include_contact_times: bool = Query(False),
    event_types: Optional[list[str]] = Query(None),
    lang: Optional[str] = Query(None),
):
    """Stream new/full moon events with eclipse classification via SSE."""
    # Validate input the same way as the POST endpoint (raises
    # ValidationError -> 422), plus the date-range-size check (raises
    # ValueError -> 400), before the stream starts - so bad requests fail
    # fast instead of erroring out mid-stream.
    AstronomicalEventsRequest(
        start_date=start_date,
        end_date=end_date,
        page_size=page_size,
        include_contact_times=include_contact_times,
        event_types=event_types,
    )
    validate_date_range(start_date, end_date)

    # pylint: disable=duplicate-code
    # Similar SSE streaming pattern in batch.py is intentional:
    # Each endpoint has domain-specific generator logic (idx-based vs
    # content-based event type detection) coupled to its service function.
    # Extracting would reduce readability without practical benefit.
    def event_generator():
        gen = stream_astronomical_events(
            start_date_str=start_date,
            end_date_str=end_date,
            page_size=page_size,
            include_contact_times=include_contact_times,
            event_types=event_types,
            locale=lang,
        )
        for item in gen:
            if 'events' in item:
                yield f"event: page\ndata: {json.dumps(item)}\n\n"
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
    "/astronomical-events/contact-times",
    response_model=EclipseContactTimesResponse,
    summary="Get eclipse contact times for a specific event",
    description="""
    Fetches the contact times (penumbral/umbral or global shadow boundary crossings)
    for a specific eclipse event. This is a separate endpoint to support lazy-loading:
    initial search returns events without contact times (fast), then individual events
    can fetch their contact times on-demand (when user expands the card).

    Response is cached for performance; repeat queries for the same event_date/is_lunar
    are served from cache.

    - **event_date**: ISO datetime from AstronomicalEvent.date (YYYY-MM-DD HH:MM:SS.sss)
    - **is_lunar**: true for lunar/full-moon events, false for solar/new-moon events
    """
)
@limiter.limit(LIMIT_CONTACT_TIMES)  # DDoS protection: 30 req/min per IP
@cache_response(ttl=600)
@handle_route_errors("calculating contact times")
def get_contact_times_route(
    request: Request,  # pylint: disable=unused-argument
    contact_times_request: EclipseContactTimesRequest = Body(...),  # For caching and validation
    _lang: Optional[str] = Query(None)
) -> EclipseContactTimesResponse:
    """Fetch eclipse contact times for a specific event."""
    contact_times = get_contact_times_for_event(
        event_date_iso=contact_times_request.event_date,
        is_lunar=contact_times_request.is_lunar,
    )
    return EclipseContactTimesResponse(contact_times=contact_times)
