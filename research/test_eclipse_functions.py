#!/usr/bin/env python
"""
Quick test of enhanced eclipse research script functions.
Verifies imports and basic function execution.
"""

import sys
import os
from astropy.time import Time

# Import functions from the verification script in same directory
from verify_eclipse_approach import (
    check_eclipse_at_time,
    classify_lunar_eclipse_type,
    classify_solar_eclipse_type,
    get_sun_moon_parameters,
    calculate_earth_shadow_cone,
    calculate_moon_shadow_cone,
)

print("[OK] All functions imported successfully\n")

# Test 1: 2025-09-07 Lunar Eclipse
print("="*70)
print("TEST 1: 2025-09-07 18:11 UTC - Total Lunar Eclipse")
print("="*70)

time_lunar = Time('2025-09-07 18:11:00', scale='utc')
result_lunar = check_eclipse_at_time(time_lunar, is_lunar=True)

print(f"Is Eclipse: {result_lunar['is_eclipse']}")
print(f"Eclipse Type: {result_lunar['eclipse_type']}")
print(f"Umbral Magnitude: {result_lunar['umbral_magnitude']}")
print(f"Penumbral Magnitude: {result_lunar['penumbral_magnitude']}")

# Get detailed info
if result_lunar['is_eclipse']:
    params = get_sun_moon_parameters(time_lunar)
    shadow = calculate_earth_shadow_cone(time_lunar)
    print(f"\nShadow Geometry:")
    print(f"  Moon distance: {params['moon_dist_km']:.1f} km")
    print(f"  Umbral radius at Moon: {shadow['umbral_radius_km']:.1f} km ({shadow['umbral_radius_ang']:.4f} deg)")
    print(f"  Moon angular radius: {params['moon_ang_radius_deg']:.4f} deg")

test1_pass = result_lunar['is_eclipse'] and result_lunar['eclipse_type'] == 'TOTAL'
print(f"\nTest 1: {'PASS' if test1_pass else 'FAIL'}")

# Test 2: 2026-02-17 Solar Eclipse
print("\n" + "="*70)
print("TEST 2: 2026-02-17 14:29 UTC - Annular Solar Eclipse")
print("="*70)

time_solar = Time('2026-02-17 14:29:00', scale='utc')
result_solar = check_eclipse_at_time(time_solar, is_lunar=False)

print(f"Is Eclipse: {result_solar['is_eclipse']}")
print(f"Eclipse Type: {result_solar['eclipse_type']}")
print(f"Size Ratio: {result_solar['size_ratio']}")
print(f"Umbral Exists: {result_solar['umbral_exists']}")

# Get detailed info
if result_solar['is_eclipse']:
    params = get_sun_moon_parameters(time_solar)
    shadow = calculate_moon_shadow_cone(time_solar)
    print(f"\nShadow Geometry:")
    print(f"  Moon distance: {params['moon_dist_km']:.1f} km")
    print(f"  Moon's umbral radius at Earth: {shadow['umbral_radius_km']:.1f} km")
    print(f"  Umbral reaches Earth: {shadow['umbral_exists']}")
    print(f"  Moon/Sun size ratio: {result_solar['size_ratio']:.6f}")
    print(f"  Analysis: size_ratio={result_solar['size_ratio']:.4f} < 1.0 AND umbral_exists={result_solar['umbral_exists']}")
    print(f"  Result: ANNULAR (Moon too distant, umbral doesn't reach Earth)")

test2_pass = result_solar['is_eclipse'] and result_solar['eclipse_type'] == 'ANNULAR'
print(f"\nTest 2: {'PASS' if test2_pass else 'FAIL'}")

# Test 3: Demonstrate PARTIAL vs ANNULAR distinction
print("\n" + "="*70)
print("TEST 3: PARTIAL vs ANNULAR Classification")
print("="*70)
print("\nKey Difference (Solar Eclipses):")
print("  ANNULAR: Moon too far away")
print("    - umbral_exists = False (Moon's shadow doesn't reach Earth)")
print("    - size_ratio < 1.0 (Moon is smaller than Sun)")
print("    - Result: Ring of Sun visible around Moon silhouette")
print("\n  PARTIAL: Moon closer to Earth")
print("    - umbral_exists = True (Moon's shadow reaches Earth)")
print("    - size_ratio < 1.0 (Moon is still smaller than Sun)")
print("    - Result: Moon partially blocks Sun, no ring")
print("\n2026-02-17 Example:")
print(f"  umbral_exists = {result_solar['umbral_exists']} (Moon's shadow {['DOES reach', 'DOES NOT reach'][int(not result_solar['umbral_exists'])]} Earth)")
print(f"  size_ratio = {result_solar['size_ratio']:.4f} < 1.0 (Moon smaller than Sun)")
print(f"  Classification: {result_solar['eclipse_type']} eclipse")

# Summary
print("\n" + "="*70)
print("SUMMARY")
print("="*70)
all_pass = test1_pass and test2_pass
print(f"Overall: {'ALL TESTS PASSED' if all_pass else 'TESTS FAILED'}")
print(f"  Test 1 (Lunar): {'PASS' if test1_pass else 'FAIL'}")
print(f"  Test 2 (Solar): {'PASS' if test2_pass else 'FAIL'}")

exit(0 if all_pass else 1)
