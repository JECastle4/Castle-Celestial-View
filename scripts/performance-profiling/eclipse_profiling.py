#!/usr/bin/env python3
"""
Eclipse Event Performance Profiling - Phase 3 Optimization

Measures performance of each stage in astronomical event detection:
1. find_new_full_moons() - Moon phase crossing detection (should be fast)
2. Pre-filter (node distance) - Quick rejection of non-eclipse events (should be fast)
3. Eclipse classification - Determine eclipse type (can be slow)
4. Contact time calculations - Most expensive operation (expected bottleneck)

Goal: Verify that non-eclipse events process quickly, and identify where
expensive eclipse calculations dominate the latency.
"""

import time
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent to path for API imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from astropy.time import Time
import astropy.units as u

from api.services.astronomical_events import (
    find_new_full_moons,
    build_astronomical_event,
    validate_date_range,
)
from api.services.eclipse_detection import (
    get_moon_ecliptic_coords,
    node_distance_deg,
    find_greatest_eclipse_time,
    classify_lunar_eclipse_type,
    classify_solar_eclipse_type,
    get_sun_ecliptic_longitude,
)
from api.services.eclipse_contact_times import (
    calculate_lunar_contact_times,
    calculate_solar_contact_times,
)


def profile_moon_detection(start_date_str, end_date_str):
    """Profile find_new_full_moons() performance."""
    print(f"\n{'='*70}")
    print(f"PROFILE: New/Full Moon Detection")
    print(f"{'='*70}")
    print(f"Date range: {start_date_str} to {end_date_str}")

    start_time_str, end_time_str = validate_date_range(start_date_str, end_date_str)
    date_range_days = (end_time_str - start_time_str).to(u.day).value

    start_perf = time.perf_counter()
    raw_events = find_new_full_moons(start_time_str, end_time_str)
    elapsed = time.perf_counter() - start_perf

    new_moons = [e for e in raw_events if e['phase'] == 'new']
    full_moons = [e for e in raw_events if e['phase'] == 'full']

    print(f"\nResults:")
    print(f"  Total events: {len(raw_events)} (New: {len(new_moons)}, Full: {len(full_moons)})")
    print(f"  Date range: {date_range_days:.1f} days")
    print(f"  Response time: {elapsed:.2f}s")
    print(f"  Per-event overhead: {elapsed/max(1, len(raw_events))*1000:.1f}ms")

    return raw_events, elapsed


def profile_prefilter_only(raw_events):
    """Profile just the pre-filter (node distance check) for all events."""
    print(f"\n{'='*70}")
    print(f"PROFILE: Pre-filter (Node Distance) for All Events")
    print(f"{'='*70}")

    eclipse_candidates = []
    non_eclipse = []

    start_perf = time.perf_counter()
    for event in raw_events:
        time_obj = event['time']
        phase = event['phase']
        is_lunar = phase == 'full'

        # Get moon ecliptic coordinates (very fast)
        moon_lat, moon_lon = get_moon_ecliptic_coords(time_obj)

        # Check if eclipse is geometrically possible (fast pre-filter)
        if is_lunar:
            node_dist = node_distance_deg(moon_lon, time_obj)
            within_threshold = node_dist <= 12.25  # LUNAR_ECLIPSE_NODE_LIMIT_DEG
        else:
            sun_lon = get_sun_ecliptic_longitude(time_obj)
            node_dist = node_distance_deg(sun_lon, time_obj)
            within_threshold = node_dist <= 18.5167  # SOLAR_ECLIPSE_NODE_LIMIT_DEG

        if within_threshold:
            eclipse_candidates.append((event, moon_lat, moon_lon, is_lunar))
        else:
            non_eclipse.append(event)

    elapsed = time.perf_counter() - start_perf

    print(f"\nResults:")
    print(f"  Total events: {len(raw_events)}")
    print(f"  Eclipse candidates: {len(eclipse_candidates)}")
    print(f"  Non-eclipse (filtered out): {len(non_eclipse)}")
    print(f"  Total time: {elapsed:.2f}s")
    print(f"  Per-event overhead: {elapsed/max(1, len(raw_events))*1000:.1f}ms")
    print(f"  Per-candidate overhead: {elapsed/max(1, len(eclipse_candidates))*1000:.1f}ms (if any)")

    return eclipse_candidates, elapsed


