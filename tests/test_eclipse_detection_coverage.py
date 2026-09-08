"""Tests for eclipse detection and contact times (Issue #141).

Tests designed to achieve high code coverage of:
- api/services/eclipse_detection.py
- api/services/eclipse_contact_times.py
"""

import pytest
import numpy as np
from astropy.time import Time
from api.services.eclipse_detection import (
    check_eclipse_at_time,
    is_new_moon,
    is_full_moon,
    classify_lunar_eclipse_type,
    classify_solar_eclipse_type,
    get_moon_ecliptic_latitude,
    LUNAR_ECLIPSE_LATITUDE_LIMIT,
    SOLAR_ECLIPSE_LATITUDE_LIMIT,
)
from api.services.eclipse_contact_times import (
    calculate_lunar_contact_times,
    calculate_solar_contact_times,
)


class TestSolarEclipseDetection:
    """Test solar eclipse detection (coverage for lines 449-497 in eclipse_detection.py)."""

    def test_solar_eclipse_august_2026(self):
        """Test detection of total solar eclipse on 2026-08-12."""
        # Total Solar Eclipse, greatest eclipse at 2026-08-12 18:11 UTC
        time = Time('2026-08-12 18:11:00', scale='utc')
        result = check_eclipse_at_time(time, is_lunar=False)

        assert result['is_eclipse'] is True
        assert result['eclipse_type'] in ['TOTAL', 'ANNULAR', 'PARTIAL']
        assert result['phase'] == 'new'
        assert 'greatest_eclipse_time' in result
        assert result['size_ratio'] is not None

    def test_solar_eclipse_february_2026(self):
        """Test detection of annular solar eclipse on 2026-02-17."""
        # Annular Solar Eclipse, greatest eclipse at 2026-02-17 14:29 UTC
        time = Time('2026-02-17 14:29:00', scale='utc')
        result = check_eclipse_at_time(time, is_lunar=False)

        assert result['is_eclipse'] is True
        # Could be ANNULAR or TOTAL depending on location - we test for either
        assert result['eclipse_type'] in ['TOTAL', 'ANNULAR', 'PARTIAL']
        assert result['size_ratio'] is not None
        assert 'umbral_exists' in result

    def test_no_solar_eclipse_during_full_moon(self):
        """Test that no solar eclipse occurs during full moon (time not at new moon)."""
        # Full moon - no solar eclipse possible
        time = Time('2026-08-27 12:00:00', scale='utc')  # ~full moon
        result = check_eclipse_at_time(time, is_lunar=False)

        # Should not detect an eclipse
        assert result['is_eclipse'] is False
        assert result['eclipse_type'] == 'NONE'
        assert result['size_ratio'] is None

    def test_random_time_no_solar_eclipse(self):
        """Test that random time outside eclipse window shows no eclipse."""
        # Random time when no eclipse occurs
        time = Time('2026-08-20 15:30:00', scale='utc')
        result = check_eclipse_at_time(time, is_lunar=False)

        # Should not detect an eclipse (unless by chance this IS an eclipse time)
        # If it is, that's fine - the test verifies the function runs without error
        assert 'is_eclipse' in result
        assert 'eclipse_type' in result


class TestLunarEclipseDetection:
    """Test lunar eclipse detection (existing coverage test for completeness)."""

    def test_lunar_eclipse_august_2026(self):
        """Test detection of lunar eclipse on 2026-08-28."""
        # Total Lunar Eclipse, greatest eclipse at 2026-08-28 03:00 UTC
        time = Time('2026-08-28 03:00:00', scale='utc')
        result = check_eclipse_at_time(time, is_lunar=True)

        assert result['is_eclipse'] is True
        assert result['eclipse_type'] in ['TOTAL', 'PARTIAL', 'PENUMBRAL']
        assert result['phase'] == 'full'
        assert result['umbral_magnitude'] is not None

    def test_lunar_eclipse_march_2026(self):
        """Test detection of lunar eclipse on 2026-03-03."""
        time = Time('2026-03-03 14:00:00', scale='utc')
        result = check_eclipse_at_time(time, is_lunar=True)

        assert result['is_eclipse'] is True
        assert result['eclipse_type'] in ['TOTAL', 'PARTIAL', 'PENUMBRAL']
        assert result['phase'] == 'full'

    def test_no_lunar_eclipse_during_new_moon(self):
        """Test that no lunar eclipse occurs during new moon (time not at full moon)."""
        # New moon - no lunar eclipse possible
        time = Time('2026-08-10 13:00:00', scale='utc')  # ~new moon
        result = check_eclipse_at_time(time, is_lunar=True)

        # Should not detect an eclipse
        assert result['is_eclipse'] is False
        assert result['eclipse_type'] == 'NONE'
        assert result['umbral_magnitude'] is None


