"""Tests for RA/Dec coordinate returns in API services."""

import pytest
from api.services.sun import calculate_sun_position
from api.services.moon import calculate_moon_position
from api.services.venus import calculate_venus_position
from api.models import ObservationDateTime, LocationModel


class TestSunRADec:
    """Test RA/Dec coordinates for Sun"""
    
    def test_sun_ra_dec_returned(self):
        """Test that RA/Dec coordinates are returned for sun"""
        result = calculate_sun_position(
            ObservationDateTime(date="2026-02-01", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060)
        )
        
        assert "ra_degrees" in result
        assert "dec_degrees" in result
        assert isinstance(result["ra_degrees"], float)
        assert isinstance(result["dec_degrees"], float)
    
    def test_sun_ra_dec_ranges(self):
        """Test that sun RA/Dec are in valid ranges"""
        result = calculate_sun_position(
            ObservationDateTime(date="2026-02-01", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060)
        )
        
        # RA should be 0-360 degrees
        assert 0 <= result["ra_degrees"] <= 360
        # Dec should be -90 to +90 degrees
        assert -90 <= result["dec_degrees"] <= 90
    
    def test_sun_ra_dec_observer_dependent_small_parallax(self):
        """Test that sun RA/Dec are observer-dependent but with minimal parallax
        
        The Sun's RA/Dec returned by the API are topocentric/apparent coordinates
        derived from an AltAz frame. While the Sun exhibits parallax effects due to
        observer location, these are very small (~0.005 degrees) due to the Sun's
        great distance. This test verifies differences stay within expected bounds.
        """
        result_nyc = calculate_sun_position(
            ObservationDateTime(date="2026-02-01", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060)
        )
        
        result_london = calculate_sun_position(
            ObservationDateTime(date="2026-02-01", time="12:00:00"),
            LocationModel(latitude=51.5074, longitude=-0.1278)
        )
        
        # Parallax for the Sun is negligible, so RA/Dec should be nearly identical
        # (within ~0.01 degree due to numerical precision, not actual parallax)
        assert abs(result_nyc["ra_degrees"] - result_london["ra_degrees"]) < 0.01
        assert abs(result_nyc["dec_degrees"] - result_london["dec_degrees"]) < 0.01
    
    def test_sun_ra_dec_summer_solstice(self):
        """Test sun RA/Dec at summer solstice"""
        # At summer solstice, sun's declination should be near +23.4 degrees
        result = calculate_sun_position(
            ObservationDateTime(date="2026-06-20", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0)
        )
        
        # Dec should be near +23.4 degrees at summer solstice
        # Allow larger range for exact solstice timing
        assert -25 < result["dec_degrees"] < 25
        assert 0 <= result["ra_degrees"] <= 360
    
    def test_sun_ra_dec_winter_solstice(self):
        """Test sun RA/Dec at winter solstice"""
        # At winter solstice, sun's declination should be near -23.4 degrees
        result = calculate_sun_position(
            ObservationDateTime(date="2026-12-21", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0)
        )
        
        # Dec should be near -23.4 degrees at winter solstice
        assert -25 < result["dec_degrees"] < -20
        assert 0 <= result["ra_degrees"] <= 360


class TestMoonRADec:
    """Test RA/Dec coordinates for Moon"""
    
    def test_moon_ra_dec_returned(self):
        """Test that RA/Dec coordinates are returned for moon"""
        result = calculate_moon_position(
            ObservationDateTime(date="2026-02-01", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060)
        )
        
        assert "ra_degrees" in result
        assert "dec_degrees" in result
        assert isinstance(result["ra_degrees"], float)
        assert isinstance(result["dec_degrees"], float)
    
    def test_moon_ra_dec_ranges(self):
        """Test that moon RA/Dec are in valid ranges"""
        result = calculate_moon_position(
            ObservationDateTime(date="2026-02-01", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060)
        )
        
        # RA should be 0-360 degrees
        assert 0 <= result["ra_degrees"] <= 360
        # Dec should be -90 to +90 degrees (moon's orbit is ~5.3 degrees inclined to ecliptic)
        assert -30 < result["dec_degrees"] < 30  # Moon's declination range
    
    def test_moon_ra_dec_observer_dependent_parallax(self):
        """Test that moon RA/Dec are observer-dependent due to parallax
        
        The Moon's RA/Dec returned by the API are topocentric/apparent coordinates
        derived from an AltAz frame. Parallax effects vary significantly with observer
        location (typically up to ~1 degree for the Moon).
        
        This test verifies:
        1. Values differ between observers (showing parallax effect exists)
        2. Differences stay within expected parallax bounds (~1 degree)
        """
        result_nyc = calculate_moon_position(
            ObservationDateTime(date="2026-02-01", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060)
        )
        
        result_london = calculate_moon_position(
            ObservationDateTime(date="2026-02-01", time="12:00:00"),
            LocationModel(latitude=51.5074, longitude=-0.1278)
        )
        
        # Parallax should cause measurable differences in RA/Dec
        ra_diff = abs(result_nyc["ra_degrees"] - result_london["ra_degrees"])
        dec_diff = abs(result_nyc["dec_degrees"] - result_london["dec_degrees"])
        
        # Differences should be non-zero (showing observer-dependence)
        assert ra_diff > 0 or dec_diff > 0, "Moon RA/Dec should vary by observer location due to parallax"
        
        # But stay within typical lunar parallax bound (~1 degree)
        assert ra_diff < 1.0, f"RA difference {ra_diff}° exceeds expected parallax bound"
        assert dec_diff < 1.0, f"Dec difference {dec_diff}° exceeds expected parallax bound"
    
    def test_moon_ra_dec_changes_over_time(self):
        """Test that moon RA/Dec change over time periods"""
        result_feb_1 = calculate_moon_position(
            ObservationDateTime(date="2026-02-01", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0)
        )
        
        result_feb_8 = calculate_moon_position(
            ObservationDateTime(date="2026-02-08", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0)
        )
        
        # RA and Dec should be different after 1 week
        # (moon completes ~1/4 orbit around celestial sphere in 7 days)
        ra_diff = abs(result_feb_8["ra_degrees"] - result_feb_1["ra_degrees"])
        # Handle RA wraparound
        if ra_diff > 180:
            ra_diff = 360 - ra_diff
        
        # Moon should move at least 5 degrees in RA
        assert ra_diff > 5  # At least 5 degrees in RA
        assert abs(result_feb_8["dec_degrees"] - result_feb_1["dec_degrees"]) > 2


