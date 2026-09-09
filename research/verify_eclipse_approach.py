"""
Verification script for Issue 141: Eclipse Detection using Ecliptic Latitude Approach

Phase 1: Ecliptic latitude detection (verifies eclipse occurs)
Phase 2: Shadow cone geometry (verifies eclipse type: total/partial/annular)

This script validates the complete eclipse classification algorithm using:
1. Ecliptic latitude thresholds to detect eclipses
2. Shadow cone geometry to classify eclipse types
3. Magnitude calculations to verify type predictions

Known test eclipses:
- 2025-09-07 18:11 UTC: Total Lunar Eclipse
- 2026-02-17 14:29 UTC: Annular Solar Eclipse
"""

import numpy as np
from astropy.time import Time
from astropy.coordinates import get_body, get_sun, EarthLocation
from astropy.coordinates import BarycentricMeanEcliptic, GeocentricMeanEcliptic, GCRS
import astropy.units as u
import astropy.constants as const
from datetime import datetime, timedelta
import json


# Thresholds (in degrees)
LUNAR_ECLIPSE_THRESHOLD = 11.633  # 11° 38'
SOLAR_ECLIPSE_THRESHOLD = 17.417  # 17° 25'

# Physical constants (IAU standard values)
R_SUN_KM = const.R_sun.to(u.km).value        # ~695,700 km
R_MOON_KM = 1737.4                            # km (mean lunar radius)
R_EARTH_KM = 6371.0                           # km (mean radius)
AU_KM = 149597870.7                           # 1 AU in km

# Draconic year constants
DRACONIC_YEAR_DAYS = 6585.32
LUNAR_NODE_EPOCH = Time('2000-01-01')
LUNAR_NODE_EPOCH_LON = 280.47


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


# ============================================================================
# PHASE 2: SHADOW CONE GEOMETRY (for eclipse type classification)
# ============================================================================

def get_sun_moon_parameters(time_obj):
    """
    Get all Sun and Moon parameters in a single call.
    Minimizes astropy queries for efficiency.
    
    Args:
        time_obj: astropy Time object
        
    Returns:
        dict with all positional and angular data
    """
    location = EarthLocation.from_geodetic(0, 0)
    sun = get_sun(time_obj)
    moon = get_body('moon', time_obj, location=location)
    
    sun_dist_km = sun.distance.to(u.km).value
    moon_dist_km = moon.distance.to(u.km).value
    
    # Angular radii (radians → degrees)
    sun_ang_radius = np.degrees(np.arctan(R_SUN_KM / sun_dist_km))
    moon_ang_radius = np.degrees(np.arctan(R_MOON_KM / moon_dist_km))
    
    # Ecliptic coordinates
    sun_ecl = sun.transform_to(GeocentricMeanEcliptic(equinox=time_obj))
    moon_ecl = moon.transform_to(GeocentricMeanEcliptic(equinox=time_obj))
    
    # Angular separation
    separation = sun.separation(moon).degree
    
    return {
        'sun_dist_km': sun_dist_km,
        'moon_dist_km': moon_dist_km,
        'sun_ang_radius_deg': sun_ang_radius,
        'moon_ang_radius_deg': moon_ang_radius,
        'sun_ang_diam_deg': sun_ang_radius * 2,
        'moon_ang_diam_deg': moon_ang_radius * 2,
        'moon_ecl_lat_deg': moon_ecl.lat.degree,
        'moon_ecl_lon_deg': moon_ecl.lon.degree % 360,
        'angular_separation_deg': separation,
    }


def calculate_earth_shadow_cone(time_obj):
    """
    Calculate Earth's shadow cone at Moon distance.
    
    Uses conical geometry: Sun, Earth, Moon form a cone.
    Umbra = dark shadow (sun completely blocked)
    Penumbra = faint shadow (sun partially blocked)
    
    Formulas (Meeus algorithm):
        umbral_radius = R_earth - (R_sun * d_moon) / d_sun
        penumbral_radius = R_earth + (R_sun * d_moon) / d_sun
    
    Args:
        time_obj: astropy Time object (should be at full moon)
        
    Returns:
        dict with umbral and penumbral radii (km and angular)
    """
    params = get_sun_moon_parameters(time_obj)
    sun_dist = params['sun_dist_km']
    moon_dist = params['moon_dist_km']
    
    # Umbral radius at Moon distance (dark shadow)
    umbral_radius_km = R_EARTH_KM - (R_SUN_KM * moon_dist) / sun_dist
    umbral_radius_ang = np.degrees(np.arctan(umbral_radius_km / moon_dist))
    
    # Penumbral radius at Moon distance (faint shadow)
    penumbral_radius_km = R_EARTH_KM + (R_SUN_KM * moon_dist) / sun_dist
    penumbral_radius_ang = np.degrees(np.arctan(penumbral_radius_km / moon_dist))
    
    return {
        'umbral_radius_km': umbral_radius_km,
        'penumbral_radius_km': penumbral_radius_km,
        'umbral_radius_ang': umbral_radius_ang,
        'penumbral_radius_ang': penumbral_radius_ang,
    }


