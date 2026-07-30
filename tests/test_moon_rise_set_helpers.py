# tests/test_moon_rise_set_helpers.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'research'))
from MoonRiseAndSet import moon_semidiameter, moon_target_altitude, find_altitude_crossings, moon_rise_set
from astropy.coordinates import EarthLocation, get_body
import astropy.units as u
from astropy.time import Time


def test_moon_semidiameter():
    """Test moon semidiameter calculation with typical Earth-Moon distance."""
    # Average Earth-Moon distance is about 384,400 km
    distance = 384400 * u.km
    semidiam = moon_semidiameter(distance)
    
    # Moon's angular diameter at mean distance is about 0.52 degrees (radius ~0.26 deg)
    assert semidiam.to(u.deg).value > 0.2, "Semidiameter should be positive"
    assert semidiam.to(u.deg).value < 0.35, "Semidiameter should be less than 0.35 deg"
    print(f"Moon semidiameter at {distance}: {semidiam.to(u.deg).value:.3f} degrees")


def test_moon_target_altitude():
    """Test that moon_target_altitude returns a negative value accounting for refraction and size."""
    location = EarthLocation(lat=51.5*u.deg, lon=-0.127*u.deg, height=0*u.m)
    time = Time('2025-04-28 12:00:00', format='iso', scale='utc')
    
    target_alt = moon_target_altitude(location, time)
    
    # Should be negative (below geometric horizon) to account for refraction and semidiameter
    assert target_alt.to(u.deg).value < 0, "Target altitude should be negative"
    # Typically around -0.8 to -1.0 degrees
    assert target_alt.to(u.deg).value > -1.5, "Target altitude should be reasonable"
    print(f"Moon target altitude: {target_alt.to(u.deg).value:.3f} degrees")


def test_find_altitude_crossings_normal_day():
    """Test find_altitude_crossings finds moon rise and set on a normal day."""
    location = EarthLocation(lat=51.5*u.deg, lon=-0.127*u.deg, height=0*u.m)
    start = Time('2025-04-28 00:00:00', format='iso', scale='utc')
    end = Time('2025-04-29 00:00:00', format='iso', scale='utc')
    target_altitude = -0.816 * u.deg
    
    def moon_position(times):
        return get_body('moon', times, location=location)
    
    crossings = find_altitude_crossings(
        position_func=moon_position,
        location=location,
        start_time=start,
        end_time=end,
        target_altitude=target_altitude
    )
    
    # On a normal day at mid-latitudes, should have at least one crossing
    assert len(crossings) > 0, "Should find at least one crossing"
    
    # Each crossing should have a time and event type
    for crossing_time, event_type in crossings:
        assert isinstance(crossing_time, Time), "Crossing time should be Time object"
        assert event_type in ['rise', 'set'], f"Event type should be 'rise' or 'set', got {event_type}"
        print(f"Moon {event_type} at {crossing_time.iso}")


def test_find_altitude_crossings_no_crossings():
    """Test find_altitude_crossings returns empty list when no crossings occur."""
    # Svalbard during circumpolar moon period
    location = EarthLocation(lat=78*u.deg, lon=15*u.deg, height=0*u.m)
    start = Time('2025-02-11 00:00:00', format='iso', scale='utc')
    end = Time('2025-02-12 00:00:00', format='iso', scale='utc')
    target_altitude = -0.816 * u.deg
    
    def moon_position(times):
        return get_body('moon', times, location=location)
    
    crossings = find_altitude_crossings(
        position_func=moon_position,
        location=location,
        start_time=start,
        end_time=end,
        target_altitude=target_altitude
    )
    
    # During circumpolar period, should have no crossings
    assert len(crossings) == 0, "Should find no crossings during circumpolar period"
    print("No crossings found during circumpolar period (expected)")


def test_moon_rise_set_normal_day():
    """Test moon_rise_set finds events on a normal day at mid-latitudes."""
    location = EarthLocation(lat=51.5*u.deg, lon=-0.127*u.deg, height=0*u.m)
    jd = Time('2025-04-28', format='iso', scale='utc').jd
    
    events = moon_rise_set(location, jd)
    
    # Should find at least one event on a normal day
    assert len(events) > 0, "Should find at least one rise/set event"
    
    # Verify structure
    for time_obj, event_type in events:
        assert isinstance(time_obj, Time), "Event time should be Time object"
        assert event_type in ['rise', 'set'], f"Event type should be 'rise' or 'set', got {event_type}"
        print(f"Moon {event_type}: {time_obj.iso}")


def test_moon_rise_set_circumpolar():
    """Test moon_rise_set returns empty list when moon is circumpolar."""
    # Svalbard during circumpolar moon
    location = EarthLocation(lat=78*u.deg, lon=15*u.deg, height=0*u.m)
    jd = Time('2025-02-11', format='iso', scale='utc').jd
    
    events = moon_rise_set(location, jd)
    
    # Should return empty list when no crossings
    assert len(events) == 0, "Should return empty list during circumpolar period"
    print("No rise/set events during circumpolar period (expected)")


def test_moon_rise_set_multiple_events():
    """Test moon_rise_set can find multiple rise/set events in one day."""
    # Use equator where moon might cross horizon multiple times
    location = EarthLocation(lat=0*u.deg, lon=0*u.deg, height=0*u.m)
    jd = Time('2025-04-28', format='iso', scale='utc').jd
    
    events = moon_rise_set(location, jd)
    
    # Should have at least one event
    assert len(events) >= 1, "Should find at least one event"
    
    # Verify chronological order if multiple events
    if len(events) > 1:
        for i in range(len(events) - 1):
            assert events[i][0].jd < events[i+1][0].jd, "Events should be chronologically sorted"
    
    print(f"Found {len(events)} moon rise/set event(s)")