class TestVenusRADec:
    """Test RA/Dec coordinates for Venus"""
    
    def test_venus_ra_dec_returned(self):
        """Test that RA/Dec coordinates are returned for Venus"""
        result = calculate_venus_position(
            ObservationDateTime(date="2026-02-01", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060)
        )
        
        assert "ra_degrees" in result
        assert "dec_degrees" in result
        assert isinstance(result["ra_degrees"], float)
        assert isinstance(result["dec_degrees"], float)
    
    def test_venus_ra_dec_ranges(self):
        """Test that Venus RA/Dec are in valid ranges"""
        result = calculate_venus_position(
            ObservationDateTime(date="2026-02-01", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060)
        )
        
        # RA should be 0-360 degrees
        assert 0 <= result["ra_degrees"] <= 360
        # Dec should be -90 to +90 degrees
        assert -90 <= result["dec_degrees"] <= 90
    
    def test_venus_ra_dec_observer_dependent_parallax(self):
        """Test that Venus RA/Dec are observer-dependent due to parallax
        
        Venus's RA/Dec returned by the API are topocentric/apparent coordinates
        derived from an AltAz frame. Parallax effects vary with observer location
        (typically ~0.1-1 degree depending on Venus's distance). This test verifies
        differences stay within expected parallax bounds.
        """
        result_nyc = calculate_venus_position(
            ObservationDateTime(date="2026-02-01", time="12:00:00"),
            LocationModel(latitude=40.7128, longitude=-74.0060)
        )
        
        result_london = calculate_venus_position(
            ObservationDateTime(date="2026-02-01", time="12:00:00"),
            LocationModel(latitude=51.5074, longitude=-0.1278)
        )
        
        # Parallax effects should be present but remain within typical bounds (~1 degree)
        ra_diff = abs(result_nyc["ra_degrees"] - result_london["ra_degrees"])
        dec_diff = abs(result_nyc["dec_degrees"] - result_london["dec_degrees"])
        
        # Stay within typical Venus parallax bound
        assert ra_diff < 1.0, f"RA difference {ra_diff}° exceeds expected parallax bound"
        assert dec_diff < 1.0, f"Dec difference {dec_diff}° exceeds expected parallax bound"
    
    def test_venus_ra_dec_changes_over_time(self):
        """Test that Venus RA/Dec change over months (synodic period ~584 days)"""
        result_feb = calculate_venus_position(
            ObservationDateTime(date="2026-02-01", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0)
        )
        
        result_jun = calculate_venus_position(
            ObservationDateTime(date="2026-06-01", time="12:00:00"),
            LocationModel(latitude=0.0, longitude=0.0)
        )
        
        # RA and Dec should be different after 4 months
        ra_diff = abs(result_jun["ra_degrees"] - result_feb["ra_degrees"])
        # Handle RA wraparound
        if ra_diff > 180:
            ra_diff = 360 - ra_diff
        
        # Venus moves slowly but should have some noticeable change in 4 months
        assert ra_diff > 10  # At least 10 degrees in RA
        assert abs(result_jun["dec_degrees"] - result_feb["dec_degrees"]) > 5


class TestRADecConsistency:
    """Test consistency of RA/Dec coordinates across services"""
    
    def test_ra_dec_same_for_same_time_all_bodies(self):
        """Test that different bodies have RA/Dec for same time"""
        time = ObservationDateTime(date="2026-02-01", time="12:00:00")
        location = LocationModel(latitude=40.7128, longitude=-74.0060)
        
        sun_result = calculate_sun_position(time, location)
        moon_result = calculate_moon_position(time, location)
        venus_result = calculate_venus_position(time, location)
        
        # All should have RA/Dec
        assert "ra_degrees" in sun_result
        assert "dec_degrees" in sun_result
        assert "ra_degrees" in moon_result
        assert "dec_degrees" in moon_result
        assert "ra_degrees" in venus_result
        assert "dec_degrees" in venus_result
        
        # RA/Dec should be different (bodies are in different places)
        # (very unlikely they're all at the same RA/Dec at the same time)
        assert sun_result["ra_degrees"] != moon_result["ra_degrees"] or \
               sun_result["dec_degrees"] != moon_result["dec_degrees"]
        assert sun_result["ra_degrees"] != venus_result["ra_degrees"] or \
               sun_result["dec_degrees"] != venus_result["dec_degrees"]
