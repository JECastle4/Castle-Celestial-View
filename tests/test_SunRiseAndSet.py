# tests/test_SunRiseAndSet.py
import sys
from pathlib import Path

research_path = str((Path(__file__).parent.parent / 'research').resolve())
if research_path not in sys.path:
    sys.path.insert(0, research_path)
from SunRiseAndSet import sunrise, sunset
from astropy.coordinates import EarthLocation
import astropy.units as u
from astropy.time import Time


def test_sunrise_equator_jun30_2025():
    """Test sunrise at equator on June 30, 2025 - should return a valid time."""
    location = EarthLocation(lat=0*u.deg, lon=0*u.deg, height=0*u.m)
    jd = Time('2025-06-30', format='iso', scale='utc').jd
    result = sunrise(location, jd)
    assert result is not None, "Sunrise should occur at the equator"
    assert isinstance(result, Time), "Result should be an astropy Time object"


def test_sunset_equator_jun30_2025():
    """Test sunset at equator on June 30, 2025 - should return a valid time."""
    location = EarthLocation(lat=0*u.deg, lon=0*u.deg, height=0*u.m)
    jd = Time('2025-06-30', format='iso', scale='utc').jd
    result = sunset(location, jd)
    assert result is not None, "Sunset should occur at the equator"
    assert isinstance(result, Time), "Result should be an astropy Time object"


def test_sunrise_north_pole_jun30_2025():
    """Test sunrise at North Pole on June 30, 2025 - polar day, sun never sets (returns None)."""
    location = EarthLocation(lat=90*u.deg, lon=0*u.deg, height=0*u.m)
    jd = Time('2025-06-30', format='iso', scale='utc').jd
    result = sunrise(location, jd)
    assert result is None, "Sun should not rise at North Pole during polar day (already up)"


def test_sunset_north_pole_jun30_2025():
    """Test sunset at North Pole on June 30, 2025 - polar day, sun never sets (returns None)."""
    location = EarthLocation(lat=90*u.deg, lon=0*u.deg, height=0*u.m)
    jd = Time('2025-06-30', format='iso', scale='utc').jd
    result = sunset(location, jd)
    assert result is None, "Sun should not set at North Pole during polar day"


def test_sunrise_south_pole_jun30_2025():
    """Test sunrise at South Pole on June 30, 2025 - polar night, sun never rises (returns None)."""
    location = EarthLocation(lat=-90*u.deg, lon=0*u.deg, height=0*u.m)
    jd = Time('2025-06-30', format='iso', scale='utc').jd
    result = sunrise(location, jd)
    assert result is None, "Sun should not rise at South Pole during polar night"


def test_sunset_south_pole_jun30_2025():
    """Test sunset at South Pole on June 30, 2025 - polar night, sun never rises (returns None)."""
    location = EarthLocation(lat=-90*u.deg, lon=0*u.deg, height=0*u.m)
    jd = Time('2025-06-30', format='iso', scale='utc').jd
    result = sunset(location, jd)
    assert result is None, "Sun should not set at South Pole during polar night (never up)"


