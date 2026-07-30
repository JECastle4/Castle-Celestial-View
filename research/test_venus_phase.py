"""Test Venus phase and visibility calculation."""
from astropy.coordinates import EarthLocation
from astropy.time import Time
import astropy.units as u
from api.services.venus import calculate_venus_position
from api.models import ObservationDateTime, LocationModel

# Test location: NYC
latitude = 40.7128
longitude = -74.0060
elevation = 10.0

# Test cases covering different Venus phases throughout 2026
test_cases = [
    ("2026-01-15", "12:00:00", "Morning star (waxing crescent)"),
    ("2026-03-01", "12:00:00", "Morning star (near gibbous)"),
    ("2026-05-01", "12:00:00", "Approaching inferior conjunction"),
    ("2026-06-01", "12:00:00", "Evening star emerging (thin crescent)"),
    ("2026-07-15", "20:00:00", "Evening star (gibbous)"),
    ("2026-09-01", "20:00:00", "Evening star (waning gibbous)"),
    ("2026-10-01", "12:00:00", "Near superior conjunction"),
    ("2026-12-25", "12:00:00", "Morning star returning (gibbous)"),
]

print("=" * 140)
print("VENUS PHASE & VISIBILITY CALCULATION TEST")
print("=" * 140)
print()

for date_str, time_str, description in test_cases:
    try:
        result = calculate_venus_position(
            ObservationDateTime(date=date_str, time=time_str),
            LocationModel(latitude=latitude, longitude=longitude, elevation=elevation)
        )
        
        print(f"Date: {date_str} {time_str} UTC — {description}")
        print(f"  Position: Alt={result['altitude']:6.2f}° Az={result['azimuth']:6.2f}°")
        print(f"  Visibility: is_visible={str(result['is_visible']):5s} | naked_eye_visible={str(result['naked_eye_visible']):5s} | sun_separation={result['sun_separation']:6.2f}°")
        print(f"  Phase: {result['phase_name']:10s} | Illumination={result['illumination']*100:5.1f}% | Phase Angle={result['phase_angle']:6.1f}°")
        print()
    except Exception as e:
        print(f"ERROR on {date_str} {time_str}: {e}")
        print()

print("=" * 140)
print("TEST COMPLETE")
print("=" * 140)
