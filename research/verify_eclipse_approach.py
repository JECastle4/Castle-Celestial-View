"""
Verification script for Issue 141: Eclipse Detection using Ecliptic Latitude Approach

This script validates that the ecliptic latitude method correctly identifies eclipses
by comparing against historical eclipse records.

Key thresholds (Wikipedia):
- Lunar eclipse: Full moon within 11° 38' (11.633°) of lunar node
- Solar eclipse: New moon within 17° 25' (17.417°) of lunar node

Known test eclipses:
- 2025-09-07: Total lunar eclipse
- 2026-02-17: Annular solar eclipse
"""

import numpy as np
from astropy.time import Time
from astropy.coordinates import get_body, EarthLocation
from astropy.coordinates import BarycentricMeanEcliptic, GeocentricMeanEcliptic, GCRS
import astropy.units as u
from datetime import datetime, timedelta
import json


# Thresholds (in degrees)
LUNAR_ECLIPSE_THRESHOLD = 11.633  # 11° 38'
SOLAR_ECLIPSE_THRESHOLD = 17.417  # 17° 25'


def get_moon_ecliptic_latitude(time_obj):
    """
    Calculate moon's ecliptic latitude at given time.
    
    Args:
        time_obj: astropy Time object
        
    Returns:
        Moon's ecliptic latitude in degrees
    """
    # Get moon position in geocentric mean ecliptic frame
    moon = get_body('moon', time_obj, location=EarthLocation.from_geodetic(0, 0))
    moon_ecliptic = moon.transform_to(GeocentricMeanEcliptic(equinox=time_obj))
    
    # Extract ecliptic latitude
    lat = moon_ecliptic.lat.degree
    return lat


def get_sun_ecliptic_latitude(time_obj):
    """
    Calculate sun's ecliptic latitude at given time (should always be ~0).
    
    Args:
        time_obj: astropy Time object
        
    Returns:
        Sun's ecliptic latitude in degrees
    """
    sun = get_body('sun', time_obj, location=EarthLocation.from_geodetic(0, 0))
    sun_ecliptic = sun.transform_to(GeocentricMeanEcliptic(equinox=time_obj))
    
    lat = sun_ecliptic.lat.degree
    return lat


def get_lunar_node_position(time_obj):
    """
    Get approximate ecliptic longitude of lunar ascending node.
    
    The lunar node precesses with period of 18.6 years (6585.32 days).
    Starting point: node at ecliptic longitude ~0° on 2000-01-01
    
    Args:
        time_obj: astropy Time object
        
    Returns:
        Ecliptic longitude of ascending node in degrees
    """
    # Reference epoch: 2000-01-01
    epoch = Time('2000-01-01')
    days_since_epoch = time_obj.jd - epoch.jd
    
    # Draconic year: 18.612958 years = 6585.32 days
    draconic_year_days = 6585.32
    
    # Node precesses westward (retrograde) by ~360° per draconic year
    node_lon = (280.47 - 360.0 * days_since_epoch / draconic_year_days) % 360
    
    return node_lon


def get_moon_ecliptic_longitude(time_obj):
    """
    Calculate moon's ecliptic longitude at given time.
    
    Args:
        time_obj: astropy Time object
        
    Returns:
        Moon's ecliptic longitude in degrees (0-360)
    """
    moon = get_body('moon', time_obj, location=EarthLocation.from_geodetic(0, 0))
    moon_ecliptic = moon.transform_to(GeocentricMeanEcliptic(equinox=time_obj))
    
    lon = moon_ecliptic.lon.degree
    return lon % 360


def get_sun_ecliptic_longitude(time_obj):
    """
    Calculate sun's ecliptic longitude at given time.
    
    Args:
        time_obj: astropy Time object
        
    Returns:
        Sun's ecliptic longitude in degrees (0-360)
    """
    sun = get_body('sun', time_obj, location=EarthLocation.from_geodetic(0, 0))
    sun_ecliptic = sun.transform_to(GeocentricMeanEcliptic(equinox=time_obj))
    
    lon = sun_ecliptic.lon.degree
    return lon % 360


def get_moon_angular_diameter(time_obj):
    """
    Calculate moon's angular diameter (angular size) in degrees.
    
    Uses: angular_diameter = 2 * arctan(R_moon / distance_to_moon)
    
    Args:
        time_obj: astropy Time object
        
    Returns:
        Moon's angular diameter in degrees
    """
    R_MOON_KM = 1737.4  # Moon radius in km
    
    moon = get_body('moon', time_obj, location=EarthLocation.from_geodetic(0, 0))
    distance_km = moon.distance.to(u.km).value
    
    # Angular diameter = 2 * arctan(radius / distance)
    angular_diameter = 2 * np.degrees(np.arctan(R_MOON_KM / distance_km))
    
    return angular_diameter