def test_daylight_hours_london_jun30_2025():
    """Test daylight hours in London on June 21, 2025 - summer solstice."""
    location = EarthLocation(lat=51.5*u.deg, lon=-0.127*u.deg, height=0*u.m)
    
    # Calculate June 21 (solstice date)
    jd_jun21 = Time('2025-06-21', format='iso', scale='utc').jd
    sunrise_jun21 = sunrise(location, jd_jun21)
    sunset_jun21 = sunset(location, jd_jun21)
    
    assert sunrise_jun21 is not None, "Sunrise should occur in London"
    assert sunset_jun21 is not None, "Sunset should occur in London"
    
    daylight_jun21 = (sunset_jun21 - sunrise_jun21).to(u.hour).value
    
    # London should have approximately 16.5-17 hours of daylight at summer solstice
    assert 16.0 < daylight_jun21 < 17.5, f"Expected ~16.5-17 hours of daylight, got {daylight_jun21:.2f} hours"
    
    # Calculate June 20 (day before)
    jd_jun20 = Time('2025-06-20', format='iso', scale='utc').jd
    sunrise_jun20 = sunrise(location, jd_jun20)
    sunset_jun20 = sunset(location, jd_jun20)
    
    assert sunrise_jun20 is not None, "Sunrise should occur in London"
    assert sunset_jun20 is not None, "Sunset should occur in London"
    
    daylight_jun20 = (sunset_jun20 - sunrise_jun20).to(u.hour).value
    
    # June 20 should have fewer hours of daylight than June 21 (solstice)
    assert daylight_jun20 < daylight_jun21, f"Day before solstice should have less daylight: {daylight_jun20:.2f} vs {daylight_jun21:.2f}"
    
    # Calculate June 22 (day after)
    jd_jun22 = Time('2025-06-22', format='iso', scale='utc').jd
    sunrise_jun22 = sunrise(location, jd_jun22)
    sunset_jun22 = sunset(location, jd_jun22)
    
    assert sunrise_jun22 is not None, "Sunrise should occur in London"
    assert sunset_jun22 is not None, "Sunset should occur in London"
    
    daylight_jun22 = (sunset_jun22 - sunrise_jun22).to(u.hour).value
    
    # June 22 should have fewer hours of daylight than June 21 (solstice)
    assert daylight_jun22 < daylight_jun21, f"Day after solstice should have less daylight: {daylight_jun22:.2f} vs {daylight_jun21:.2f}"
    
    print(f"London daylight on 2025-06-20: {daylight_jun20:.2f} hours")
    print(f"London daylight on 2025-06-21: {daylight_jun21:.2f} hours")
    print(f"London daylight on 2025-06-22: {daylight_jun22:.2f} hours")
    print(f"Jun20->Jun21 difference: {(daylight_jun21 - daylight_jun20) * 60:.2f} seconds")
    print(f"Jun21->Jun22 difference: {(daylight_jun21 - daylight_jun22) * 60:.2f} seconds")


def test_daylight_hours_london_mar21_2025_equinox():
    """Test daylight hours in London around March 21, 2025 - vernal equinox.
    
    At the equinox, daylight hours change rapidly (steepest part of the sine wave),
    unlike the solstice where changes are minimal.
    """
    location = EarthLocation(lat=51.5*u.deg, lon=-0.127*u.deg, height=0*u.m)
    
    # Calculate March 20, 21, 22 (around equinox)
    jd_mar20 = Time('2025-03-20', format='iso', scale='utc').jd
    sunrise_mar20 = sunrise(location, jd_mar20)
    sunset_mar20 = sunset(location, jd_mar20)
    daylight_mar20 = (sunset_mar20 - sunrise_mar20).to(u.hour).value
    
    jd_mar21 = Time('2025-03-21', format='iso', scale='utc').jd
    sunrise_mar21 = sunrise(location, jd_mar21)
    sunset_mar21 = sunset(location, jd_mar21)
    daylight_mar21 = (sunset_mar21 - sunrise_mar21).to(u.hour).value
    
    jd_mar22 = Time('2025-03-22', format='iso', scale='utc').jd
    sunrise_mar22 = sunrise(location, jd_mar22)
    sunset_mar22 = sunset(location, jd_mar22)
    daylight_mar22 = (sunset_mar22 - sunrise_mar22).to(u.hour).value
    
    # At equinox, daylight should be around 12 hours
    assert 11.5 < daylight_mar21 < 12.5, f"Equinox should have ~12 hours of daylight, got {daylight_mar21:.2f}"
    
    # Days should be getting longer (spring equinox)
    assert daylight_mar21 > daylight_mar20, "Days should be getting longer at vernal equinox"
    assert daylight_mar22 > daylight_mar21, "Days should be getting longer at vernal equinox"
    
    print(f"\nLondon daylight around vernal equinox (March 2025):")
    print(f"March 20: {daylight_mar20:.2f} hours")
    print(f"March 21: {daylight_mar21:.2f} hours (equinox)")
    print(f"March 22: {daylight_mar22:.2f} hours")
    print(f"Mar20->Mar21 difference: {(daylight_mar21 - daylight_mar20) * 60:.2f} seconds")
    print(f"Mar21->Mar22 difference: {(daylight_mar22 - daylight_mar21) * 60:.2f} seconds")
    print(f"\nCompare to solstice where change is ~0.01-0.09 seconds per day!")
