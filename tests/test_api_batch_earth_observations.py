"""
Tests for the batch earth observations service
"""
import pytest
from api.services.batch_earth_observations import calculate_batch_earth_observations
from api.models import TimeRange, ObservationDateTime, LocationModel
from pydantic import ValidationError
import json
from fastapi.testclient import TestClient
from fastapi import FastAPI
from api.routes import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_basic_batch_calculation():
    """Test basic batch calculation with multiple frames"""
    time_range = TimeRange(
        start=ObservationDateTime(date="2024-01-01", time="12:00:00"),
        end=ObservationDateTime(date="2024-01-01", time="18:00:00"),
        frame_count=7
    )
    location = LocationModel(
        latitude=40.7128,
        longitude=-74.0060,
        elevation=10.0
    )
    gen = calculate_batch_earth_observations(
        time_range=time_range,
        location=location
    )
    frames = []
    metadata = None
    for item in gen:
        if isinstance(item, dict) and "frame_count" in item:
            metadata = item
        else:
            frames.append(item)
    result = {"frames": frames, "metadata": metadata}
    assert "frames" in result
    assert "metadata" in result
    assert len(result["frames"]) == 7
    # Check first frame
    first_frame = result["frames"][0]
    assert "datetime" in first_frame
    assert "sun" in first_frame
    assert "moon" in first_frame
    assert "moon_phase" in first_frame
    assert first_frame["datetime"] == "2024-01-01T12:00:00Z"
    # Check last frame
    last_frame = result["frames"][-1]
    assert last_frame["datetime"] == "2024-01-01T18:00:00Z"
    # Check sun position structure
    assert "altitude" in first_frame["sun"]
    assert "azimuth" in first_frame["sun"]
    assert "is_visible" in first_frame["sun"]
    # Check moon position structure
    assert "altitude" in first_frame["moon"]
    assert "azimuth" in first_frame["moon"]
    assert "is_visible" in first_frame["moon"]
    # Check moon phase structure
    assert "illumination" in first_frame["moon_phase"]
    assert "phase_angle" in first_frame["moon_phase"]
    assert "phase_name" in first_frame["moon_phase"]
    # Check Venus position structure
    assert "venus" in first_frame
    assert "altitude" in first_frame["venus"]
    assert "azimuth" in first_frame["venus"]
    assert "is_visible" in first_frame["venus"]
    # Check Venus phase structure
    assert "venus_phase" in first_frame
    assert "illumination" in first_frame["venus_phase"]
    assert "phase_angle" in first_frame["venus_phase"]
    assert "phase_name" in first_frame["venus_phase"]
    assert "naked_eye_visible" in first_frame["venus_phase"]
    assert first_frame["datetime"] == "2024-01-01T12:00:00Z"
    # Check metadata
    assert result["metadata"]["frame_count"] == 7
    assert result["metadata"]["start_datetime"] == "2024-01-01T12:00:00Z"
    assert result["metadata"]["end_datetime"] == "2024-01-01T18:00:00Z"
    assert result["metadata"]["time_span_hours"] == 6.0
    assert result["metadata"]["location"]["latitude"] == 40.7128
    assert result["metadata"]["location"]["longitude"] == -74.0060
    assert result["metadata"]["location"]["elevation"] == 10.0


def test_frame_count_validation_too_low():
    """Test that frame_count < 2 raises ValidationError"""
    with pytest.raises(ValidationError, match="greater_than_equal"):
        time_range = TimeRange(
            start=ObservationDateTime(date="2024-01-01", time="12:00:00"),
            end=ObservationDateTime(date="2024-01-01", time="13:00:00"),
            frame_count=1
        )


def test_end_before_start_validation():
    """Test that end_datetime must be after start_datetime"""
    with pytest.raises(ValueError, match="end_datetime must be after start_datetime"):
        time_range = TimeRange(
            start=ObservationDateTime(date="2024-01-02", time="12:00:00"),
            end=ObservationDateTime(date="2024-01-01", time="12:00:00"),
            frame_count=2
        )
        location = LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        gen = calculate_batch_earth_observations(time_range=time_range, location=location)
        list(gen)


def test_equal_start_end_validation():
    """Test that start and end times cannot be equal"""
    with pytest.raises(ValueError, match="end_datetime must be after start_datetime"):
        time_range = TimeRange(
            start=ObservationDateTime(date="2024-01-01", time="12:00:00"),
            end=ObservationDateTime(date="2024-01-01", time="12:00:00"),
            frame_count=2
        )
        location = LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        gen = calculate_batch_earth_observations(time_range=time_range, location=location)
        list(gen)


def test_coordinate_validation_latitude():
    """Test that invalid latitude is caught during object construction"""
    with pytest.raises(ValidationError, match="less_than_equal|greater_than_equal"):
        location = LocationModel(latitude=91.0, longitude=0.0, elevation=0.0)


def test_coordinate_validation_longitude():
    """Test that invalid longitude is caught during object construction"""
    with pytest.raises(ValidationError, match="less_than_equal|greater_than_equal"):
        location = LocationModel(latitude=0.0, longitude=181.0, elevation=0.0)