def calculate_moon_shadow_cone(time_obj):
    """
    Calculate Moon's shadow cone at Earth distance.
    
    Similar to Earth shadow, but Moon casts shadow on Earth.
    Critical: if umbral_radius_km < 0, umbra doesn't reach Earth → ANNULAR eclipse
    
    Formulas (Meeus algorithm):
        umbral_radius = R_moon - (R_sun * d_moon) / d_sun
        penumbral_radius = R_moon + (R_sun * d_moon) / d_sun
    
    Args:
        time_obj: astropy Time object (should be at new moon)
        
    Returns:
        dict with umbral/penumbral radii and umbral_exists flag
    """
    params = get_sun_moon_parameters(time_obj)
    sun_dist = params['sun_dist_km']
    moon_dist = params['moon_dist_km']
    
    # Umbral radius at Earth distance (dark shadow)
    umbral_radius_km = R_MOON_KM - (R_SUN_KM * moon_dist) / sun_dist
    umbral_radius_ang = np.degrees(np.arctan(abs(umbral_radius_km) / moon_dist)) if umbral_radius_km != 0 else 0
    
    # Penumbral radius at Earth distance (faint shadow)
    penumbral_radius_km = R_MOON_KM + (R_SUN_KM * moon_dist) / sun_dist
    penumbral_radius_ang = np.degrees(np.arctan(penumbral_radius_km / moon_dist))
    
    return {
        'umbral_radius_km': umbral_radius_km,
        'penumbral_radius_km': penumbral_radius_km,
        'umbral_radius_ang': umbral_radius_ang,
        'penumbral_radius_ang': penumbral_radius_ang,
        'umbral_exists': (umbral_radius_km > 0),
    }


def classify_lunar_eclipse_type(time_obj):
    """
    Classify lunar eclipse type using magnitude calculations.
    
    Magnitude = (shadow_radius - moon_radius) / moon_radius
    
    Classification:
        mag > 1.0  → TOTAL (moon fully in dark umbra)
        mag 0-1.0  → PARTIAL (moon partially in umbra)
        mag < 0, penumbral > 0 → PENUMBRAL (penumbra only)
    
    Args:
        time_obj: astropy Time object
        
    Returns:
        dict with eclipse type and magnitudes
    """
    params = get_sun_moon_parameters(time_obj)
    shadow = calculate_earth_shadow_cone(time_obj)
    
    moon_ang_radius = params['moon_ang_radius_deg']
    umbral_radius_ang = shadow['umbral_radius_ang']
    penumbral_radius_ang = shadow['penumbral_radius_ang']
    
    # Magnitude calculations (standard astronomical definition)
    umbral_mag = (umbral_radius_ang - moon_ang_radius) / moon_ang_radius if umbral_radius_ang > 0 else -1
    penumbral_mag = (penumbral_radius_ang - moon_ang_radius) / moon_ang_radius
    
    # Classification logic
    if umbral_mag > 1.0:
        eclipse_type = "TOTAL"
        description = "Moon fully enters dark umbra"
    elif umbral_mag > 0:
        eclipse_type = "PARTIAL"
        description = "Moon partially enters dark umbra"
    elif penumbral_mag > 0:
        eclipse_type = "PENUMBRAL"
        description = "Moon enters penumbra only (very faint)"
    else:
        eclipse_type = "NONE"
        description = "No eclipse"
    
    return {
        'eclipse_type': eclipse_type,
        'description': description,
        'umbral_magnitude': round(umbral_mag, 4),
        'penumbral_magnitude': round(penumbral_mag, 4),
    }


