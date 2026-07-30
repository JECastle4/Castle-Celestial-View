"""
Research script to find when all outer planets (Jupiter, Saturn, Uranus, Neptune)
are simultaneously visible above the horizon, for use in e2e zoom-button tests.
"""
from api.models import TimeRange, ObservationDateTime, LocationModel
from api.services.batch_earth_observations import calculate_batch_earth_observations


def research_outer_planets_visibility(date_str: str):
    """Check a given date for all four outer planets visible at once"""

    # Use New York as observer location (consistent with existing inner-planet e2e research)
    location = LocationModel(
        latitude=40.7128,
        longitude=-74.0060,
        elevation=10
    )

    # Full 24-hour day in 30-minute intervals = 48 frames
    time_range = TimeRange(
        start=ObservationDateTime(date=date_str, time="00:00:00"),
        end=ObservationDateTime(date=date_str, time="23:30:00"),
        frame_count=48
    )

    print("=" * 80)
    print(f"{date_str} - OUTER PLANET VISIBILITY RESEARCH")
    print("=" * 80)
    print(f"Location: 40.7128 N, -74.0060 W")
    print(f"Time resolution: 30-minute intervals (48 frames)")
    print()

    frames = list(calculate_batch_earth_observations(time_range, location))

    all_visible_frames = []

    for i, frame in enumerate(frames):
        minutes = (i * 30) % 1440
        hours = minutes // 60
        mins = minutes % 60
        time_str = f"{hours:02d}:{mins:02d}:00"

        jup_visible = frame.get('jupiter', {}).get('is_visible', False)
        sat_visible = frame.get('saturn', {}).get('is_visible', False)
        ura_visible = frame.get('uranus', {}).get('is_visible', False)
        nep_visible = frame.get('neptune', {}).get('is_visible', False)

        all_visible = jup_visible and sat_visible and ura_visible and nep_visible

        jup_alt = frame.get('jupiter', {}).get('altitude', 0)
        sat_alt = frame.get('saturn', {}).get('altitude', 0)
        ura_alt = frame.get('uranus', {}).get('altitude', 0)
        nep_alt = frame.get('neptune', {}).get('altitude', 0)

        status = "✓ ALL VISIBLE" if all_visible else ""

        print(f"[{time_str}] Frame {i:2d}: "
              f"Jup({jup_alt:6.1f}°) Sat({sat_alt:6.1f}°) "
              f"Ura({ura_alt:6.1f}°) Nep({nep_alt:6.1f}°) {status}")

        if all_visible:
            all_visible_frames.append({
                'frame_index': i,
                'time': time_str,
                'jupiter_altitude': jup_alt,
                'saturn_altitude': sat_alt,
                'uranus_altitude': ura_alt,
                'neptune_altitude': nep_alt,
            })

    print()
    print("=" * 80)
    if all_visible_frames:
        print(f"Found {len(all_visible_frames)} frame(s) with all outer planets visible:")
        for f in all_visible_frames:
            print(f"  Frame {f['frame_index']:2d} [{f['time']}]: "
                  f"Jup({f['jupiter_altitude']:.1f}°) Sat({f['saturn_altitude']:.1f}°) "
                  f"Ura({f['uranus_altitude']:.1f}°) Nep({f['neptune_altitude']:.1f}°)")
    else:
        print("No frame found with all four outer planets simultaneously visible.")
    print("=" * 80)

    return all_visible_frames


if __name__ == "__main__":
    import sys
    date_arg = sys.argv[1] if len(sys.argv) > 1 else "2026-01-01"
    research_outer_planets_visibility(date_arg)
