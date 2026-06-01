"""
Pydantic models for API request and response validation
"""
from typing import Optional
from pydantic import BaseModel, Field


class DateTimeRequest(BaseModel):
    """Request model for date/time input"""
    date: str = Field(
        ...,
        description="Date in ISO format (YYYY-MM-DD)",
        examples=["2026-02-01"]
    )
    time: Optional[str] = Field(
        default="00:00:00",
        description="Time in HH:MM:SS format (optional, defaults to midnight)",
        examples=["12:30:45"]
    )


class LocationModel(BaseModel):
    """Model for geographic location"""
    latitude: float = Field(
        ...,
        ge=-90,
        le=90,
        description="Latitude in degrees (-90 to 90, negative=South)"
    )
    longitude: float = Field(
        ...,
        ge=-180,
        le=180,
        description="Longitude in degrees (-180 to 180, negative=West)"
    )
    elevation: float = Field(
        default=0.0,
        description="Elevation above sea level in meters"
    )


class ObservationDateTime(BaseModel):
    """Domain model for a date/time observation point"""
    date: str = Field(
        ...,
        description="Date in ISO format (YYYY-MM-DD)"
    )
    time: str = Field(
        default="00:00:00",
        description="Time in HH:MM:SS format (optional, defaults to midnight)"
    )


class TimeRange(BaseModel):
    """Domain model for a time range with multiple observation frames"""
    start: ObservationDateTime = Field(
        ...,
        description="Start time for observations"
    )
    end: ObservationDateTime = Field(
        ...,
        description="End time for observations"
    )
    frame_count: int = Field(
        ...,
        ge=2,
        le=10000,
        description="Number of observation frames to generate"
    )


class SunPositionRequest(BaseModel):
    """Request model for sun position calculation"""
    date: str = Field(
        ...,
        description="Date in ISO format (YYYY-MM-DD)",
        examples=["2026-02-01"]
    )
    time: str = Field(
        ...,
        description="Time in HH:MM:SS format",
        examples=["12:30:45"]
    )
    latitude: float = Field(
        ...,
        ge=-90,
        le=90,
        description="Latitude in degrees (-90 to 90, negative=South)",
        examples=[40.7128]
    )
    longitude: float = Field(
        ...,
        ge=-180,
        le=180,
        description="Longitude in degrees (-180 to 180, negative=West)",
        examples=[-74.0060]
    )
    elevation: float = Field(
        default=0.0,
        description="Elevation above sea level in meters",
        examples=[10.0]
    )


class SunPositionResponse(BaseModel):
    """Response model for sun position calculation"""
    altitude: float = Field(
        ...,
        description="Sun's altitude in degrees (negative = below horizon)"
    )
    azimuth: float = Field(
        ...,
        description="Sun's azimuth in degrees (0=North, 90=East, 180=South, 270=West)"
    )
    is_visible: bool = Field(
        ...,
        description="Whether the sun is above the horizon"
    )
    julian_date: float = Field(
        ...,
        description="Julian Date (JD) for this calculation"
    )
    input_datetime: str = Field(
        ...,
        description="The input date and time that was processed"
    )
    location: LocationModel = Field(
        ...,
        description="The location used for the calculation"
    )


class MoonPositionRequest(BaseModel):
    """Request model for moon position calculation"""
    date: str = Field(
        ...,
        description="Date in ISO format (YYYY-MM-DD)",
        examples=["2026-02-01"]
    )
    time: str = Field(
        ...,
        description="Time in HH:MM:SS format",
        examples=["12:30:45"]
    )
    latitude: float = Field(
        ...,
        ge=-90,
        le=90,
        description="Latitude in degrees (-90 to 90, negative=South)",
        examples=[40.7128]
    )
    longitude: float = Field(
        ...,
        ge=-180,
        le=180,
        description="Longitude in degrees (-180 to 180, negative=West)",
        examples=[-74.0060]
    )
    elevation: float = Field(
        default=0.0,
        description="Elevation above sea level in meters",
        examples=[10.0]
    )