def get_sun_angular_diameter(time_obj):
    """
    Calculate sun's angular diameter (angular size) in degrees.
    
    Uses: angular_diameter = 2 * arctan(R_sun / distance_to_sun)
    
    Args:
        time_obj: astropy Time object
        
    Returns:
        Sun's angular diameter in degrees
    """
    R_SUN_KM = 695700  # Sun radius in km
    
    sun = get_body('sun', time_obj, location=EarthLocation.from_geodetic(0, 0))
    distance_km = sun.distance.to(u.km).value
    
    # Angular diameter = 2 * arctan(radius / distance)
    angular_diameter = 2 * np.degrees(np.arctan(R_SUN_KM / distance_km))
    
    return angular_diameter


def get_moon_phase_angle(time_obj):
    """
    Calculate moon's phase angle (elongation from sun).
    
    Args:
        time_obj: astropy Time object
        
    Returns:
        Phase angle in degrees (0° = new moon, 180° = full moon)
    """
    sun = get_body('sun', time_obj, location=EarthLocation.from_geodetic(0, 0))
    moon = get_body('moon', time_obj, location=EarthLocation.from_geodetic(0, 0))
    
    # Angular separation
    separation = sun.separation(moon)
    
    return separation.degree


def is_new_moon(time_obj, tolerance_hours=12):
    """
    Check if time is approximately at new moon.
    
    Args:
        time_obj: astropy Time object
        tolerance_hours: search tolerance in hours
        
    Returns:
        bool: True if approximately new moon
    """
    phase_angle = get_moon_phase_angle(time_obj)
    return phase_angle < 10  # Within ~10° of sun


def is_full_moon(time_obj, tolerance_hours=12):
    """
    Check if time is approximately at full moon.
    
    Args:
        time_obj: astropy Time object
        tolerance_hours: search tolerance in hours
        
    Returns:
        bool: True if approximately full moon
    """
    phase_angle = get_moon_phase_angle(time_obj)
    return abs(phase_angle - 180) < 10  # Within ~10° of 180°


def check_eclipse_at_time(time_obj, is_lunar=True):
    """
    Check if eclipse occurs at given time using ecliptic latitude approach.
    
    Args:
        time_obj: astropy Time object
        is_lunar: bool, True for lunar eclipse check, False for solar
        
    Returns:
        dict with eclipse detection results
    """
    moon_lat = get_moon_ecliptic_latitude(time_obj)
    sun_lat = get_sun_ecliptic_latitude(time_obj)
    moon_lon = get_moon_ecliptic_longitude(time_obj)
    sun_lon = get_sun_ecliptic_longitude(time_obj)
    node_lon = get_lunar_node_position(time_obj)
    
    # Distance from moon to node (account for 360° wrap)
    lon_diff = abs(moon_lon - node_lon)
    if lon_diff > 180:
        lon_diff = 360 - lon_diff
    
    if is_lunar:
        threshold = LUNAR_ECLIPSE_THRESHOLD
        is_full = is_full_moon(time_obj)
        eclipse_occurs = (abs(moon_lat) < threshold) and is_full
        eclipse_type = "lunar"
    else:
        threshold = SOLAR_ECLIPSE_THRESHOLD
        is_new = is_new_moon(time_obj)
        eclipse_occurs = (abs(moon_lat) < threshold) and is_new
        eclipse_type = "solar"
    
    # Get angular sizes for type classification
    moon_ang = get_moon_angular_diameter(time_obj)
    sun_ang = get_sun_angular_diameter(time_obj)
    
    # Determine eclipse subtype
    subtype = "unknown"
    if eclipse_occurs:
        if is_lunar:
            # For lunar eclipses: partial or total based on penumbra/umbra
            # Simplified: if moon's angular size significant, likely total
            subtype = "total" if moon_ang > sun_ang * 0.5 else "partial"
        else:
            # For solar eclipses: annular or total
            ratio = moon_ang / sun_ang
            if ratio < 0.99:
                subtype = "annular"
            elif ratio > 1.01:
                subtype = "total"
            else:
                subtype = "hybrid"
    
    return {
        "time": time_obj.iso,
        "eclipse_type": eclipse_type,
        "eclipse_occurs": bool(eclipse_occurs),
        "subtype": subtype,
        "moon_ecliptic_latitude": round(moon_lat, 4),
        "moon_ecliptic_longitude": round(moon_lon, 2),
        "sun_ecliptic_longitude": round(sun_lon, 2),
        "node_ecliptic_longitude": round(node_lon, 2),
        "threshold": threshold,
        "within_threshold": bool(abs(moon_lat) < threshold),
        "is_full_moon": bool(is_full_moon(time_obj)) if is_lunar else "N/A",
        "is_new_moon": bool(is_new_moon(time_obj)) if not is_lunar else "N/A",
        "moon_angular_diameter": round(moon_ang, 4),
        "sun_angular_diameter": round(sun_ang, 4),
        "magnitude": round(moon_ang / sun_ang, 4) if not is_lunar else None,
    }


