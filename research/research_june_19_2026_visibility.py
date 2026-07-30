"""
Research script to find when all celestial bodies are visible on June 19, 2026
"""
from api.models import TimeRange, ObservationDateTime, LocationModel
from api.services.batch_earth_observations import calculate_batch_earth_observations


def research_june_19_visibility():
    """Check June 19, 2026 for all bodies visible at once"""
    
    # Use New York as observer location (UTC-4 in June, so roughly centered timezone)
    location = LocationModel(
        latitude=40.7128,
        longitude=-74.0060,
        elevation=10
    )
    
    # Full 24-hour day in 30-minute intervals = 48 frames
    time_range = TimeRange(
        start=ObservationDateTime(date="2026-06-19", time="00:00:00"),
        end=ObservationDateTime(date="2026-06-19", time="23:30:00"),
        frame_count=48
    )
    
    print("=" * 80)
    print("JUNE 19, 2026 - CELESTIAL BODY VISIBILITY RESEARCH")
    print("=" * 80)
    # Format latitude with proper N/S designation (negative = S, positive = N)
    lat_dir = 'S' if location.latitude < 0 else 'N'
    lat_value = abs(location.latitude)
    # Format longitude with proper E/W designation (negative = W, positive = E)
    lon_dir = 'W' if location.longitude < 0 else 'E'
    lon_value = abs(location.longitude)
    print(f"Location: {lat_value}° {lat_dir}, {lon_value}° {lon_dir}")
    print(f"Date: 2026-06-19")
    print(f"Time resolution: 30-minute intervals (48 frames)")
    print()
    
    frames = list(calculate_batch_earth_observations(time_range, location))
    
    all_visible_frames = []
    
    for i, frame in enumerate(frames):
        # Calculate time of this frame
        frame_num = i
        minutes = (frame_num * 30) % 1440
        hours = minutes // 60
        mins = minutes % 60
        time_str = f"{hours:02d}:{mins:02d}:00"
        
        # Check visibility (frames are dicts, not objects)
        sun_visible = frame.get('sun', {}).get('is_visible', False)
        moon_visible = frame.get('moon', {}).get('is_visible', False)
        mercury_visible = frame.get('mercury', {}).get('is_visible', False)
        venus_visible = frame.get('venus', {}).get('is_visible', False)
        mars_visible = frame.get('mars', {}).get('is_visible', False)
        
        all_visible = sun_visible and moon_visible and mercury_visible and venus_visible and mars_visible
        
        # Get altitudes for context
        sun_alt = frame.get('sun', {}).get('altitude', 0)
        moon_alt = frame.get('moon', {}).get('altitude', 0)
        merc_alt = frame.get('mercury', {}).get('altitude', 0)
        venus_alt = frame.get('venus', {}).get('altitude', 0)
        mars_alt = frame.get('mars', {}).get('altitude', 0)
        
        status = "✓ ALL VISIBLE" if all_visible else ""
        
        print(f"[{time_str}] Frame {i:2d}: "
              f"Sun({sun_alt:6.1f}°) Moon({moon_alt:6.1f}°) "
              f"Merc({merc_alt:6.1f}°) Ven({venus_alt:6.1f}°) "
              f"Mars({mars_alt:6.1f}°) {status}")
        
        if all_visible:
            all_visible_frames.append({
                'frame_index': i,
                'time': time_str,
                'sun_altitude': sun_alt,
                'moon_altitude': moon_alt,
                'mercury_altitude': merc_alt,
                'venus_altitude': venus_alt,
                'mars_altitude': mars_alt,
            })
    
    print()
    print("=" * 80)
    if all_visible_frames:
        print(f"✓ FOUND {len(all_visible_frames)} frame(s) where ALL bodies are visible:")
        print("=" * 80)
        for frame_data in all_visible_frames:
            print(f"\n  Time: {frame_data['time']} (Frame index: {frame_data['frame_index']})")
            print(f"    Sun altitude:     {frame_data['sun_altitude']:6.2f}°")
            print(f"    Moon altitude:    {frame_data['moon_altitude']:6.2f}°")
            print(f"    Mercury altitude: {frame_data['mercury_altitude']:6.2f}°")
            print(f"    Venus altitude:   {frame_data['venus_altitude']:6.2f}°")
            print(f"    Mars altitude:    {frame_data['mars_altitude']:6.2f}°")
        
        best_frame = max(all_visible_frames, 
                         key=lambda f: min(f['sun_altitude'], f['moon_altitude'], 
                                          f['mercury_altitude'], f['venus_altitude'], 
                                          f['mars_altitude']))
        print()
        print(f"RECOMMENDED FOR TEST: Frame {best_frame['frame_index']} at {best_frame['time']}")
        print(f"(Highest minimum altitude: {min(best_frame['sun_altitude'], best_frame['moon_altitude'], best_frame['mercury_altitude'], best_frame['venus_altitude'], best_frame['mars_altitude']):.2f}°)")
    else:
        print("✗ NO frames found where all bodies are simultaneously visible on June 19, 2026")
        print("Consider widening the date range or checking alternative dates.")
    print("=" * 80)


if __name__ == "__main__":
    research_june_19_visibility()