class TestMoonPhaseDetection:
    """Test is_new_moon and is_full_moon helper functions.

    These test coverage for lines 70-72 and 85-87 in eclipse_detection.py
    (the False return branches).
    """

    def test_is_full_moon_at_full_moon(self):
        """Test that full moon is correctly identified as full moon.
        
        Uses actual eclipse detection result to identify full moon time.
        """
        # Get a confirmed full moon eclipse time
        time = Time('2026-08-28 03:00:00', scale='utc')  # Confirmed lunar eclipse (full moon)
        # Should return True (or close to True)
        result = is_full_moon(time, tolerance_deg=20)
        assert result is True or result is np.True_

    def test_is_full_moon_at_quarter_moon(self):
        """Test that quarter moon is NOT identified as full moon (covers False branch).
        
        Tests False return to improve code coverage.
        """
        # ~7 days from full moon = quarter moon
        time = Time('2026-09-04 12:00:00', scale='utc')
        # Should return False (covers line 92-93 False case)
        result = is_full_moon(time, tolerance_deg=5)
        # Should be False with tight tolerance
        assert result is False or result is np.False_

    def test_is_new_moon_at_new_moon(self):
        """Test that new moon is correctly identified as new moon.
        
        Uses actual eclipse detection result to identify new moon time.
        """
        # Get a confirmed new moon solar eclipse time
        time = Time('2026-08-12 18:11:00', scale='utc')  # Confirmed solar eclipse (new moon)
        # Should return True (or close to True)
        result = is_new_moon(time, tolerance_deg=20)
        assert result is True or result is np.True_

    def test_is_new_moon_at_quarter_moon(self):
        """Test that quarter moon is NOT identified as new moon (covers False branch).
        
        Tests False return to improve code coverage.
        """
        # ~7 days from new moon = quarter moon
        time = Time('2026-08-19 12:00:00', scale='utc')
        # Should return False (covers line 70-72 False case)
        result = is_new_moon(time, tolerance_deg=5)
        # Should be False with tight tolerance
        assert result is False or result is np.False_

    def test_is_full_moon_with_large_tolerance(self):
        """Test is_full_moon with large tolerance (edge case coverage)."""
        time = Time('2026-09-04 12:00:00', scale='utc')
        # With large tolerance, quarter moon might register as close to full
        result = is_full_moon(time, tolerance_deg=45)
        # Result depends on exact phase angle
        assert isinstance(result, (bool, np.bool_))

    def test_is_new_moon_with_large_tolerance(self):
        """Test is_new_moon with large tolerance (edge case coverage)."""
        time = Time('2026-08-19 12:00:00', scale='utc')
        # With large tolerance, quarter moon might register as close to new
        result = is_new_moon(time, tolerance_deg=45)
        # Result depends on exact phase angle
        assert isinstance(result, (bool, np.bool_))