class MoonPositionResponse(BaseModel):
    """Response model for moon position calculation"""
    altitude: float = Field(
        ...,
        description="Moon's altitude in degrees (negative = below horizon)"
    )
    azimuth: float = Field(
        ...,
        description="Moon's azimuth in degrees (0=North, 90=East, 180=South, 270=West)"
    )
    is_visible: bool = Field(
        ...,
        description="Whether the moon is above the horizon"
    )
    julian_date: float = Field(
        ...,
        description="Julian Date (JD) for this calculation"
    )
    input_datetime: str = Field(
        ...,
        description="The input date and time that was processed"
    )
    location: LocationModel = Field(
        ...,
        description="The location used for the calculation"
    )


class VenusPositionRequest(BaseModel):
    """Request model for Venus position calculation"""
    date: str = Field(
        ...,
        description="Date in ISO format (YYYY-MM-DD)",
        examples=["2026-02-01"]
    )
    time: str = Field(
        ...,
        description="Time in HH:MM:SS format",
        examples=["12:30:45"]
    )
    latitude: float = Field(
        ...,
        ge=-90,
        le=90,
        description="Latitude in degrees (-90 to 90, negative=South)",
        examples=[40.7128]
    )
    longitude: float = Field(
        ...,
        ge=-180,
        le=180,
        description="Longitude in degrees (-180 to 180, negative=West)",
        examples=[-74.0060]
    )
    elevation: float = Field(
        default=0.0,
        description="Elevation above sea level in meters",
        examples=[10.0]
    )


class VenusPositionResponse(BaseModel):
    """Response model for Venus position calculation"""
    altitude: float = Field(
        ...,
        description="Venus's altitude in degrees (negative = below horizon)"
    )
    azimuth: float = Field(
        ...,
        description="Venus's azimuth in degrees (0=North, 90=East, 180=South, 270=West)"
    )
    is_visible: bool = Field(
        ...,
        description="Whether Venus is above the horizon (altitude > 0°)"
    )
    sun_separation: float = Field(
        ...,
        description="Angular separation between Venus and Sun in degrees (elongation)"
    )
    naked_eye_visible: bool = Field(
        ...,
        description=(
            "Whether Venus is naked-eye visible "
            "(above horizon AND sufficiently separated from Sun)"
        )
    )
    illumination: float = Field(
        ...,
        description="Fraction of Venus illuminated (0.0 to 1.0)"
    )
    phase_angle: float = Field(
        ...,
        description="Venus's phase angle in ecliptic longitude (0 to 360 degrees)"
    )
    phase_name: str = Field(
        ...,
        description="Textual name of Venus's phase (New, Crescent, Quarter, Gibbous, Full)"
    )
    julian_date: float = Field(
        ...,
        description="Julian Date (JD) for this calculation"
    )
    input_datetime: str = Field(
        ...,
        description="The input date and time that was processed"
    )
    location: LocationModel = Field(
        ...,
        description="The location used for the calculation"
    )


class MoonPhaseRequest(BaseModel):
    """Request model for moon phase calculation"""
    date: str = Field(
        ...,
        description="Date in ISO format (YYYY-MM-DD)",
        examples=["2026-02-01"]
    )
    time: str = Field(
        ...,
        description="Time in HH:MM:SS format",
        examples=["12:30:45"]
    )
    latitude: float = Field(
        ...,
        ge=-90,
        le=90,
        description="Latitude in degrees (-90 to 90, negative=South)",
        examples=[40.7128]
    )
    longitude: float = Field(
        ...,
        ge=-180,
        le=180,
        description="Longitude in degrees (-180 to 180, negative=West)",
        examples=[-74.0060]
    )
    elevation: float = Field(
        default=0.0,
        description="Elevation above sea level in meters",
        examples=[10.0]
    )