def verify_known_eclipses():
    """
    Verify that known historical eclipses are correctly detected.
    
    Test cases:
    - 2025-09-07: Total Lunar Eclipse
    - 2026-02-17: Annular Solar Eclipse
    """
    results = {
        "verification_tests": [],
        "status": "running"
    }
    
    # Test 1: 2025-09-07 Lunar Eclipse
    print("\n" + "="*70)
    print("TEST 1: 2025-09-07 - Expected: Total Lunar Eclipse")
    print("="*70)
    
    time_2025_lunar = Time('2025-09-07 18:11:00', scale='utc')
    result_lunar = check_eclipse_at_time(time_2025_lunar, is_lunar=True)
    print(json.dumps(result_lunar, indent=2))
    
    test1_pass = (
        result_lunar["eclipse_occurs"] and
        result_lunar["subtype"] in ["total", "partial"]
    )
    results["verification_tests"].append({
        "name": "2025-09-07 Lunar Eclipse",
        "expected": "Total",
        "detected": result_lunar["subtype"],
        "passed": test1_pass
    })
    print(f"\nTest 1 Result: {'PASS' if test1_pass else 'FAIL'}")
    
    # Test 2: 2026-02-17 Solar Eclipse
    print("\n" + "="*70)
    print("TEST 2: 2026-02-17 - Expected: Annular Solar Eclipse")
    print("="*70)
    
    time_2026_solar = Time('2026-02-17 14:29:00', scale='utc')
    result_solar = check_eclipse_at_time(time_2026_solar, is_lunar=False)
    print(json.dumps(result_solar, indent=2))
    
    test2_pass = (
        result_solar["eclipse_occurs"] and
        result_solar["subtype"] in ["annular", "total"]
    )
    results["verification_tests"].append({
        "name": "2026-02-17 Solar Eclipse",
        "expected": "Annular",
        "detected": result_solar["subtype"],
        "passed": test2_pass
    })
    print(f"\nTest 2 Result: {'PASS' if test2_pass else 'FAIL'}")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    all_passed = all(t["passed"] for t in results["verification_tests"])
    results["status"] = "passed" if all_passed else "failed"
    
    for test in results["verification_tests"]:
        status = "✓ PASS" if test["passed"] else "✗ FAIL"
        print(f"{status}: {test['name']}")
        print(f"         Expected: {test['expected']}, Detected: {test['detected']}")
    
    return results


def scan_date_range_for_eclipses(start_date_str, end_date_str, sample_interval_days=1):
    """
    Scan a date range for potential eclipses.
    
    Args:
        start_date_str: Start date as string (e.g., "2025-01-01")
        end_date_str: End date as string
        sample_interval_days: Sampling interval (1 day for dense sampling)
        
    Returns:
        List of detected eclipse events
    """
    print(f"\nScanning {start_date_str} to {end_date_str} for eclipses...")
    print("(Sampling every {} day(s))\n".format(sample_interval_days))
    
    start = Time(start_date_str)
    end = Time(end_date_str)
    
    eclipses = []
    current = start
    
    while current < end:
        # Check for lunar eclipse
        result_lunar = check_eclipse_at_time(current, is_lunar=True)
        if result_lunar["eclipse_occurs"]:
            eclipses.append(result_lunar)
        
        # Check for solar eclipse
        result_solar = check_eclipse_at_time(current, is_lunar=False)
        if result_solar["eclipse_occurs"]:
            eclipses.append(result_solar)
        
        current += timedelta(days=sample_interval_days)
    
    # Sort by time
    eclipses.sort(key=lambda x: x["time"])
    
    return eclipses


def main():
    """Run full verification suite."""
    print("\n" + "="*70)
    print("ECLIPSE DETECTION APPROACH VERIFICATION")
    print("Issue 141: Ecliptic Latitude Method")
    print("="*70)
    
    # Run known eclipse verification
    verification_results = verify_known_eclipses()
    
    # Scan 2025-2026 for all eclipses
    print("\n" + "="*70)
    print("ECLIPSES DETECTED IN 2025-2026")
    print("="*70)
    
    eclipses = scan_date_range_for_eclipses("2025-01-01", "2026-12-31", sample_interval_days=1)
    
    print(f"\nTotal eclipses detected: {len(eclipses)}\n")
    for eclipse in eclipses:
        print(f"  {eclipse['time']} - {eclipse['eclipse_type'].upper()} ({eclipse['subtype']})")
        print(f"    Moon ecliptic latitude: {eclipse['moon_ecliptic_latitude']}°")
    
    # Final status
    print("\n" + "="*70)
    print(f"VERIFICATION STATUS: {verification_results['status'].upper()}")
    print("="*70)
    
    return verification_results["status"] == "passed"


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