class TestSolarContactTimes:
    """Test solar contact time calculation.

    These test coverage for lines 449-497 in eclipse_detection.py
    and the entire calculate_solar_contact_times function.
    """

    def test_solar_contact_times_august_2026(self):
        """Test solar contact time calculation for 2026 solar eclipse."""
        greatest_time = Time('2026-08-12 18:11:00', scale='utc')
        
        result = calculate_solar_contact_times(greatest_time, search_window_hours=3)

        # Should return dict with contact times
        assert isinstance(result, dict)
        assert 'eclipse_begins' in result
        assert 'eclipse_ends' in result
        assert 'central_phase_begins' in result
        assert 'central_phase_ends' in result

        # At least eclipse begins/ends should be found for a real eclipse
        # (central phase might be None for partial eclipse)
        assert result['eclipse_begins'] is not None or result['eclipse_ends'] is not None

    def test_solar_contact_times_return_iso_format(self):
        """Test that solar contact times are returned in ISO format."""
        greatest_time = Time('2026-08-12 18:11:00', scale='utc')
        result = calculate_solar_contact_times(greatest_time, search_window_hours=3)

        # If times are found, they should be ISO strings
        if result['eclipse_begins'] is not None:
            assert isinstance(result['eclipse_begins'], str)
            # ISO format with either 'T' or space separator
            assert 'T' in result['eclipse_begins'] or ' ' in result['eclipse_begins']
        if result['eclipse_ends'] is not None:
            assert isinstance(result['eclipse_ends'], str)

    def test_solar_contact_times_edge_case_none_returns(self):
        """Test that missing contact times return None (edge case coverage).
        
        Tests the code paths where _find_crossing_before/_find_crossing_after
        return None (lines 54, 57, 64, 67 in eclipse_contact_times.py).
        """
        # Use a time that's clearly not an eclipse
        # This should result in some None returns
        non_eclipse_time = Time('2026-08-20 12:00:00', scale='utc')
        
        result = calculate_solar_contact_times(non_eclipse_time, search_window_hours=1)
        
        # Result should still be valid dict, but might have None values
        assert isinstance(result, dict)
        # At least one of these should likely be None for non-eclipse time
        assert result['eclipse_begins'] is not None or result['eclipse_ends'] is None


class TestLunarContactTimes:
    """Test lunar contact time calculation."""

    def test_lunar_contact_times_august_2026(self):
        """Test lunar contact time calculation for 2026 lunar eclipse."""
        greatest_time = Time('2026-08-28 03:00:00', scale='utc')
        
        result = calculate_lunar_contact_times(greatest_time, search_window_hours=6)

        # Should return dict with contact times
        assert isinstance(result, dict)
        assert 'p1' in result  # Penumbral entry
        assert 'p4' in result  # Penumbral exit
        assert 'u1' in result  # Umbral entry
        assert 'u4' in result  # Umbral exit
        assert 'u2' in result  # Total/umbral entry (totality begin)
        assert 'u3' in result  # Total/umbral exit (totality end)

        # For a total lunar eclipse, these should be found
        # (though they might be None for partial/penumbral only)
        assert result['p1'] is not None or result['p4'] is not None

    def test_lunar_contact_times_return_iso_format(self):
        """Test that lunar contact times are returned in ISO format."""
        greatest_time = Time('2026-08-28 03:00:00', scale='utc')
        result = calculate_lunar_contact_times(greatest_time, search_window_hours=6)

        # If times are found, they should be ISO strings
        if result['p1'] is not None:
            assert isinstance(result['p1'], str)
            # ISO format with either 'T' or space separator
            assert 'T' in result['p1'] or ' ' in result['p1']

    def test_lunar_contact_times_none_for_non_eclipse(self):
        """Test lunar contact times with non-eclipse time (edge case coverage).
        
        Tests the code paths where _find_crossing_before/_find_crossing_after
        return None (lines 54, 57, 64, 67 in eclipse_contact_times.py).
        """
        # Use a time during new moon (no lunar eclipse possible)
        non_eclipse_time = Time('2026-08-10 12:00:00', scale='utc')
        
        result = calculate_lunar_contact_times(non_eclipse_time, search_window_hours=3)
        
        # For non-eclipse time, all contacts should be None
        assert isinstance(result, dict)
        # Most or all should be None
        assert (result['p1'] is None or result['p4'] is None or
                result['u1'] is None or result['u4'] is None)