def test_time_span_calculation():
    """Test that time span is calculated correctly"""
    time_range = TimeRange(
        start=ObservationDateTime(date="2024-01-01", time="00:00:00"),
        end=ObservationDateTime(date="2024-01-02", time="00:00:00"),
        frame_count=5
    )
    location = LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
    gen = calculate_batch_earth_observations(time_range=time_range, location=location)
    frames = []
    metadata = None
    for item in gen:
        if isinstance(item, dict) and "frame_count" in item:
            metadata = item
        else:
            frames.append(item)
    result = {"frames": frames, "metadata": metadata}
    assert result["metadata"]["time_span_hours"] == 24.0


def test_default_time_values():
    """Test that default start_time is 00:00:00 and end_time is 23:59:59"""
    # This test verifies behavior when defaults might be used by the API
    time_range = TimeRange(
        start=ObservationDateTime(date="2024-01-01", time="00:00:00"),
        end=ObservationDateTime(date="2024-01-01", time="23:59:59"),
        frame_count=2
    )
    location = LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
    gen = calculate_batch_earth_observations(time_range=time_range, location=location)
    frames = []
    metadata = None
    for item in gen:
        if isinstance(item, dict) and "frame_count" in item:
            metadata = item
        else:
            frames.append(item)
    result = {"frames": frames, "metadata": metadata}
    assert result["frames"][0]["datetime"] == "2024-01-01T00:00:00Z"
    assert result["frames"][1]["datetime"] == "2024-01-01T23:59:59Z"
    assert abs(result["metadata"]["time_span_hours"] - 23.9997) < 0.001


def test_large_frame_count():
    """Test with larger frame count"""
    time_range = TimeRange(
        start=ObservationDateTime(date="2024-01-01", time="00:00:00"),
        end=ObservationDateTime(date="2024-01-01", time="01:00:00"),
        frame_count=61
    )
    location = LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
    gen = calculate_batch_earth_observations(time_range=time_range, location=location)
    frames = []
    metadata = None
    for item in gen:
        if isinstance(item, dict) and "frame_count" in item:
            metadata = item
        else:
            frames.append(item)
    result = {"frames": frames, "metadata": metadata}
    assert len(result["frames"]) == 61
    assert result["metadata"]["frame_count"] == 61


def test_multi_day_span():
    """Test batch calculation spanning multiple days"""
    time_range = TimeRange(
        start=ObservationDateTime(date="2024-01-01", time="12:00:00"),
        end=ObservationDateTime(date="2024-01-03", time="12:00:00"),
        frame_count=3
    )
    location = LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
    gen = calculate_batch_earth_observations(time_range=time_range, location=location)
    frames = []
    metadata = None
    for item in gen:
        if isinstance(item, dict) and "frame_count" in item:
            metadata = item
        else:
            frames.append(item)
    result = {"frames": frames, "metadata": metadata}
    assert len(result["frames"]) == 3
    assert result["frames"][0]["datetime"] == "2024-01-01T12:00:00Z"
    assert result["frames"][1]["datetime"] == "2024-01-02T12:00:00Z"
    assert result["frames"][2]["datetime"] == "2024-01-03T12:00:00Z"
    assert result["metadata"]["time_span_hours"] == 48.0

def test_north_pole():
    """Test calculation at North Pole"""
    time_range = TimeRange(
        start=ObservationDateTime(date="2024-06-21", time="12:00:00"),
        end=ObservationDateTime(date="2024-06-21", time="18:00:00"),
        frame_count=3
    )
    location = LocationModel(latitude=90.0, longitude=0.0, elevation=0.0)
    gen = calculate_batch_earth_observations(time_range=time_range, location=location)
    frames = []
    metadata = None
    for item in gen:
        if isinstance(item, dict) and "frame_count" in item:
            metadata = item
        else:
            frames.append(item)
    result = {"frames": frames, "metadata": metadata}
    assert len(result["frames"]) == 3
    # Sun should be visible at North Pole during summer
    assert result["frames"][0]["sun"]["is_visible"]


def test_south_pole():
    """Test calculation at South Pole"""
    time_range = TimeRange(
        start=ObservationDateTime(date="2024-12-21", time="12:00:00"),
        end=ObservationDateTime(date="2024-12-21", time="18:00:00"),
        frame_count=3
    )
    location = LocationModel(latitude=-90.0, longitude=0.0, elevation=0.0)
    gen = calculate_batch_earth_observations(time_range=time_range, location=location)
    frames = []
    metadata = None
    for item in gen:
        if isinstance(item, dict) and "frame_count" in item:
            metadata = item
        else:
            frames.append(item)
    result = {"frames": frames, "metadata": metadata}
    assert len(result["frames"]) == 3
    # Sun should be visible at South Pole during southern summer


def test_equator():
    """Test calculation at equator"""
    time_range = TimeRange(
        start=ObservationDateTime(date="2024-03-20", time="06:00:00"),
        end=ObservationDateTime(date="2024-03-20", time="18:00:00"),
        frame_count=5
    )
    location = LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
    gen = calculate_batch_earth_observations(time_range=time_range, location=location)
    frames = []
    metadata = None
    for item in gen:
        if isinstance(item, dict) and "frame_count" in item:
            metadata = item
        else:
            frames.append(item)
    result = {"frames": frames, "metadata": metadata}
    assert len(result["frames"]) == 5


