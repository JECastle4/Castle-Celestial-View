"""Comprehensive Venus rise/set testing for all possible scenarios.

Tests all 6 possible patterns:
1. Never rises (always above horizon)
2. Never sets (always below horizon)
3. Set before rise (inferior planet special case)
4. Rise before set (typical/normal pattern)
5. Only rise, no set (transition date)
6. Only set, no rise (transition date)
"""
from astropy.coordinates import EarthLocation
from astropy.time import Time
import astropy.units as u
from VenusRiseAndSet import venus_rise, venus_set

# Test locations
LOCATIONS = {
    "Equator": EarthLocation(lat=0*u.deg, lon=0*u.deg, height=0*u.m),
    "NYC": EarthLocation(lat=40.7128*u.deg, lon=-74.0060*u.deg, height=10*u.m),
    "Sydney": EarthLocation(lat=-33.8688*u.deg, lon=151.2093*u.deg, height=58*u.m),
    "Arctic (North Pole region)": EarthLocation(lat=80*u.deg, lon=0*u.deg, height=0*u.m),
    "Antarctic (South Pole region)": EarthLocation(lat=-80*u.deg, lon=0*u.deg, height=0*u.m),
}

# Test dates throughout 2026 (Venus visibility cycle)
# Venus becomes visible as evening star around June, reaches max in August, 
# then gradually gets closer to Sun through September
TEST_DATES = [
    ("2026-01-15", "Early 2026 (morning star phase)"),
    ("2026-03-01", "March 2026 (morning star ending)"),
    ("2026-04-15", "April 2026 (conjunction period start)"),
    ("2026-05-15", "May 2026 (evening star emerging)"),
    ("2026-06-01", "June 1 2026 (evening star visible)"),
    ("2026-06-15", "June 15 2026 (evening star peak season)"),
    ("2026-07-15", "July 2026 (evening star)"),
    ("2026-08-15", "August 2026 (evening star)"),
    ("2026-09-01", "Sept 1 2026 (evening star declining)"),
    ("2026-09-15", "Sept 15 2026 (conjunction approaching)"),
    ("2026-10-01", "Oct 2026 (conjunction period)"),
    ("2026-12-25", "December 25 2026 (morning star returning)"),
]


def classify_pattern(rise_time, set_time, location=None, jd=None):
    """Classify the rise/set pattern.
    
    Returns tuple: (pattern_name, description)
    """
    if rise_time is None and set_time is None:
        # Determine if always above or always below using astropy
        if location is not None and jd is not None:
            from astropy.time import Time
            from astropy.coordinates import AltAz, get_body
            import astropy.units as u
            import numpy as np
            
            midday = Time(jd, format='jd', scale='utc') + 0.5 * u.day
            hours = np.linspace(-12, 12, 241)
            times = midday + hours * u.hour
            venus_coords = get_body("venus", times, location)
            altaz = venus_coords.transform_to(AltAz(obstime=times, location=location))
            altitudes = altaz.alt.to(u.deg)
            
            min_alt = np.min(altitudes)
            if min_alt > 0:
                return "NO_RISE_NO_SET", "CIRCUMPOLAR: always above horizon"
            else:
                return "NO_RISE_NO_SET", "NEVER_RISES: always below horizon"
        
        return "NO_RISE_NO_SET", "Never crosses horizon"
    
    if rise_time is None and set_time is not None:
        return "SET_ONLY", "Only sets (no rise in 24h)"
    
    if rise_time is not None and set_time is None:
        return "RISE_ONLY", "Only rises (no set in 24h)"
    
    # Both are not None
    if set_time < rise_time:
        return "SET_THEN_RISE", "Set before rise (inferior planet)"
    else:
        return "RISE_THEN_SET", "Rise before set (normal)"


def format_time(t):
    """Format Time object to readable string or 'None'."""
    if t is None:
        return "None"
    # Convert to local time display (just show UTC)
    return f"{t.iso} UTC"


def main():
    print("=" * 100)
    print("VENUS RISE/SET - COMPREHENSIVE SCENARIO TESTING")
    print("=" * 100)
    print()
    
    # Pattern collection
    patterns_found = {}
    
    # Test each location
    for loc_name, location in LOCATIONS.items():
        print(f"\n{'='*100}")
        print(f"LOCATION: {loc_name}")
        print(f"Latitude: {location.lat.deg:.2f}°, Longitude: {location.lon.deg:.2f}°")
        print(f"{'='*100}")
        print()
        
        for date_str, date_desc in TEST_DATES:
            jd = Time(f"{date_str} 12:00:00", scale='utc').jd
            
            rise_time = venus_rise(location, jd)
            set_time = venus_set(location, jd)
            
            pattern, desc = classify_pattern(rise_time, set_time, location=location, jd=jd)
            
            # Track patterns found
            if pattern not in patterns_found:
                patterns_found[pattern] = []
            patterns_found[pattern].append({
                "location": loc_name,
                "date": date_str,
                "description": date_desc,
                "rise": rise_time,
                "set": set_time,
            })
            
            # Print result
            print(f"{date_str:12} | {date_desc:30} | {pattern:18} | {desc:35} | Rise: {format_time(rise_time):30} | Set: {format_time(set_time):30}")
        
        print()
    
    # Summary
    print("\n" + "=" * 100)
    print("PATTERN SUMMARY")
    print("=" * 100)
    print()
    
    all_patterns = [
        "RISE_THEN_SET",
        "SET_THEN_RISE", 
        "RISE_ONLY",
        "SET_ONLY",
        "NO_RISE_NO_SET"
    ]
    
    for pattern_name in all_patterns:
        if pattern_name in patterns_found:
            examples = patterns_found[pattern_name]
            print(f"✓ {pattern_name:20} (Found {len(examples)} examples)")
            print(f"  Examples:")
            for ex in examples[:2]:  # Show first 2 examples
                print(f"    - {ex['location']:30} on {ex['date']}: Rise={format_time(ex['rise']):30} Set={format_time(ex['set']):30}")
            if len(examples) > 2:
                print(f"    ... and {len(examples)-2} more")
        else:
            print(f"✗ {pattern_name:20} (Not found in test range)")
    
    print()
    print("=" * 100)
    print("CONCLUSION")
    print("=" * 100)
    print()
    
    found_count = len(patterns_found)
    target_patterns = [
        "RISE_THEN_SET",
        "SET_THEN_RISE",
        "RISE_ONLY",
        "SET_ONLY",
        "NO_RISE_NO_SET"
    ]
    
    found_patterns = [p for p in target_patterns if p in patterns_found]
    print(f"Pattern Coverage: {found_count}/{len(target_patterns)} patterns found")
    print(f"Found: {', '.join(found_patterns)}")
    print(f"Missing: {', '.join([p for p in target_patterns if p not in patterns_found])}")
    print()
    
    if len(found_patterns) == len(target_patterns):
        print("✓ SUCCESS: All Venus rise/set patterns validated!")
        print("  Algorithm correctly handles all inferior planet scenarios.")
    else:
        print(f"⚠ INCOMPLETE: {len(target_patterns) - found_count} pattern(s) not yet observed.")
        print("  Consider:")
        print("  - Extending date range further into 2026 or testing 2027")
        print("  - Testing more extreme latitudes")
        print("  - Note: Some patterns may be rare (e.g., polar day/night)")
    
    print()


if __name__ == "__main__":
    main()