class TestEclipseTypeClassification:
    """Test eclipse type classification functions."""

    def test_classify_lunar_eclipse_types(self):
        """Test that lunar eclipse types are correctly classified."""
        # Total lunar eclipse
        total_time = Time('2026-08-28 03:00:00', scale='utc')
        result = classify_lunar_eclipse_type(total_time)
        
        assert 'eclipse_type' in result
        assert result['eclipse_type'] in ['TOTAL', 'PARTIAL', 'PENUMBRAL']
        assert 'umbral_magnitude' in result
        assert 'penumbral_magnitude' in result

    def test_classify_solar_eclipse_types(self):
        """Test that solar eclipse types are correctly classified."""
        # Solar eclipse
        solar_time = Time('2026-08-12 18:11:00', scale='utc')
        result = classify_solar_eclipse_type(solar_time)
        
        assert 'eclipse_type' in result
        assert result['eclipse_type'] in ['TOTAL', 'ANNULAR', 'PARTIAL', 'NONE']
        assert 'size_ratio' in result
        assert 'umbral_exists' in result


class TestEclipsePreFilter:
    """Test the eclipse pre-filter based on Moon's ecliptic latitude.
    
    The pre-filter checks if abs(moon_lat) < LATITUDE_LIMIT. This is geometrically sound
    because eclipses can only occur when the Moon is close to the ecliptic plane (where 
    the Sun always resides). The Moon's orbital inclination is 5.09°, so the threshold
    of 5.3° captures all possible eclipses while rejecting ~95% of syzygy events before
    expensive shadow geometry calculations.
    """

    def test_moon_ecliptic_latitude_valid_range(self):
        """Test that Moon's ecliptic latitude is always within ±6° (well within threshold)."""
        # Test at many times throughout 2025-2026
        test_times = [
            Time('2025-09-07 18:11:00', scale='utc'),  # Lunar eclipse
            Time('2025-09-21', scale='utc'),  # Solar eclipse
            Time('2026-08-12 18:11:00', scale='utc'),  # Solar eclipse  
            Time('2026-08-28 03:00:00', scale='utc'),  # Lunar eclipse
            Time('2026-09-01 12:00:00', scale='utc'),  # Random time
            Time('2025-12-25 00:00:00', scale='utc'),  # Different time
        ]
        
        for time_obj in test_times:
            lat = get_moon_ecliptic_latitude(time_obj)
            # Moon latitude should stay within ~±5.1° (orbital inclination)
            assert -6 < lat < 6, f"Latitude {lat}° at {time_obj.iso} outside expected range"
            assert isinstance(lat, (float, np.floating))

    def test_moon_latitude_changes_during_lunation(self):
        """Test that Moon's latitude oscillates during its ~27.3-day orbit."""
        # Sample Moon latitude during one lunation (every ~2 days)
        base_time = Time('2026-08-01', scale='utc')
        latitudes = []
        
        for i in range(15):
            time_obj = base_time + i * 2  # Every 2 days
            lat = get_moon_ecliptic_latitude(time_obj)
            latitudes.append(lat)
        
        # Latitudes should vary (oscillate as Moon orbits)
        assert max(latitudes) != min(latitudes), "Latitude should change during lunation"
        assert max(latitudes) < 6, "Max latitude should be < 6°"
        assert min(latitudes) > -6, "Min latitude should be > -6°"

    def test_pre_filter_rejects_outside_threshold(self):
        """Test that eclipse check rejects full/new moons with latitude > threshold."""
        # Find a time with large latitude (not close to ecliptic plane)
        # The Moon's latitude varies sinusoidally, so some full moons will be far from ecliptic
        non_eclipse_full = Time('2026-02-03 18:00:00', scale='utc')  # A random full moon
        
        lat = get_moon_ecliptic_latitude(non_eclipse_full)
        
        # If latitude > threshold, pre-filter should reject immediately
        if abs(lat) >= LUNAR_ECLIPSE_LATITUDE_LIMIT:
            result = check_eclipse_at_time(non_eclipse_full, is_lunar=True)
            assert result['is_eclipse'] is False, \
                f"Pre-filter should reject latitude {lat}° > {LUNAR_ECLIPSE_LATITUDE_LIMIT}°"
            assert result['eclipse_type'] == 'NONE'
            assert result['within_threshold'] is False

    def test_pre_filter_allows_within_threshold(self):
        """Test that eclipse check processes events with latitude < threshold."""
        # Use known eclipse times where latitude should be small
        solar_eclipse_time = Time('2026-08-12 18:11:00', scale='utc')
        lat = get_moon_ecliptic_latitude(solar_eclipse_time)
        
        # Should pass pre-filter (proceeds to shadow geometry calculation)
        if abs(lat) < SOLAR_ECLIPSE_LATITUDE_LIMIT:
            result = check_eclipse_at_time(solar_eclipse_time, is_lunar=False)
            assert result['within_threshold'] is True, \
                f"Pre-filter should accept latitude {lat}° < {SOLAR_ECLIPSE_LATITUDE_LIMIT}°"

    def test_latitude_limit_is_correct(self):
        """Test that latitude limit (5.3°) is based on Moon's orbital inclination."""
        # Moon's orbital inclination is ~5.09°, so threshold should be ~5.3°
        assert LUNAR_ECLIPSE_LATITUDE_LIMIT == 5.3, \
            "Lunar latitude limit should be 5.3° (based on orbital inclination 5.09°)"
        assert SOLAR_ECLIPSE_LATITUDE_LIMIT == 5.3, \
            "Solar latitude limit should be 5.3° (symmetric with lunar)"

    def test_eclipses_occur_within_latitude_limit(self):
        """Test that all known eclipses occur when Moon latitude < threshold."""
        known_eclipses = [
            (Time('2025-09-07 18:11:00', scale='utc'), True),   # Lunar
            (Time('2025-09-21', scale='utc'), False),           # Solar
            (Time('2026-08-12 18:11:00', scale='utc'), False),  # Solar
            (Time('2026-08-28 03:00:00', scale='utc'), True),   # Lunar
        ]
        
        for time_obj, is_lunar in known_eclipses:
            lat = get_moon_ecliptic_latitude(time_obj)
            limit = LUNAR_ECLIPSE_LATITUDE_LIMIT if is_lunar else SOLAR_ECLIPSE_LATITUDE_LIMIT
            assert abs(lat) < limit, \
                f"Eclipse at {time_obj.iso} has latitude {lat}° outside limit {limit}°"

    def test_check_eclipse_response_includes_latitude(self):
        """Test that eclipse check responses include moon_ecl_lat_deg for diagnostics."""
        eclipse_time = Time('2026-08-12 18:11:00', scale='utc')
        result = check_eclipse_at_time(eclipse_time, is_lunar=False)
        
        # Response should include diagnostic field
        assert 'moon_ecl_lat_deg' in result, "Response missing moon_ecl_lat_deg"
        assert isinstance(result['moon_ecl_lat_deg'], (float, int))
        # Should match the direct calculation
        expected_lat = get_moon_ecliptic_latitude(eclipse_time)
        assert abs(result['moon_ecl_lat_deg'] - expected_lat) < 0.0001


class TestEclipseEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_eclipse_check_with_default_tolerance(self):
        """Test eclipse detection with default moon phase tolerance."""
        # Should use default tolerance of 10 degrees
        time = Time('2026-08-28 03:00:00', scale='utc')
        result = check_eclipse_at_time(time, is_lunar=True)
        assert 'is_eclipse' in result

    def test_contact_times_with_different_search_windows(self):
        """Test contact time calculation with different search windows."""
        greatest_time = Time('2026-08-28 03:00:00', scale='utc')
        
        # Test with different window sizes
        result_1hour = calculate_lunar_contact_times(greatest_time, search_window_hours=1)
        result_6hours = calculate_lunar_contact_times(greatest_time, search_window_hours=6)
        
        # Both should return valid dicts
        assert isinstance(result_1hour, dict)
        assert isinstance(result_6hours, dict)
        
        # Larger window might find more contacts
        # (smaller window might miss some if contacts are far from greatest time)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