def test_prime_meridian_and_dateline():
    """Test calculations at Prime Meridian and International Date Line"""
    # Prime Meridian
    time_range1 = TimeRange(
        start=ObservationDateTime(date="2024-01-01", time="12:00:00"),
        end=ObservationDateTime(date="2024-01-01", time="13:00:00"),
        frame_count=2
    )
    location1 = LocationModel(latitude=51.4778, longitude=0.0, elevation=0.0)
    gen1 = calculate_batch_earth_observations(time_range=time_range1, location=location1)
    frames1 = []
    metadata1 = None
    for item in gen1:
        if isinstance(item, dict) and "frame_count" in item:
            metadata1 = item
        else:
            frames1.append(item)
    result1 = {"frames": frames1, "metadata": metadata1}
    assert len(result1["frames"]) == 2
    # International Date Line (180 degrees)
    time_range2 = TimeRange(
        start=ObservationDateTime(date="2024-01-01", time="12:00:00"),
        end=ObservationDateTime(date="2024-01-01", time="13:00:00"),
        frame_count=2
    )
    location2 = LocationModel(latitude=0.0, longitude=180.0, elevation=0.0)
    gen2 = calculate_batch_earth_observations(time_range=time_range2, location=location2)
    frames2 = []
    metadata2 = None
    for item in gen2:
        if isinstance(item, dict) and "frame_count" in item:
            metadata2 = item
        else:
            frames2.append(item)
    result2 = {"frames": frames2, "metadata": metadata2}
    assert len(result2["frames"]) == 2


def test_moon_phase_varies_over_month():
    """Test that moon phase changes over a month"""
    time_range = TimeRange(
        start=ObservationDateTime(date="2024-01-01", time="12:00:00"),
        end=ObservationDateTime(date="2024-01-29", time="12:00:00"),
        frame_count=5
    )
    location = LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
    gen = calculate_batch_earth_observations(time_range=time_range, location=location)
    frames = []
    metadata = None
    for item in gen:
        if isinstance(item, dict) and "frame_count" in item:
            metadata = item
        else:
            frames.append(item)
    result = {"frames": frames, "metadata": metadata}
    # Moon phase should change significantly over a month
    phases = [frame["moon_phase"]["phase_angle"] for frame in result["frames"]]
    assert len(set(phases)) > 1  # Phases should be different


def test_sun_moon_visibility_changes():
    """Test that sun and moon visibility can change over time"""
    time_range = TimeRange(
        start=ObservationDateTime(date="2024-01-01", time="00:00:00"),
        end=ObservationDateTime(date="2024-01-02", time="00:00:00"),
        frame_count=25
    )
    location = LocationModel(latitude=40.0, longitude=0.0, elevation=0.0)
    gen = calculate_batch_earth_observations(time_range=time_range, location=location)
    frames = []
    metadata = None
    for item in gen:
        if isinstance(item, dict) and "frame_count" in item:
            metadata = item
        else:
            frames.append(item)
    result = {"frames": frames, "metadata": metadata}
    sun_visibility = [frame["sun"]["is_visible"] for frame in result["frames"]]
    # Sun should rise and set during 24 hours at mid-latitudes
    assert True in sun_visibility
    assert False in sun_visibility


def test_sse_batch_earth_observations_stream():
    """Test SSE streaming endpoint for batch earth observations"""
    payload = {
        "start_date": "2024-01-01",
        "start_time": "12:00:00",
        "end_date": "2024-01-01",
        "end_time": "18:00:00",
        "frame_count": 3,
        "latitude": 40.7128,
        "longitude": -74.0060,
        "elevation": 10.0
    }
    response = client.get(
        "/batch-earth-observations-stream",
        params=payload,
        headers={"Accept": "text/event-stream"}
    )
    assert response.status_code == 200
    # Parse SSE events
    events = response.text.strip().split("\n\n")
    frame_events = [e for e in events if e.startswith("event: frame")]
    metadata_events = [e for e in events if e.startswith("event: metadata")]
    assert len(frame_events) == 3
    assert len(metadata_events) == 1
    # Validate frame event structure
    for idx, event in enumerate(frame_events):
        assert f"id: {idx}" in event
        assert "data: " in event
        data = json.loads(event.split("data: ", 1)[1])
        assert "datetime" in data
        assert "sun" in data
        assert "moon" in data
        assert "moon_phase" in data
    # Validate metadata event structure
    metadata_data = json.loads(metadata_events[0].split("data: ", 1)[1])
    assert metadata_data["frame_count"] == 3
    assert metadata_data["start_datetime"] == "2024-01-01T12:00:00Z"
    assert metadata_data["end_datetime"] == "2024-01-01T18:00:00Z"
    assert metadata_data["location"]["latitude"] == 40.7128
    assert metadata_data["location"]["longitude"] == -74.0060
    assert metadata_data["location"]["elevation"] == 10.0