def profile_greatest_eclipse_time(eclipse_candidates):
    """Profile find_greatest_eclipse_time() for candidates."""
    print(f"\n{'='*70}")
    print(f"PROFILE: Greatest Eclipse Time Search")
    print(f"{'='*70}")

    elapsed_times = {'lunar': [], 'solar': []}

    if not eclipse_candidates:
        print("No eclipse candidates to profile.")
        return elapsed_times, 0.0

    times_by_phase = {'full': [], 'new': []}

    for event, _, _, _ in eclipse_candidates:
        phase = event['phase']
        times_by_phase[phase].append(event['time'])

    # Profile lunar eclipses
    if times_by_phase['full']:
        print(f"\nLunar eclipses ({len(times_by_phase['full'])} events):")
        lunar_times = []
        for time_obj in times_by_phase['full']:
            start_perf = time.perf_counter()
            greatest = find_greatest_eclipse_time(time_obj, is_lunar=True)
            elapsed = time.perf_counter() - start_perf
            lunar_times.append(elapsed)
            elapsed_times['lunar'].append(elapsed)

        avg_lunar = sum(lunar_times) / len(lunar_times)
        max_lunar = max(lunar_times)
        print(f"  Average per-event: {avg_lunar*1000:.1f}ms")
        print(f"  Max per-event: {max_lunar*1000:.1f}ms")
        print(f"  Total: {sum(lunar_times):.2f}s")

    # Profile solar eclipses
    if times_by_phase['new']:
        print(f"\nSolar eclipses ({len(times_by_phase['new'])} events):")
        solar_times = []
        for time_obj in times_by_phase['new']:
            start_perf = time.perf_counter()
            greatest = find_greatest_eclipse_time(time_obj, is_lunar=False)
            elapsed = time.perf_counter() - start_perf
            solar_times.append(elapsed)
            elapsed_times['solar'].append(elapsed)

        avg_solar = sum(solar_times) / len(solar_times)
        max_solar = max(solar_times)
        print(f"  Average per-event: {avg_solar*1000:.1f}ms")
        print(f"  Max per-event: {max_solar*1000:.1f}ms")
        print(f"  Total: {sum(solar_times):.2f}s")

    total_elapsed = sum(elapsed_times['lunar']) + sum(elapsed_times['solar'])
    return elapsed_times, total_elapsed


def profile_eclipse_classification(eclipse_candidates, elapsed_times):
    """Profile eclipse type classification."""
    print(f"\n{'='*70}")
    print(f"PROFILE: Eclipse Type Classification")
    print(f"{'='*70}")

    lunar_events = [e for e in eclipse_candidates if e[3]]  # is_lunar
    solar_events = [e for e in eclipse_candidates if not e[3]]

    classification_times = {'lunar': [], 'solar': []}

    # Profile lunar eclipses
    if lunar_events:
        print(f"\nLunar eclipses ({len(lunar_events)} events):")
        for event, _, _, _ in lunar_events:
            greatest_time = find_greatest_eclipse_time(event['time'], is_lunar=True)
            start_perf = time.perf_counter()
            result = classify_lunar_eclipse_type(greatest_time)
            elapsed = time.perf_counter() - start_perf
            classification_times['lunar'].append(elapsed)

        avg_lunar = sum(classification_times['lunar']) / len(classification_times['lunar'])
        max_lunar = max(classification_times['lunar'])
        print(f"  Average per-event: {avg_lunar*1000:.1f}ms")
        print(f"  Max per-event: {max_lunar*1000:.1f}ms")
        print(f"  Total: {sum(classification_times['lunar']):.2f}s")

    # Profile solar eclipses
    if solar_events:
        print(f"\nSolar eclipses ({len(solar_events)} events):")
        for event, _, _, _ in solar_events:
            greatest_time = find_greatest_eclipse_time(event['time'], is_lunar=False)
            start_perf = time.perf_counter()
            result = classify_solar_eclipse_type(greatest_time)
            elapsed = time.perf_counter() - start_perf
            classification_times['solar'].append(elapsed)

        avg_solar = sum(classification_times['solar']) / len(classification_times['solar'])
        max_solar = max(classification_times['solar'])
        print(f"  Average per-event: {avg_solar*1000:.1f}ms")
        print(f"  Max per-event: {max_solar*1000:.1f}ms")
        print(f"  Total: {sum(classification_times['solar']):.2f}s")

    total_elapsed = sum(classification_times['lunar']) + sum(classification_times['solar'])
    return classification_times, total_elapsed


def profile_contact_times(eclipse_candidates):
    """Profile contact time calculations."""
    print(f"\n{'='*70}")
    print(f"PROFILE: Contact Time Calculations")
    print(f"{'='*70}")

    lunar_events = [e for e in eclipse_candidates if e[3]]
    solar_events = [e for e in eclipse_candidates if not e[3]]

    contact_times = {'lunar': [], 'solar': []}

    # Profile lunar eclipses
    if lunar_events:
        print(f"\nLunar eclipses ({len(lunar_events)} events):")
        for event, _, _, _ in lunar_events:
            greatest_time = find_greatest_eclipse_time(event['time'], is_lunar=True)
            start_perf = time.perf_counter()
            result = calculate_lunar_contact_times(greatest_time)
            elapsed = time.perf_counter() - start_perf
            contact_times['lunar'].append(elapsed)

        avg_lunar = sum(contact_times['lunar']) / len(contact_times['lunar'])
        max_lunar = max(contact_times['lunar'])
        print(f"  Average per-event: {avg_lunar*1000:.1f}ms")
        print(f"  Max per-event: {max_lunar*1000:.1f}ms")
        print(f"  Total: {sum(contact_times['lunar']):.2f}s")

    # Profile solar eclipses
    if solar_events:
        print(f"\nSolar eclipses ({len(solar_events)} events):")
        for event, _, _, _ in solar_events:
            greatest_time = find_greatest_eclipse_time(event['time'], is_lunar=False)
            start_perf = time.perf_counter()
            result = calculate_solar_contact_times(greatest_time)
            elapsed = time.perf_counter() - start_perf
            contact_times['solar'].append(elapsed)

        avg_solar = sum(contact_times['solar']) / len(contact_times['solar'])
        max_solar = max(contact_times['solar'])
        print(f"  Average per-event: {avg_solar*1000:.1f}ms")
        print(f"  Max per-event: {max_solar*1000:.1f}ms")
        print(f"  Total: {sum(contact_times['solar']):.2f}s")

    total_elapsed = sum(contact_times['lunar']) + sum(contact_times['solar'])
    return contact_times, total_elapsed


