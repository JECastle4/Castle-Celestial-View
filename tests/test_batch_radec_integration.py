"""Tests for batch earth observations endpoint with RA/Dec coordinates."""

import pytest
from api.services.batch_earth_observations import calculate_batch_earth_observations
from api.models import TimeRange, ObservationDateTime, LocationModel


class TestBatchEarthObservationsRADec:
    """Test batch endpoint returns RA/Dec coordinates"""
    
    def test_batch_returns_ra_dec_for_all_bodies(self):
        """Test that batch endpoint returns RA/Dec for all celestial bodies"""
        time_range = TimeRange(
            start=ObservationDateTime(date="2026-02-01", time="00:00:00"),
            end=ObservationDateTime(date="2026-02-01", time="12:00:00"),
            frame_count=5
        )
        location = LocationModel(latitude=40.7128, longitude=-74.0060)
        
        frames = list(calculate_batch_earth_observations(time_range, location))
        
        # Frames are yielded first, metadata is yielded last
        # Filter to get just the frame dicts (which have "datetime" field)
        frame_list = [f for f in frames if isinstance(f, dict) and "datetime" in f]
        
        assert len(frame_list) >= 2
        
        # Check first frame has RA/Dec for all bodies
        frame = frame_list[0]
        assert "sun" in frame
        assert "moon" in frame
        assert "venus" in frame
        
        # Each body should have RA/Dec
        assert "ra_degrees" in frame["sun"]
        assert "dec_degrees" in frame["sun"]
        assert "ra_degrees" in frame["moon"]
        assert "dec_degrees" in frame["moon"]
        assert "ra_degrees" in frame["venus"]
        assert "dec_degrees" in frame["venus"]
    
    def test_batch_ra_dec_ranges_all_frames(self):
        """Test that RA/Dec are in valid ranges for all frames"""
        time_range = TimeRange(
            start=ObservationDateTime(date="2026-02-01", time="00:00:00"),
            end=ObservationDateTime(date="2026-02-01", time="12:00:00"),
            frame_count=5
        )
        location = LocationModel(latitude=0.0, longitude=0.0)
        
        frames = list(calculate_batch_earth_observations(time_range, location))
        frame_list = [f for f in frames if isinstance(f, dict) and "datetime" in f]
        
        for frame in frame_list:
            # Check sun
            assert 0 <= frame["sun"]["ra_degrees"] <= 360
            assert -90 <= frame["sun"]["dec_degrees"] <= 90
            
            # Check moon
            assert 0 <= frame["moon"]["ra_degrees"] <= 360
            assert -90 <= frame["moon"]["dec_degrees"] <= 90
            
            # Check venus
            assert 0 <= frame["venus"]["ra_degrees"] <= 360
            assert -90 <= frame["venus"]["dec_degrees"] <= 90
    
    def test_batch_ra_dec_changes_over_time(self):
        """Test that RA/Dec change as expected over time"""
        time_range = TimeRange(
            start=ObservationDateTime(date="2026-02-01", time="00:00:00"),
            end=ObservationDateTime(date="2026-02-01", time="12:00:00"),
            frame_count=5
        )
        location = LocationModel(latitude=0.0, longitude=0.0)
        
        frames = list(calculate_batch_earth_observations(time_range, location))
        frame_list = [f for f in frames if isinstance(f, dict) and "datetime" in f]
        
        # Sun should move about 1 degree per day, so in 12 hours ~0.5 degrees
        sun_ra_0 = frame_list[0]["sun"]["ra_degrees"]
        sun_ra_last = frame_list[-1]["sun"]["ra_degrees"]
        sun_ra_diff = abs(sun_ra_last - sun_ra_0)
        
        # Handle RA wraparound
        if sun_ra_diff > 180:
            sun_ra_diff = 360 - sun_ra_diff
        
        # Sun should move (but not too much in 12 hours)
        assert sun_ra_diff < 1  # Less than 1 degree in 12 hours
    
    def test_batch_frame_count_respected(self):
        """Test that batch returns requested frame count"""
        for frame_count in [2, 5, 10]:
            time_range = TimeRange(
                start=ObservationDateTime(date="2026-02-01", time="00:00:00"),
                end=ObservationDateTime(date="2026-02-01", time="12:00:00"),
                frame_count=frame_count
            )
            location = LocationModel(latitude=40.7128, longitude=-74.0060)
            
            frames = list(calculate_batch_earth_observations(time_range, location))
            frame_list = [f for f in frames if isinstance(f, dict) and "datetime" in f]
            
            assert len(frame_list) == frame_count
    
    def test_batch_datetimes_are_ordered(self):
        """Test that batch frames are in chronological order"""
        time_range = TimeRange(
            start=ObservationDateTime(date="2026-02-01", time="00:00:00"),
            end=ObservationDateTime(date="2026-02-01", time="12:00:00"),
            frame_count=5
        )
        location = LocationModel(latitude=0.0, longitude=0.0)
        
        frames = list(calculate_batch_earth_observations(time_range, location))
        frame_list = [f for f in frames if isinstance(f, dict) and "datetime" in f]
        
        datetimes = [f["datetime"] for f in frame_list]
        
        # Verify they're in order
        for i in range(len(datetimes) - 1):
            assert datetimes[i] <= datetimes[i + 1]
    
    def test_batch_metadata_included(self):
        """Test that batch response includes metadata"""
        time_range = TimeRange(
            start=ObservationDateTime(date="2026-02-01", time="00:00:00"),
            end=ObservationDateTime(date="2026-02-01", time="12:00:00"),
            frame_count=3
        )
        location = LocationModel(latitude=40.7128, longitude=-74.0060, elevation=100.0)
        
        frames = list(calculate_batch_earth_observations(time_range, location))
        
        # Last element should be metadata
        metadata = frames[-1]
        
        assert "location" in metadata
        assert metadata["location"]["latitude"] == 40.7128
        assert metadata["location"]["longitude"] == -74.0060
        assert metadata["location"]["elevation"] == 100.0
        assert metadata["frame_count"] == 3
    
    def test_batch_error_end_before_start(self):
        """Test that error is raised if end time is before start time"""
        time_range = TimeRange(
            start=ObservationDateTime(date="2026-02-02", time="00:00:00"),
            end=ObservationDateTime(date="2026-02-01", time="12:00:00"),
            frame_count=3
        )
        location = LocationModel(latitude=0.0, longitude=0.0)
        
        with pytest.raises(ValueError, match="endTimeAfterStart|end.*after.*start"):
            list(calculate_batch_earth_observations(time_range, location))
    
    def test_batch_error_invalid_frame_count(self):
        """Test that error is raised for invalid frame count"""
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            time_range = TimeRange(
                start=ObservationDateTime(date="2026-02-01", time="00:00:00"),
                end=ObservationDateTime(date="2026-02-01", time="12:00:00"),
                frame_count=1  # Too small, should raise ValidationError
            )


class TestBatchEarthObservationsHttp:
    """Test batch endpoint via HTTP"""
    
    def test_batch_http_returns_ra_dec(self):
        """Test that HTTP endpoint returns RA/Dec via FastAPI"""
        from fastapi.testclient import TestClient
        from api.main import app
        
        client = TestClient(app)
        
        response = client.post(
            "/api/v1/batch-earth-observations",
            json={
                "start_date": "2026-02-01",
                "start_time": "12:00:00",
                "end_date": "2026-02-01",
                "end_time": "18:00:00",
                "frame_count": 2,
                "latitude": 40.7128,
                "longitude": -74.0060,
                "elevation": 0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "frames" in data
        assert len(data["frames"]) == 2
        
        frame = data["frames"][0]
        
        # Verify RA/Dec are in response
        assert "ra_degrees" in frame["sun"]
        assert "dec_degrees" in frame["sun"]
        assert "ra_degrees" in frame["moon"]
        assert "dec_degrees" in frame["moon"]
        assert "ra_degrees" in frame["venus"]
        assert "dec_degrees" in frame["venus"]
        
        # Verify ranges
        assert 0 <= frame["sun"]["ra_degrees"] <= 360
        assert -90 <= frame["sun"]["dec_degrees"] <= 90