def classify_solar_eclipse_type(time_obj):
    """
    Classify solar eclipse type using size ratio and umbral reach.
    
    Key metric: size_ratio = moon_angular_diam / sun_angular_diam
    
    Classification:
        size_ratio ≥ 1.0 AND umbral exists → TOTAL (Moon covers Sun)
        size_ratio < 1.0 AND umbra DOESN'T exist → ANNULAR (Ring visible; Moon too far)
        size_ratio < 1.0 AND umbra EXISTS → PARTIAL (Moon smaller; some covering)
        0.95 < size_ratio < 1.05 AND umbral exists → HYBRID (Transitional cases)
    
    Key Distinction (ANNULAR vs PARTIAL):
        - ANNULAR: not umbral_exists AND size_ratio < 1.0 (Moon too distant to cast umbra)
        - PARTIAL: umbral_exists AND size_ratio < 1.0 (Moon closer, casts umbra, but still smaller)
    
    Args:
        time_obj: astropy Time object
        
    Returns:
        dict with eclipse type and characteristics
    """
    params = get_sun_moon_parameters(time_obj)
    shadow = calculate_moon_shadow_cone(time_obj)
    
    sun_ang_radius = params['sun_ang_radius_deg']
    moon_ang_radius = params['moon_ang_radius_deg']
    size_ratio = moon_ang_radius / sun_ang_radius
    umbral_exists = shadow['umbral_exists']
    
    # Classification logic (order matters for correct type determination)
    if umbral_exists and size_ratio >= 1.0:
        # Moon completely covers Sun and casts umbral shadow on Earth
        eclipse_type = "TOTAL"
    elif not umbral_exists and size_ratio < 1.0:
        # Moon too far away - umbral shadow doesn't reach Earth
        # But Moon still blocks some/all of Sun, creating a ring effect
        eclipse_type = "ANNULAR"
    elif umbral_exists and 0.95 < size_ratio < 1.05:
        # Moon size very close to Sun size, umbral reaches Earth
        # Near boundary - total in some locations, annular in others
        eclipse_type = "HYBRID"
    elif umbral_exists and size_ratio < 1.0:
        # Moon is smaller than Sun, but casts umbral shadow on Earth
        # Moon partially blocks Sun view
        eclipse_type = "PARTIAL"
    else:
        # Fallback: bodies don't properly overlap or edge cases
        eclipse_type = "PARTIAL"
    
    return {
        'eclipse_type': eclipse_type,
        'description': f"{eclipse_type} eclipse",
        'size_ratio': round(size_ratio, 6),
        'moon_ang_diam_deg': round(moon_ang_radius * 2, 6),
        'sun_ang_diam_deg': round(sun_ang_radius * 2, 6),
        'umbral_exists': umbral_exists,
    }