def main():
    """Run eclipse performance profiling."""
    print("\n" + "="*70)
    print("ECLIPSE EVENT PERFORMANCE PROFILING")
    print("="*70)
    print(f"Started at: {datetime.now().isoformat()}")

    # Test with 10-year range (same as benchmark)
    end_date = datetime(2026, 12, 31)
    start_date = end_date - timedelta(days=365*10)
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    # Stage 1: Find new/full moons
    raw_events, moon_detection_time = profile_moon_detection(start_date_str, end_date_str)

    # Stage 2: Pre-filter (node distance check)
    eclipse_candidates, prefilter_time = profile_prefilter_only(raw_events)

    # Stage 3: Greatest eclipse time (if any candidates)
    if eclipse_candidates:
        greatest_time_results, greatest_time_elapsed = profile_greatest_eclipse_time(eclipse_candidates)

        # Stage 4: Eclipse classification
        classification_results, classification_elapsed = profile_eclipse_classification(
            eclipse_candidates, greatest_time_results
        )

        # Stage 5: Contact times
        contact_times_results, contact_times_elapsed = profile_contact_times(eclipse_candidates)

        # Summary
        print(f"\n{'='*70}")
        print("SUMMARY")
        print(f"{'='*70}")
        print(f"\nStage breakdown (10-year range, {len(raw_events)} total events):")
        print(f"  1. Moon detection:              {moon_detection_time:7.2f}s ({moon_detection_time*100//(moon_detection_time+prefilter_time+greatest_time_elapsed+classification_elapsed+contact_times_elapsed)+1:.0f}%)")
        print(f"  2. Pre-filter (all events):     {prefilter_time:7.2f}s ({prefilter_time*100//(moon_detection_time+prefilter_time+greatest_time_elapsed+classification_elapsed+contact_times_elapsed)+1:.0f}%)")
        print(f"  3. Greatest eclipse time:       {greatest_time_elapsed:7.2f}s ({greatest_time_elapsed*100//(moon_detection_time+prefilter_time+greatest_time_elapsed+classification_elapsed+contact_times_elapsed)+1:.0f}%)")
        print(f"  4. Eclipse classification:      {classification_elapsed:7.2f}s ({classification_elapsed*100//(moon_detection_time+prefilter_time+greatest_time_elapsed+classification_elapsed+contact_times_elapsed)+1:.0f}%)")
        print(f"  5. Contact times:               {contact_times_elapsed:7.2f}s ({contact_times_elapsed*100//(moon_detection_time+prefilter_time+greatest_time_elapsed+classification_elapsed+contact_times_elapsed)+1:.0f}%)")
        print(f"  {'─'*50}")
        total = moon_detection_time + prefilter_time + greatest_time_elapsed + classification_elapsed + contact_times_elapsed
        print(f"  TOTAL:                          {total:7.2f}s")

        print(f"\nEclipse events (candidates for expensive calculations):")
        print(f"  Lunar: {len([e for e in eclipse_candidates if e[3]])}")
        print(f"  Solar: {len([e for e in eclipse_candidates if not e[3]])}")
        print(f"  Non-eclipse (filtered): {len(raw_events) - len(eclipse_candidates)}")

        print(f"\nKey insights:")
        if greatest_time_elapsed > contact_times_elapsed:
            print(f"  * Greatest eclipse time search dominates (~{greatest_time_elapsed/total*100:.0f}%)")
            print(f"  * Recommendation: Cache greatest_time results or use coarser search")
        else:
            print(f"  * Contact time calculations dominate (~{contact_times_elapsed/total*100:.0f}%)")
            print(f"  * Recommendation: Skip contact times for non-display use cases")

        if prefilter_time < 2.0:
            print(f"  * Pre-filter is efficient ({prefilter_time:.2f}s for {len(raw_events)} events)")
        else:
            print(f"  * Pre-filter could be optimized (vectorize eclipse candidate checks)")

    else:
        print("\nNo eclipse candidates found in date range.")

    print(f"\nCompleted at: {datetime.now().isoformat()}")
    print("="*70)


if __name__ == "__main__":
    main()
