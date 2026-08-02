"""
Tests for api/models.py validation error paths
"""
import pytest
from pydantic import ValidationError
from api.models import ObservationDateTime


class TestObservationDateTimeValidation:
    """Test ObservationDateTime model validation with custom validators"""
    
    def test_valid_date_and_time(self):
        """Test valid date and time"""
        model = ObservationDateTime(date="2026-02-01", time="12:30:45")
        assert model.date == "2026-02-01"
        assert model.time == "12:30:45"
    
    def test_valid_date_only(self):
        """Test valid date with default time"""
        model = ObservationDateTime(date="2026-02-01")
        assert model.date == "2026-02-01"
        assert model.time == "00:00:00"
    
    # Direct validator tests - call validators directly to ensure coverage
    
    def test_direct_validate_date_format_invalid_regex(self):
        """Test date validator directly with invalid regex format"""
        from api.models import ObservationDateTime
        with pytest.raises(ValueError) as exc_info:
            ObservationDateTime.validate_date_format("20260201")
        assert "YYYY-MM-DD" in str(exc_info.value)
    
    def test_direct_validate_date_format_valid(self):
        """Test date validator directly with valid format"""
        result = ObservationDateTime.validate_date_format("2026-02-01")
        assert result == "2026-02-01"
    
    def test_direct_validate_time_format_invalid_regex(self):
        """Test time validator directly with invalid regex format"""
        from api.models import ObservationDateTime
        with pytest.raises(ValueError) as exc_info:
            ObservationDateTime.validate_time_format("123045")
        assert "HH:MM:SS" in str(exc_info.value)
    
    def test_direct_validate_time_format_valid(self):
        """Test time validator directly with valid format"""
        result = ObservationDateTime.validate_time_format("12:30:45")
        assert result == "12:30:45"
    
    # Date format validation tests via model instantiation
    
    def test_invalid_date_format_missing_dashes(self):
        """Test date format validation rejects dates without dashes"""
        with pytest.raises(ValidationError) as exc_info:
            ObservationDateTime(date="20260201")
        
        errors = exc_info.value.errors()
        assert any("YYYY-MM-DD" in str(e) for e in errors)
    
    def test_invalid_date_format_wrong_separators(self):
        """Test date format validation rejects wrong separators"""
        with pytest.raises(ValidationError) as exc_info:
            ObservationDateTime(date="2026/02/01")
        
        errors = exc_info.value.errors()
        assert any("YYYY-MM-DD" in str(e) for e in errors)
    
    # Date format validation tests
    
    def test_invalid_date_format_missing_dashes(self):
        """Test date format validation rejects dates without dashes"""
        with pytest.raises(ValidationError) as exc_info:
            ObservationDateTime(date="20260201")
        
        errors = exc_info.value.errors()
        assert any("YYYY-MM-DD" in str(e) for e in errors)
    
    def test_invalid_date_format_wrong_separators(self):
        """Test date format validation rejects wrong separators"""
        with pytest.raises(ValidationError) as exc_info:
            ObservationDateTime(date="2026/02/01")
        
        errors = exc_info.value.errors()
        assert any("YYYY-MM-DD" in str(e) for e in errors)
    
    def test_invalid_date_format_letters(self):
        """Test date format validation rejects non-numeric dates"""
        with pytest.raises(ValidationError) as exc_info:
            ObservationDateTime(date="202a-02-01")
        
        errors = exc_info.value.errors()
        assert any("YYYY-MM-DD" in str(e) for e in errors)
    
    def test_invalid_date_not_string(self):
        """Test date must be string type"""
        with pytest.raises(ValidationError) as exc_info:
            ObservationDateTime(date=20260201)  # type: ignore
        
        errors = exc_info.value.errors()
        assert any("string" in str(e).lower() for e in errors)
    
    def test_invalid_date_nonexistent(self):
        """Test invalid date (e.g., February 30)"""
        with pytest.raises(ValidationError) as exc_info:
            ObservationDateTime(date="2026-02-30")
        
        errors = exc_info.value.errors()
        assert any("Invalid date" in str(e) for e in errors)
    
    # Time format validation tests
    
    def test_invalid_time_format_missing_colons(self):
        """Test time format validation rejects times without colons"""
        with pytest.raises(ValidationError) as exc_info:
            ObservationDateTime(date="2026-02-01", time="123045")
        
        errors = exc_info.value.errors()
        assert any("HH:MM:SS" in str(e) for e in errors)
    
    def test_invalid_time_format_wrong_separators(self):
        """Test time format validation rejects wrong separators"""
        with pytest.raises(ValidationError) as exc_info:
            ObservationDateTime(date="2026-02-01", time="12-30-45")
        
        errors = exc_info.value.errors()
        assert any("HH:MM:SS" in str(e) for e in errors)
    
    def test_invalid_time_format_letters(self):
        """Test time format validation rejects non-numeric times"""
        with pytest.raises(ValidationError) as exc_info:
            ObservationDateTime(date="2026-02-01", time="1a:30:45")
        
        errors = exc_info.value.errors()
        assert any("HH:MM:SS" in str(e) for e in errors)
    
    def test_invalid_time_not_string(self):
        """Test time must be string type"""
        with pytest.raises(ValidationError) as exc_info:
            ObservationDateTime(date="2026-02-01", time=123045)  # type: ignore
        
        errors = exc_info.value.errors()
        assert any("string" in str(e).lower() for e in errors)
    
    def test_invalid_time_hour_out_of_range(self):
        """Test hour must be 0-23"""
        with pytest.raises(ValidationError) as exc_info:
            ObservationDateTime(date="2026-02-01", time="24:00:00")
        
        errors = exc_info.value.errors()
        assert any("Hour" in str(e) for e in errors)
    
    def test_invalid_time_minute_out_of_range(self):
        """Test minute must be 0-59"""
        with pytest.raises(ValidationError) as exc_info:
            ObservationDateTime(date="2026-02-01", time="12:60:00")
        
        errors = exc_info.value.errors()
        assert any("Minute" in str(e) for e in errors)
    
    def test_invalid_time_second_out_of_range(self):
        """Test second must be 0-59"""
        with pytest.raises(ValidationError) as exc_info:
            ObservationDateTime(date="2026-02-01", time="12:30:60")
        
        errors = exc_info.value.errors()
        assert any("Second" in str(e) for e in errors)
    
    def test_valid_time_edge_cases(self):
        """Test valid edge case times"""
        # Start of day
        model1 = ObservationDateTime(date="2026-02-01", time="00:00:00")
        assert model1.time == "00:00:00"
        
        # End of day
        model2 = ObservationDateTime(date="2026-02-01", time="23:59:59")
        assert model2.time == "23:59:59"
        
        # Noon
        model3 = ObservationDateTime(date="2026-02-01", time="12:00:00")
        assert model3.time == "12:00:00"
    
    def test_date_boundary_cases(self):
        """Test valid edge case dates"""
        # Leap year February 29
        model1 = ObservationDateTime(date="2024-02-29")
        assert model1.date == "2024-02-29"
        
        # Year boundary
        model2 = ObservationDateTime(date="2099-12-31")
        assert model2.date == "2099-12-31"
        
        # Early date
        model3 = ObservationDateTime(date="1900-01-01")
        assert model3.date == "1900-01-01"