def check_eclipse_at_time(time_obj, is_lunar=True):
    """
    Complete eclipse analysis: detection (ecliptic latitude) + type classification (shadow geometry).
    
    Args:
        time_obj: astropy Time object
        is_lunar: bool, True for lunar eclipse check, False for solar
        
    Returns:
        dict with complete eclipse information
    """
    moon_lat = get_moon_ecliptic_latitude(time_obj)
    node_lon = get_lunar_node_position(time_obj)
    
    if is_lunar:
        threshold = LUNAR_ECLIPSE_THRESHOLD
        is_full = is_full_moon(time_obj)
        eclipse_occurs = (abs(moon_lat) < threshold) and is_full
        
        if eclipse_occurs:
            type_info = classify_lunar_eclipse_type(time_obj)
            eclipse_type = type_info['eclipse_type']
            magnitude = type_info['umbral_magnitude']
        else:
            eclipse_type = "NONE"
            magnitude = None
        
        return {
            'time': time_obj.iso,
            'is_eclipse': bool(eclipse_occurs),
            'eclipse_type': eclipse_type,
            'phase': 'full',
            'moon_ecl_lat_deg': round(moon_lat, 4),
            'node_ecl_lon_deg': round(node_lon, 2),
            'within_threshold': bool(abs(moon_lat) < threshold),
            'umbral_magnitude': magnitude,
            'penumbral_magnitude': type_info.get('penumbral_magnitude') if eclipse_occurs else None,
        }
    
    else:  # Solar eclipse
        threshold = SOLAR_ECLIPSE_THRESHOLD
        is_new = is_new_moon(time_obj)
        eclipse_occurs = (abs(moon_lat) < threshold) and is_new
        
        if eclipse_occurs:
            type_info = classify_solar_eclipse_type(time_obj)
            eclipse_type = type_info['eclipse_type']
            size_ratio = type_info['size_ratio']
        else:
            eclipse_type = "NONE"
            size_ratio = None
        
        return {
            'time': time_obj.iso,
            'is_eclipse': bool(eclipse_occurs),
            'eclipse_type': eclipse_type,
            'phase': 'new',
            'moon_ecl_lat_deg': round(moon_lat, 4),
            'node_ecl_lon_deg': round(node_lon, 2),
            'within_threshold': bool(abs(moon_lat) < threshold),
            'size_ratio': size_ratio,
            'umbral_exists': type_info.get('umbral_exists') if eclipse_occurs else None,
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
    print("TEST 1: 2025-09-07 18:11 UTC - Expected: TOTAL Lunar Eclipse")
    print("="*70)
    
    time_2025_lunar = Time('2025-09-07 18:11:00', scale='utc')
    result_lunar = check_eclipse_at_time(time_2025_lunar, is_lunar=True)
    print(json.dumps(result_lunar, indent=2))
    
    # Detailed classification
    if result_lunar['is_eclipse']:
        detailed_lunar = classify_lunar_eclipse_type(time_2025_lunar)
        print("\nDetailed Lunar Eclipse Classification:")
        print(json.dumps(detailed_lunar, indent=2))
        shadow = calculate_earth_shadow_cone(time_2025_lunar)
        params = get_sun_moon_parameters(time_2025_lunar)
        print("\nShadow Geometry:")
        print(f"  Moon distance: {params['moon_dist_km']:.1f} km")
        print(f"  Sun distance: {params['sun_dist_km']:.1f} km")
        print(f"  Umbral radius at Moon: {shadow['umbral_radius_km']:.1f} km ({shadow['umbral_radius_ang']:.4f}°)")
        print(f"  Penumbral radius at Moon: {shadow['penumbral_radius_km']:.1f} km ({shadow['penumbral_radius_ang']:.4f}°)")
        print(f"  Moon angular radius: {params['moon_ang_radius_deg']:.4f}°")
    
    test1_pass = (
        result_lunar["is_eclipse"] and
        result_lunar["eclipse_type"] == "TOTAL"
    )
    results["verification_tests"].append({
        "name": "2025-09-07 Lunar Eclipse",
        "expected": "TOTAL",
        "detected": result_lunar["eclipse_type"],
        "passed": test1_pass
    })
    print(f"\nTest 1 Result: {'✓ PASS' if test1_pass else '✗ FAIL'}")
    
    # Test 2: 2026-02-17 Solar Eclipse
    print("\n" + "="*70)
    print("TEST 2: 2026-02-17 14:29 UTC - Expected: ANNULAR Solar Eclipse")
    print("="*70)
    
    time_2026_solar = Time('2026-02-17 14:29:00', scale='utc')
    result_solar = check_eclipse_at_time(time_2026_solar, is_lunar=False)
    print(json.dumps(result_solar, indent=2))
    
    # Detailed classification
    if result_solar['is_eclipse']:
        detailed_solar = classify_solar_eclipse_type(time_2026_solar)
        print("\nDetailed Solar Eclipse Classification:")
        print(json.dumps(detailed_solar, indent=2))
        shadow = calculate_moon_shadow_cone(time_2026_solar)
        params = get_sun_moon_parameters(time_2026_solar)
        print("\nShadow Geometry:")
        print(f"  Moon distance: {params['moon_dist_km']:.1f} km")
        print(f"  Sun distance: {params['sun_dist_km']:.1f} km")
        print(f"  Moon's umbral radius at Earth: {shadow['umbral_radius_km']:.1f} km")
        print(f"  Umbral reaches Earth: {shadow['umbral_exists']}")
        print(f"  Size ratio (Moon/Sun): {detailed_solar['size_ratio']}")
        print(f"  Moon angular diameter: {detailed_solar['moon_ang_diam_deg']:.6f}°")
        print(f"  Sun angular diameter: {detailed_solar['sun_ang_diam_deg']:.6f}°")
    
    test2_pass = (
        result_solar["is_eclipse"] and
        result_solar["eclipse_type"] == "ANNULAR"
    )
    results["verification_tests"].append({
        "name": "2026-02-17 Solar Eclipse",
        "expected": "ANNULAR",
        "detected": result_solar["eclipse_type"],
        "passed": test2_pass
    })
    print(f"\nTest 2 Result: {'✓ PASS' if test2_pass else '✗ FAIL'}")
    
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
        if result_lunar["is_eclipse"]:
            eclipses.append(result_lunar)
        
        # Check for solar eclipse
        result_solar = check_eclipse_at_time(current, is_lunar=False)
        if result_solar["is_eclipse"]:
            eclipses.append(result_solar)
        
        current += timedelta(days=sample_interval_days)
    
    # Sort by time
    eclipses.sort(key=lambda x: x["time"])
    
    return eclipses


def main():
    """Run full verification suite."""
    print("\n" + "="*70)
    print("ECLIPSE DETECTION AND CLASSIFICATION VERIFICATION")
    print("Issue 141: Complete Shadow Cone Geometry Implementation")
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
        phase_type = eclipse['phase'].upper()
        eclipse_type = eclipse['eclipse_type']
        magnitude = eclipse.get('umbral_magnitude') or eclipse.get('size_ratio', 'N/A')
        print(f"  {eclipse['time']} - {phase_type:5s} moon: {eclipse_type:10s} (magnitude: {magnitude})")
    
    # Final status
    print("\n" + "="*70)
    print(f"VERIFICATION STATUS: {verification_results['status'].upper()}")
    print("="*70)
    
    return verification_results["status"] == "passed"


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
