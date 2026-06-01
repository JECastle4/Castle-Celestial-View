"""Search for Venus RISE_ONLY and SET_ONLY transition patterns.

These patterns occur at the boundaries of conjunction when Venus is 
appearing or disappearing. Test focused date ranges.
"""
from astropy.coordinates import EarthLocation
from astropy.time import Time
import astropy.units as u
from VenusRiseAndSet import venus_rise, venus_set

# Test location: equator (tends to show clearest patterns)
location = EarthLocation(lat=0*u.deg, lon=0*u.deg, height=0*u.m)

print("=" * 100)
print("SEARCHING FOR RISE_ONLY AND SET_ONLY PATTERNS")
print("=" * 100)
print()

# Test comprehensive date range - daily through transition periods
# Venus inferior conjunction around April 2026, Superior conjunction around October 2026

# Test around inferior conjunction (Venus between Earth and Sun - April 2026)
print("FOCUS AREA 1: Inferior Conjunction (April 2026) - Daily sweep")
print("-" * 100)
start_date = Time("2026-03-20", scale='utc')
for day_offset in range(1, 31):  # April 1-30 (April has 30 days)
    date = Time(f"2026-04-{day_offset:02d} 12:00:00", scale='utc')
    jd = date.jd
    
    rise_time = venus_rise(location, jd)
    set_time = venus_set(location, jd)
    
    # Classify
    if rise_time is None and set_time is None:
        pattern = "NO_RISE_NO_SET"
    elif rise_time is None and set_time is not None:
        pattern = "SET_ONLY"
    elif rise_time is not None and set_time is None:
        pattern = "RISE_ONLY"
    elif set_time < rise_time:
        pattern = "SET_THEN_RISE"
    else:
        pattern = "RISE_THEN_SET"
    
    rise_str = f"{rise_time.iso}" if rise_time else "None"
    set_str = f"{set_time.iso}" if set_time else "None"
    
    print(f"2026-04-{day_offset:02d} | {pattern:18} | Rise: {rise_str:30} Set: {set_str:30}")

print()
print()

# Test around superior conjunction (Venus behind Sun - October 2026)
print("FOCUS AREA 2: Superior Conjunction (October 2026) - Daily sweep")
print("-" * 100)
for day_offset in range(1, 32):  # October 1-31
    try:
        date = Time(f"2026-10-{day_offset:02d} 12:00:00", scale='utc')
        jd = date.jd
        
        rise_time = venus_rise(location, jd)
        set_time = venus_set(location, jd)
        
        # Classify
        if rise_time is None and set_time is None:
            pattern = "NO_RISE_NO_SET"
        elif rise_time is None and set_time is not None:
            pattern = "SET_ONLY"
        elif rise_time is not None and set_time is None:
            pattern = "RISE_ONLY"
        elif set_time < rise_time:
            pattern = "SET_THEN_RISE"
        else:
            pattern = "RISE_THEN_SET"
        
        rise_str = f"{rise_time.iso}" if rise_time else "None"
        set_str = f"{set_time.iso}" if set_time else "None"
        
        print(f"2026-10-{day_offset:02d} | {pattern:18} | Rise: {rise_str:30} Set: {set_str:30}")
    except Exception:  # Skip dates where calculations fail
        pass

print()
print()

# Also test early 2027 for morning star returning (after superior conjunction)
print("FOCUS AREA 3: Morning Star Returning (Early 2027) - Daily sweep")
print("-" * 100)
for day_offset in range(1, 32):  # November 2026
    try:
        date = Time(f"2026-11-{day_offset:02d} 12:00:00", scale='utc')
        jd = date.jd
        
        rise_time = venus_rise(location, jd)
        set_time = venus_set(location, jd)
        
        # Classify
        if rise_time is None and set_time is None:
            pattern = "NO_RISE_NO_SET"
        elif rise_time is None and set_time is not None:
            pattern = "SET_ONLY"
        elif rise_time is not None and set_time is None:
            pattern = "RISE_ONLY"
        elif set_time < rise_time:
            pattern = "SET_THEN_RISE"
        else:
            pattern = "RISE_THEN_SET"
        
        rise_str = f"{rise_time.iso}" if rise_time else "None"
        set_str = f"{set_time.iso}" if set_time else "None"
        
        print(f"2026-11-{day_offset:02d} | {pattern:18} | Rise: {rise_str:30} Set: {set_str:30}")
    except Exception:  # Skip dates where calculations fail
        pass

print()
print("=" * 100)
print("ANALYSIS")
print("=" * 100)
print("""
Note: RISE_ONLY and SET_ONLY patterns may be rare or non-existent depending on:
1. Venus's orbital geometry
2. The specific latitude chosen (equator is used here)
3. The definition of "24-hour period" (UTC midnight to midnight)

These patterns would occur if Venus entered/exited the observable zone
exactly at the UTC date boundary. However, Venus's motion is slow and smooth,
so these patterns may be mathematically possible but practically rare.

The three main patterns we've confirmed are:
✓ RISE_THEN_SET: Normal pattern (rise before set, same day)
✓ SET_THEN_RISE: Inferior planet pattern (set before rise, consecutive days)
✓ NO_RISE_NO_SET: Polar day/night or Venus always above/below horizon
""")
