"""Test Venus rise/set at different altitude thresholds to match timeanddate.com"""
from astropy.coordinates import EarthLocation
from astropy.time import Time
import astropy.units as u
from VenusRiseAndSet import venus_rise, venus_set

# New York City
location = EarthLocation(lat=40.7128*u.deg, lon=-74.0060*u.deg, height=10*u.m)

# June 1, 2026
jd = Time("2026-06-01 12:00:00", scale='utc').jd

# Test different altitude thresholds
altitudes_to_test = [
    0 * u.deg,           # Geometric horizon (our current default)
    -0.833 * u.deg,      # Standard atmospheric refraction
    -0.5 * u.deg,        # Half degree
    -1.0 * u.deg,        # 1 degree
]

print("="*70)
print("VENUS RISE/SET AT DIFFERENT ALTITUDE THRESHOLDS - June 1, 2026")
print("="*70)
print()

for alt in altitudes_to_test:
    print(f"Target Altitude: {alt.value:+.3f}°")
    print("-" * 70)
    
    rise_utc = venus_rise(location, jd, target_altitude=alt)
    set_utc = venus_set(location, jd, target_altitude=alt)
    
    if rise_utc:
        # Convert UTC to EDT (UTC-4)
        rise_edt_hour = rise_utc.datetime.hour - 4
        rise_edt_day = rise_utc.datetime.day
        if rise_edt_hour < 0:
            rise_edt_hour += 24
            rise_edt_day -= 1
        rise_edt_str = f"June {rise_edt_day} {rise_edt_hour:02d}:{rise_utc.datetime.minute:02d} EDT"
        print(f"  Rise: {rise_utc.iso} UTC = {rise_edt_str}")
    else:
        print(f"  Rise: None")
    
    if set_utc:
        # Convert UTC to EDT (UTC-4)
        set_edt_hour = set_utc.datetime.hour - 4
        set_edt_day = set_utc.datetime.day
        if set_edt_hour < 0:
            set_edt_hour += 24
            set_edt_day -= 1
        set_edt_str = f"June {set_edt_day} {set_edt_hour:02d}:{set_utc.datetime.minute:02d} EDT"
        print(f"  Set:  {set_utc.iso} UTC = {set_edt_str}")
    else:
        print(f"  Set: None")
    
    print()

print("="*70)
print("NOTE: Timeanddate reports 23:02 on June 1 (presumably local EDT)")
print("      which would be 03:02 UTC on June 2")
print("="*70)
