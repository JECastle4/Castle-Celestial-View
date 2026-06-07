"""
Unit tests for api/services/dates.py
"""
import pytest
from api.services.dates import calculate_day_of_week


class TestCalculateDayOfWeek:
    """Test cases for calculate_day_of_week function"""
    
    def test_known_date_sunday(self):
        """Test a known Sunday date"""
        # 2026-02-01 is a Sunday
        result = calculate_day_of_week("2026-02-01", "00:00:00")
        
        assert result["day_of_week"] == 0
        assert result["day_name"] == "Sunday"
        assert "julian_date" in result
        assert result["input_datetime"] == "2026-02-01T00:00:00Z"
    
    def test_known_date_wednesday(self):
        """Test a known Wednesday date"""
        # 2026-01-01 is a Thursday, so 2026-01-07 is a Wednesday
        result = calculate_day_of_week("2026-01-07", "12:30:00")
        
        assert result["day_of_week"] == 3
        assert result["day_name"] == "Wednesday"
        assert result["input_datetime"] == "2026-01-07T12:30:00Z"
    
    def test_known_date_saturday(self):
        """Test a known Saturday date"""
        # 2026-01-03 is a Saturday
        result = calculate_day_of_week("2026-01-03")
        
        assert result["day_of_week"] == 6
        assert result["day_name"] == "Saturday"
    
    def test_default_time(self):
        """Test that time defaults to midnight"""
        result = calculate_day_of_week("2026-02-01")
        
        assert result["input_datetime"] == "2026-02-01T00:00:00Z"
    
    def test_custom_time(self):
        """Test with custom time"""
        result = calculate_day_of_week("2026-02-01", "15:45:30")
        
        assert result["input_datetime"] == "2026-02-01T15:45:30Z"
        # Day of week should be same regardless of time
        assert result["day_of_week"] == 0
    
    def test_julian_date_returned(self):
        """Test that Julian Date is a float"""
        result = calculate_day_of_week("2026-02-01", "12:00:00")
        
        assert isinstance(result["julian_date"], float)
        assert result["julian_date"] > 0
    
    def test_all_days_of_week(self):
        """Test a sequence of dates covering all days"""
        # Starting from 2026-02-01 (Sunday), test 7 consecutive days
        expected_days = [
            (0, "Sunday"),
            (1, "Monday"),
            (2, "Tuesday"),
            (3, "Wednesday"),
            (4, "Thursday"),
            (5, "Friday"),
            (6, "Saturday")
        ]
        
        for i, (expected_index, expected_name) in enumerate(expected_days):
            day = 1 + i
            result = calculate_day_of_week(f"2026-02-{day:02d}")
            assert result["day_of_week"] == expected_index
            assert result["day_name"] == expected_name
    
    def test_invalid_date_format(self):
        """Test that invalid date format raises ValueError"""
        with pytest.raises(ValueError):
            calculate_day_of_week("not-a-date")
    
    def test_invalid_time_format(self):
        """Test that invalid time format raises ValueError"""
        with pytest.raises(ValueError):
            calculate_day_of_week("2026-02-01", "not-a-time")
    
    def test_leap_year_date(self):
        """Test February 29 on a leap year"""
        # 2024 is a leap year, Feb 29 exists
        result = calculate_day_of_week("2024-02-29")
        
        assert "julian_date" in result
        assert result["day_of_week"] in range(7)
    
    def test_historical_date(self):
        """Test a historical date"""
        # January 1, 2000 was a Saturday
        result = calculate_day_of_week("2000-01-01")
        
        assert result["day_of_week"] == 6
        assert result["day_name"] == "Saturday"
    
    def test_future_date(self):
        """Test a future date"""
        result = calculate_day_of_week("2030-12-31")
        
        assert result["day_of_week"] in range(7)
        assert result["day_name"] in ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    
    def test_gregorian_calendar_transition_before(self):
        """Test date just before Gregorian calendar adoption (Oct 4, 1582)"""
        # Last day of Julian calendar (proleptic Gregorian date)
        result = calculate_day_of_week("1582-10-04")
        
        assert result["day_of_week"] in range(7)
        assert "julian_date" in result
        assert result["julian_date"] > 0
    
    def test_gregorian_calendar_transition_after(self):
        """Test date just after Gregorian calendar adoption (Oct 15, 1582)"""
        # First day of Gregorian calendar
        result = calculate_day_of_week("1582-10-15")
        
        assert result["day_of_week"] in range(7)
        assert "julian_date" in result
        assert result["julian_date"] > 0
    
    def test_gregorian_missing_dates(self):
        """Test dates that were skipped in Gregorian transition (Oct 5-14, 1582)"""
        # These dates "don't exist" in Gregorian calendar but astropy handles them
        # using proleptic Gregorian calendar (extends Gregorian rules backward)
        for day in [5, 10, 14]:
            result = calculate_day_of_week(f"1582-10-{day:02d}")
            
            # Should still calculate successfully
            assert result["day_of_week"] in range(7)
            assert "julian_date" in result
    
    def test_pre_gregorian_date(self):
        """Test a date well before Gregorian calendar (year 1000)"""
        result = calculate_day_of_week("1000-01-01")
        
        assert result["day_of_week"] in range(7)
        assert result["day_name"] in ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        assert result["julian_date"] > 0
    
    def test_jd_continuity_across_transition(self):
        """Test that Julian Date is continuous across calendar transition"""
        result_oct4 = calculate_day_of_week("1582-10-04")
        result_oct15 = calculate_day_of_week("1582-10-15")
        
        jd_oct4 = result_oct4["julian_date"]
        jd_oct15 = result_oct15["julian_date"]
        
        # Historically, Oct 15 was the day after Oct 4 (calendar skipped, not time)
        # But astropy uses proleptic Gregorian, so these are actually 11 days apart
        days_diff = jd_oct15 - jd_oct4
        
        # In proleptic Gregorian calendar (what astropy uses), these dates are 11 days apart
        assert 10.9 < days_diff < 11.1, f"Expected ~11 days, got {days_diff}"
    
    def test_consecutive_days_jd_difference(self):
        """Test that consecutive dates differ by ~1 JD"""
        result1 = calculate_day_of_week("2026-02-01", "00:00:00")
        result2 = calculate_day_of_week("2026-02-02", "00:00:00")
        
        jd_diff = result2["julian_date"] - result1["julian_date"]
        
        # Consecutive dates should differ by exactly 1 day
        assert 0.99 < jd_diff < 1.01, f"Expected ~1 day, got {jd_diff}"
    
    def test_year_1_ce(self):
        """Test year 1 CE (near the boundary of common date representations)"""
        result = calculate_day_of_week("0001-01-01")
        
        assert result["julian_date"] > 0
        assert result["day_of_week"] in range(7)
        assert result["day_name"] in ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    
    def test_year_9999_ce(self):
        """Test year 9999 CE (boundary of 4-digit years)"""
        result = calculate_day_of_week("9999-12-31")
        
        assert result["julian_date"] > 0
        assert result["day_of_week"] in range(7)
        assert result["day_name"] in ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    
    def test_five_digit_year_fails(self):
        """Test that 5-digit years fail due to Python datetime limitations"""
        # Python's datetime.fromisoformat() doesn't support 5-digit years
        with pytest.raises(ValueError):
            calculate_day_of_week("10000-01-01")
    
    def test_bce_date_fails(self):
        """Test that BCE dates fail due to Python datetime limitations"""
        # Python's datetime.fromisoformat() doesn't support negative years
        # API is limited to year 1 CE onwards, even though astropy can handle BCE
        with pytest.raises(ValueError):
            calculate_day_of_week("-4713-11-24")
    
    def test_year_zero_warning(self):
        """Test that year 0 produces a result (astropy accepts it with warning)"""
        # Year 0 doesn't exist in the proleptic Gregorian calendar
        # (Goes from 1 BCE to 1 CE), but astropy Time accepts it with a warning
        # and treats it as astronomical year 0 (1 BCE)
        import warnings
        from erfa import ErfaWarning
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ErfaWarning)
            result = calculate_day_of_week("0000-01-01")
            assert "julian_date" in result
            assert "day_of_week" in result
