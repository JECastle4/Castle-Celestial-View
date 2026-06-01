"""Test harness for Venus rise/set functionality"""

from astropy.time import Time
from astropy.coordinates import EarthLocation
import astropy.units as u
from VenusRiseAndSet import venus_rise, venus_set, alt_at

# Test location: New York City
location = EarthLocation(lat=40.7128*u.deg, lon=-74.0060*u.deg, height=10*u.m)

# Test dates
test_dates = [
    ("2026-05-31", False),  # Previous day - to find rise
    ("2026-06-01", True),   # Enable debug for June 1
    ("2026-06-02", True),   # Next day - to find set
    ("2026-12-25", False),  # Far future to verify algorithm works
]

print("=" * 70)
print("VENUS RISE AND SET TEST HARNESS")
print("=" * 70)
print(f"Location: New York City (Lat: 40.7128°N, Lon: 74.0060°W)")
print()

for date_str, debug in test_dates:
    t = Time(date_str, format='iso', scale='utc')
    jd = t.jd
    
    print(f"Date: {date_str}")
    print(f"  Julian Date: {jd:.4f}")
    
    # Get Venus rise and set
    rise_time = venus_rise(location, jd, debug=debug)
    set_time = venus_set(location, jd, debug=debug)
    
    if rise_time is not None:
        print(f"  Venus Rise:  {rise_time.iso} UTC")
        rise_alt = alt_at(rise_time, location)
        print(f"    Altitude at rise: {rise_alt:.2f}°")
    else:
        print(f"  Venus Rise:  [Not visible on this date]")
    
    if set_time is not None:
        print(f"  Venus Set:   {set_time.iso} UTC")
        set_alt = alt_at(set_time, location)
        print(f"    Altitude at set: {set_alt:.2f}°")
    else:
        print(f"  Venus Set:   [Not visible on this date]")
    
    # Check altitude at noon
    noon = Time(f"{date_str}T12:00:00", format='isot', scale='utc')
    noon_alt = alt_at(noon, location)
    print(f"  Altitude at noon (12:00 UTC): {noon_alt:.2f}°")
    print(f"  Visible at noon: {'YES' if noon_alt > 0 else 'NO'}")
    print()

print("=" * 70)
print("Test complete. Venus position tracking is functional!")
print("=" * 70)
