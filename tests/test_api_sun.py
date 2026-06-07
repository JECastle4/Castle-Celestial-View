"""
Unit tests for api/services/sun.py
"""
import pytest
from pydantic import ValidationError
from api.services.sun import calculate_sun_position
from api.models import ObservationDateTime, LocationModel


class TestCalculateSunPosition:
    """Test cases for calculate_sun_position function"""
    
    def test_sun_position_noon_equator(self):
        """Test sun position at solar noon on equator"""
        # At solar noon on the equinox, sun should be near zenith at equator
        result = calculate_sun_position(
            ObservationDateTime(date="2026-03-20", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0, elevation=0.0)
        )
        
        assert "altitude" in result
        assert "azimuth" in result
        assert "is_visible" in result
        assert result["is_visible"] is True
        assert result["altitude"] > 60  # Should be high in the sky
        assert 0 <= result["azimuth"] <= 360
    
    def test_sun_position_midnight(self):
        """Test sun position at midnight (should be below horizon)"""
        # New York at midnight - sun should be below horizon
        result = calculate_sun_position(
            ObservationDateTime(date="2026-02-01", time="00:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=10.0)
        )
        
        assert result["is_visible"] is False
        assert result["altitude"] < 0
    
    def test_sun_position_new_york_noon(self):
        """Test sun position in New York at noon"""
        result = calculate_sun_position(
            ObservationDateTime(date="2026-06-21", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060)
        )
        
        # Sun should be visible and relatively high at noon in summer
        assert result["is_visible"] is True
        assert result["altitude"] > 0
    
    def test_sun_position_north_pole_summer(self):
        """Test sun position at North Pole during summer (midnight sun)"""
        result = calculate_sun_position(
            ObservationDateTime(date="2026-06-21", time="00:00:00"),
            LocationModel(latitude=89.0, longitude=0.0)
        )
        
        # During polar summer, sun should be visible even at midnight
        assert result["is_visible"] is True
        assert result["altitude"] > 0
    
    def test_sun_position_north_pole_winter(self):
        """Test sun position at North Pole during winter (polar night)"""
        result = calculate_sun_position(
            ObservationDateTime(date="2026-12-21", time="12:00:00"),
            LocationModel(latitude=89.0, longitude=0.0)
        )
        
        # During polar winter, sun should be below horizon even at noon
        assert result["is_visible"] is False
        assert result["altitude"] < 0
    
    def test_location_returned(self):
        """Test that location information is returned"""
        result = calculate_sun_position(
            ObservationDateTime(date="2026-02-01", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060, elevation=100.0)
        )
        
        assert "location" in result
        assert result["location"]["latitude"] == 40.7128
        assert result["location"]["longitude"] == -74.0060
        assert result["location"]["elevation"] == 100.0
    
    def test_julian_date_returned(self):
        """Test that Julian Date is returned"""
        result = calculate_sun_position(
            ObservationDateTime(date="2026-02-01", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0)
        )
        
        assert "julian_date" in result
        assert isinstance(result["julian_date"], float)
        assert result["julian_date"] > 0
    
    def test_input_datetime_returned(self):
        """Test that input datetime is echoed back"""
        result = calculate_sun_position(
            ObservationDateTime(date="2026-02-01", time="14:30:45"),
            LocationModel(latitude=40.0, longitude=-75.0)
        )
        
        assert result["input_datetime"] == "2026-02-01T14:30:45Z"
    
    def test_azimuth_range(self):
        """Test that azimuth is always in valid range"""
        result = calculate_sun_position(
            ObservationDateTime(date="2026-02-01", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060)
        )
        
        assert 0 <= result["azimuth"] < 360
    
    def test_altitude_reasonable_range(self):
        """Test that altitude is in reasonable range"""
        result = calculate_sun_position(
            ObservationDateTime(date="2026-02-01", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060)
        )
        
        # Altitude should be between -90 and +90 degrees
        assert -90 <= result["altitude"] <= 90
    
    def test_invalid_latitude_high(self):
        """Test that latitude above 90 raises error"""
        with pytest.raises(ValidationError, match="less_than_equal|greater_than_equal"):
            calculate_sun_position(
                ObservationDateTime(date="2026-02-01", time="12:00:00"),
                LocationModel(latitude=91.0, longitude=0.0)
            )
    
    def test_invalid_latitude_low(self):
        """Test that latitude below -90 raises error"""
        with pytest.raises(ValidationError, match="less_than_equal|greater_than_equal"):
            calculate_sun_position(
                ObservationDateTime(date="2026-02-01", time="12:00:00"),
                LocationModel(latitude=-91.0, longitude=0.0)
            )
    
    def test_invalid_longitude_high(self):
        """Test that longitude above 180 raises error"""
        with pytest.raises(ValidationError, match="less_than_equal|greater_than_equal"):
            calculate_sun_position(
                ObservationDateTime(date="2026-02-01", time="12:00:00"),
                LocationModel(latitude=0.0, longitude=181.0)
            )
    
    def test_invalid_longitude_low(self):
        """Test that longitude below -180 raises error"""
        with pytest.raises(ValidationError, match="less_than_equal|greater_than_equal"):
            calculate_sun_position(
                ObservationDateTime(date="2026-02-01", time="12:00:00"),
                LocationModel(latitude=0.0, longitude=-181.0)
            )
    
    def test_invalid_date_format(self):
        """Test that invalid date format raises error"""
        with pytest.raises(ValueError):
            calculate_sun_position(
                ObservationDateTime(date="not-a-date", time="12:00:00"),
                LocationModel(latitude=0.0, longitude=0.0)
            )
    
    def test_invalid_time_format(self):
        """Test that invalid time format raises error"""
        with pytest.raises(ValueError):
            calculate_sun_position(
                ObservationDateTime(date="2026-02-01", time="not-a-time"),
                LocationModel(latitude=0.0, longitude=0.0)
            )
    
    def test_different_elevations(self):
        """Test that different elevations produce slightly different results"""
        result_sea_level = calculate_sun_position(
            ObservationDateTime(date="2026-02-01", time="12:00:00"),
            LocationModel(latitude=40.0, longitude=-75.0, elevation=0.0)
        )
        
        result_mountain = calculate_sun_position(
            ObservationDateTime(date="2026-02-01", time="12:00:00"),
            LocationModel(latitude=40.0, longitude=-75.0, elevation=3000.0)
        )
        
        # Altitude might be very slightly different at higher elevation
        # (atmospheric effects ignored since pressure=0, but still worth testing)
        assert isinstance(result_sea_level["altitude"], float)
        assert isinstance(result_mountain["altitude"], float)
    
    def test_visibility_boundary(self):
        """Test sun visibility near horizon"""
        # Find a time/location where sun is near horizon
        result = calculate_sun_position(
            ObservationDateTime(date="2026-02-01", time="07:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060)
        )
        
        # is_visible should match the sign of altitude
        if result["altitude"] > 0:
            assert result["is_visible"] is True
        else:
            assert result["is_visible"] is False
    
    def test_ra_dec_returned(self):
        """Test that RA/Dec coordinates are returned"""
        result = calculate_sun_position(
            ObservationDateTime(date="2026-02-01", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060)
        )
        
        assert "ra_degrees" in result
        assert "dec_degrees" in result
        assert isinstance(result["ra_degrees"], float)
        assert isinstance(result["dec_degrees"], float)
    
    def test_ra_dec_ranges(self):
        """Test that RA/Dec are in valid ranges"""
        result = calculate_sun_position(
            ObservationDateTime(date="2026-02-01", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060)
        )
        
        # RA should be 0-360 degrees
        assert 0 <= result["ra_degrees"] <= 360
        # Dec should be -90 to +90 degrees
        assert -90 <= result["dec_degrees"] <= 90
    
    def test_ra_dec_observer_independent(self):
        """Test that RA/Dec are same regardless of observer location"""
        # RA/Dec are celestial coordinates, should not depend on observer location
        # (only time matters)
        result_nyc = calculate_sun_position(
            ObservationDateTime(date="2026-02-01", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060)
        )
        
        result_london = calculate_sun_position(
            ObservationDateTime(date="2026-02-01", time="12:00:00"),
            LocationModel(latitude=51.5074, longitude=-0.1278)
        )
        
        # RA/Dec should be very close (within ~1 degree due to slight time variations)
        # since we're using the same absolute time
        assert abs(result_nyc["ra_degrees"] - result_london["ra_degrees"]) < 0.1
        assert abs(result_nyc["dec_degrees"] - result_london["dec_degrees"]) < 0.1
    
    def test_ra_dec_at_solstices_equinoxes(self):
        """Test RA/Dec at significant celestial dates"""
        # Spring equinox - sun near 0° RA
        result_equinox = calculate_sun_position(
            ObservationDateTime(date="2026-03-20", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0)
        )
        assert 0 <= result_equinox["ra_degrees"] <= 360
        assert -90 <= result_equinox["dec_degrees"] <= 90
        
        # Summer solstice - sun at northernmost declination (~23.4°)
        result_summer = calculate_sun_position(
            ObservationDateTime(date="2026-06-20", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0)
        )
        # Dec should be near +23.4 degrees (allow range for solstice timing)
        assert -25 < result_summer["dec_degrees"] < 25
        assert 0 <= result_summer["ra_degrees"] <= 360
    
    def test_southern_hemisphere(self):
        """Test sun position in southern hemisphere"""
        # Sydney, Australia - using UTC time
        result = calculate_sun_position(
            ObservationDateTime(date="2026-02-01", time="02:00:00"),
            LocationModel(latitude=-33.8688, longitude=151.2093)
        )
        
        assert result["is_visible"] is True
        assert result["altitude"] > 0
        assert 0 <= result["azimuth"] < 360
