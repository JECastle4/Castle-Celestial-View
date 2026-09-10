"""
Helper utilities for route handlers to reduce code duplication.

Provides:
- Exception handling decorators for consistent error responses
- Parameter object builders for common request patterns
"""
import asyncio
import functools
from typing import Callable, TypeVar
from fastapi import HTTPException
from pydantic import ValidationError

from api.models import LocationModel, ObservationDateTime, TimeRange


T = TypeVar("T")


def handle_route_errors(action: str = "processing request"):
    """
    Decorator to handle exceptions in route handlers uniformly.

    Converts:
    - ValidationError → 422 (Unprocessable Entity)
    - ValueError → 400 (Bad Request)
    - Exception → 500 (Internal Server Error)

    Args:
        action: Description of what was being done (e.g., "calculating sun position")
                Used in error messages.

    Example:
        @handle_route_errors("calculating sun position")
        async def get_sun_position(request):
            result = calculate_sun_position(...)
            return SunPositionResponse(**result)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except ValidationError as e:
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid input: {str(e)}"
                ) from e
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid input: {str(e)}"
                ) from e
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error {action}: {str(e)}"
                ) from e

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except ValidationError as e:
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid input: {str(e)}"
                ) from e
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid input: {str(e)}"
                ) from e
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error {action}: {str(e)}"
                ) from e

        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def build_location_from_request(
    latitude: float,
    longitude: float,
    elevation: float = 0.0
) -> LocationModel:
    """
    Build a LocationModel from individual request parameters.

    Args:
        latitude: Latitude in degrees (-90 to 90)
        longitude: Longitude in degrees (-180 to 180)
        elevation: Elevation above sea level in meters (default: 0.0)

    Returns:
        LocationModel instance

    Example:
        location = build_location_from_request(
            latitude=40.7128,
            longitude=-74.0060,
            elevation=10.0
        )
    """
    try:
        return LocationModel(
            latitude=latitude,
            longitude=longitude,
            elevation=elevation
        )
    except ValidationError as e:
        raise ValueError(f"Invalid location: {str(e)}") from e


def build_observation_datetime(
    date: str,
    time: str
) -> ObservationDateTime:
    """
    Build an ObservationDateTime from date and time strings.

    Args:
        date: Date in ISO format (YYYY-MM-DD)
        time: Time in HH:MM:SS format

    Returns:
        ObservationDateTime instance

    Example:
        obs_time = build_observation_datetime("2025-06-21", "12:00:00")
    """
    try:
        return ObservationDateTime(date=date, time=time)
    except ValidationError as e:
        raise ValueError(f"Invalid date/time format: {str(e)}") from e


def build_time_range(
    start_date: str,
    start_time: str,
    end_date: str,
    end_time: str,
    frame_count: int
) -> TimeRange:
    """
    Build a TimeRange from start/end date/time and frame count.

    Args:
        start_date: Start date in ISO format (YYYY-MM-DD)
        start_time: Start time in HH:MM:SS format
        end_date: End date in ISO format (YYYY-MM-DD)
        end_time: End time in HH:MM:SS format
        frame_count: Number of frames to generate

    Returns:
        TimeRange instance

    Example:
        time_range = build_time_range(
            "2025-06-21", "00:00:00",
            "2025-06-22", "00:00:00",
            24
        )
    """
    try:
        # Build the ObservationDateTime objects - these validate format
        # and raise ValueError for format errors
        start = ObservationDateTime(date=start_date, time=start_time)
        end = ObservationDateTime(date=end_date, time=end_time)
    except ValidationError as e:
        # Format validation errors should return 400
        raise ValueError(f"Invalid time range: {str(e)}") from e

    # Build TimeRange - this validates business logic and raises
    # ValidationError for logic errors
    return TimeRange(
        start=start,
        end=end,
        frame_count=frame_count
    )
