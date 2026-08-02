"""
Unit tests for API validation fixes
Tests for date/time format validation and business logic validation
"""

import pytest
from pydantic import ValidationError
from api.models import ObservationDateTime, TimeRange, LocationModel


class TestDateFormatValidation:
    """Test date format validation"""
    
    def test_valid_date_format(self):
        """Valid ISO date format should pass"""
        dt = ObservationDateTime(date="2026-01-15", time="12:30:45")
        assert dt.date == "2026-01-15"
    
    def test_invalid_date_format_american(self):
        """American date format (MM-DD-YYYY) should fail"""
        with pytest.raises(ValidationError) as exc_info:
            ObservationDateTime(date="01-15-2026", time="12:30:45")
        assert "date" in str(exc_info.value).lower() or "format" in str(exc_info.value).lower()
    
    def test_invalid_date_format_european(self):
        """European date format (DD-MM-YYYY) should fail"""
        with pytest.raises(ValidationError) as exc_info:
            ObservationDateTime(date="15-01-2026", time="12:30:45")
        assert "date" in str(exc_info.value).lower() or "format" in str(exc_info.value).lower()
    
    def test_invalid_date_format_slashes(self):
        """Date with slashes should fail"""
        with pytest.raises(ValidationError) as exc_info:
            ObservationDateTime(date="2026/01/15", time="12:30:45")
        assert "date" in str(exc_info.value).lower() or "format" in str(exc_info.value).lower()
    
    def test_invalid_date_format_text(self):
        """Random text as date should fail"""
        with pytest.raises(ValidationError) as exc_info:
            ObservationDateTime(date="not-a-date", time="12:30:45")
        assert "date" in str(exc_info.value).lower() or "format" in str(exc_info.value).lower()


class TestTimeFormatValidation:
    """Test time format validation"""
    
    def test_valid_time_format(self):
        """Valid HH:MM:SS format should pass"""
        dt = ObservationDateTime(date="2026-01-15", time="12:30:45")
        assert dt.time == "12:30:45"
    
    def test_valid_time_midnight(self):
        """Midnight format should pass"""
        dt = ObservationDateTime(date="2026-01-15", time="00:00:00")
        assert dt.time == "00:00:00"
    
    def test_valid_time_end_of_day(self):
        """End of day should pass"""
        dt = ObservationDateTime(date="2026-01-15", time="23:59:59")
        assert dt.time == "23:59:59"
    
    def test_invalid_time_hour_too_high(self):
        """Hour > 23 should fail"""
        with pytest.raises(ValidationError) as exc_info:
            ObservationDateTime(date="2026-01-15", time="25:30:45")
        assert "time" in str(exc_info.value).lower() or "format" in str(exc_info.value).lower()
    
    def test_invalid_time_minute_too_high(self):
        """Minute > 59 should fail"""
        with pytest.raises(ValidationError) as exc_info:
            ObservationDateTime(date="2026-01-15", time="12:99:45")
        assert "time" in str(exc_info.value).lower() or "format" in str(exc_info.value).lower()
    
    def test_invalid_time_second_too_high(self):
        """Second > 59 should fail"""
        with pytest.raises(ValidationError) as exc_info:
            ObservationDateTime(date="2026-01-15", time="12:30:99")
        assert "time" in str(exc_info.value).lower() or "format" in str(exc_info.value).lower()
    
    def test_invalid_time_format_text(self):
        """Random text as time should fail"""
        with pytest.raises(ValidationError) as exc_info:
            ObservationDateTime(date="2026-01-15", time="not-a-time")
        assert "time" in str(exc_info.value).lower() or "format" in str(exc_info.value).lower()
    
    def test_invalid_time_wrong_separator(self):
        """Time with wrong separator should fail"""
        with pytest.raises(ValidationError) as exc_info:
            ObservationDateTime(date="2026-01-15", time="12-30-45")
        assert "time" in str(exc_info.value).lower() or "format" in str(exc_info.value).lower()


class TestTimeRangeBusinessLogic:
    """Test time range business logic validation"""
    
    def test_valid_time_range(self):
        """Valid time range should pass"""
        time_range = TimeRange(
            start=ObservationDateTime(date="2026-01-01", time="00:00:00"),
            end=ObservationDateTime(date="2026-01-02", time="00:00:00"),
            frame_count=10
        )
        assert time_range.start.date == "2026-01-01"
        assert time_range.end.date == "2026-01-02"
    
    def test_same_start_and_end_time(self):
        """Same start and end time should fail"""
        with pytest.raises(ValidationError) as exc_info:
            TimeRange(
                start=ObservationDateTime(date="2026-01-01", time="12:00:00"),
                end=ObservationDateTime(date="2026-01-01", time="12:00:00"),
                frame_count=10
            )
        error_msg = str(exc_info.value).lower()
        assert "start" in error_msg or "end" in error_msg or "time" in error_msg
    
    def test_inverted_times(self):
        """End time before start time should fail"""
        with pytest.raises(ValidationError) as exc_info:
            TimeRange(
                start=ObservationDateTime(date="2026-01-02", time="00:00:00"),
                end=ObservationDateTime(date="2026-01-01", time="00:00:00"),
                frame_count=10
            )
        error_msg = str(exc_info.value).lower()
        assert "start" in error_msg or "end" in error_msg or "before" in error_msg or "after" in error_msg


class TestLocationValidation:
    """Test location validation (already working, ensure it stays working)"""
    
    def test_valid_location(self):
        """Valid location should pass"""
        loc = LocationModel(latitude=40.7128, longitude=-74.0060, elevation=10.0)
        assert loc.latitude == 40.7128
        assert loc.longitude == -74.0060
    
    def test_latitude_boundary_north(self):
        """Latitude 90 should pass"""
        loc = LocationModel(latitude=90.0, longitude=0.0)
        assert loc.latitude == 90.0
    
    def test_latitude_boundary_south(self):
        """Latitude -90 should pass"""
        loc = LocationModel(latitude=-90.0, longitude=0.0)
        assert loc.latitude == -90.0
    
    def test_latitude_too_high(self):
        """Latitude > 90 should fail"""
        with pytest.raises(ValidationError):
            LocationModel(latitude=90.1, longitude=0.0)
    
    def test_latitude_too_low(self):
        """Latitude < -90 should fail"""
        with pytest.raises(ValidationError):
            LocationModel(latitude=-90.1, longitude=0.0)
    
    def test_longitude_boundary_east(self):
        """Longitude 180 should pass"""
        loc = LocationModel(latitude=0.0, longitude=180.0)
        assert loc.longitude == 180.0
    
    def test_longitude_boundary_west(self):
        """Longitude -180 should pass"""
        loc = LocationModel(latitude=0.0, longitude=-180.0)
        assert loc.longitude == -180.0
    
    def test_longitude_too_high(self):
        """Longitude > 180 should fail"""
        with pytest.raises(ValidationError):
            LocationModel(latitude=0.0, longitude=180.1)
    
    def test_longitude_too_low(self):
        """Longitude < -180 should fail"""
        with pytest.raises(ValidationError):
            LocationModel(latitude=0.0, longitude=-180.1)