class MoonPhaseResponse(BaseModel):
    """Response model for moon phase calculation"""
    illumination: float = Field(
        ...,
        description="Fraction of moon illuminated (0.0=new moon, 1.0=full moon)",
        ge=0.0,
        le=1.0
    )
    phase_angle: float = Field(
        ...,
        description="Moon's phase angle in ecliptic longitude (0-180=waxing, 180-360=waning)",
        ge=0.0,
        lt=360.0
    )
    phase_name: str = Field(
        ...,
        description="Textual name of the moon phase",
        examples=["Waxing Crescent", "Full Moon", "Waning Gibbous"]
    )
    julian_date: float = Field(
        ...,
        description="Julian Date (JD) for this calculation"
    )
    input_datetime: str = Field(
        ...,
        description="The input date and time that was processed"
    )
    location: LocationModel = Field(
        ...,
        description="The location used for the calculation"
    )


class DayOfWeekResponse(BaseModel):
    """Response model for day of week calculation"""
    julian_date: float = Field(
        ...,
        description="Julian Date (JD) as a floating point number"
    )
    day_of_week: int = Field(
        ...,
        description="Day of week as integer (0=Sunday, 1=Monday, ..., 6=Saturday)"
    )
    day_name: str = Field(
        ...,
        description="Name of the day"
    )
    input_datetime: str = Field(
        ...,
        description="The input date and time that was processed"
    )


# Batch Earth Observations Models
class BatchEarthObservationsRequest(BaseModel):
    """Request model for batch earth observations"""
    start_date: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Start date in ISO format (YYYY-MM-DD)",
        examples=["2026-02-01"]
    )
    start_time: str = Field(
        default="00:00:00",
        pattern=r"^\d{2}:\d{2}:\d{2}$",
        description="Start time in ISO format (HH:MM:SS)",
        examples=["00:00:00"]
    )
    end_date: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="End date in ISO format (YYYY-MM-DD)",
        examples=["2026-02-01"]
    )
    end_time: str = Field(
        default="23:59:59",
        pattern=r"^\d{2}:\d{2}:\d{2}$",
        description="End time in ISO format (HH:MM:SS)",
        examples=["23:59:59"]
    )
    frame_count: int = Field(
        ...,
        ge=2,
        le=10000,
        description="Number of frames to generate (2-10000)",
        examples=[10]
    )
    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Latitude in degrees",
        examples=[40.7128]
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Longitude in degrees",
        examples=[-74.0060]
    )
    elevation: float = Field(
        default=0.0,
        description="Elevation in meters above sea level",
        examples=[0.0]
    )


class CelestialPosition(BaseModel):
    """Celestial object position data"""
    altitude: float = Field(..., description="Altitude in degrees")
    azimuth: float = Field(..., description="Azimuth in degrees")
    is_visible: bool = Field(..., description="Whether object is above horizon")


class MoonPhaseData(BaseModel):
    """Moon phase information"""
    illumination: float = Field(..., ge=0.0, le=1.0, description="Illumination fraction")
    phase_angle: float = Field(..., ge=0.0, lt=360.0, description="Phase angle in degrees")
    phase_name: str = Field(..., description="Name of the moon phase")


class ObservationFrame(BaseModel):
    """Single frame of observations"""
    datetime: str = Field(..., description="ISO datetime of the frame")
    sun: CelestialPosition = Field(..., description="Sun position")
    moon: CelestialPosition = Field(..., description="Moon position")
    moon_phase: MoonPhaseData = Field(..., description="Moon phase information")
    venus: CelestialPosition = Field(..., description="Venus position")


class BatchMetadata(BaseModel):
    """Metadata about the batch observations"""
    location: LocationModel = Field(..., description="Observer location")
    frame_count: int = Field(..., description="Number of frames generated")
    start_datetime: str = Field(..., description="Start datetime")
    end_datetime: str = Field(..., description="End datetime")
    time_span_hours: float = Field(..., description="Time span in hours")


class BatchEarthObservationsResponse(BaseModel):
    """Response model for batch earth observations"""
    frames: list[ObservationFrame] = Field(
        ...,
        description="List of observation frames"
    )
    metadata: BatchMetadata = Field(
        ...,
        description="Metadata about the observations"
    )
