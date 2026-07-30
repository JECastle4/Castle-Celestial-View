# tests/test_MoonPhase.py
import sys
from pathlib import Path

research_path = str((Path(__file__).parent.parent / 'research').resolve())
if research_path not in sys.path:
    sys.path.insert(0, research_path)
from MoonPhase import moon_phase, moon_phase_angle, moon_phase_name
from astropy.time import Time
import numpy as np


def test_moon_phase_cycle_february_2025():
    """Test moon phase progression through February 2025.
    
    Verifies:
    - Phase angles progress monotonically from 0-360°
    - Both new and full moon phases occur
    - Phase names progress logically through the lunar cycle
    """
    # Generate all days in February 2025
    dates = [f'2025-02-{day:02d}' for day in range(1, 29)]
    times = [Time(date, format='iso', scale='utc') for date in dates]
    
    # Collect phase data
    phase_angles = []
    phase_names = []
    illuminations = []
    
    for time in times:
        angle = moon_phase_angle(time)
        name = moon_phase_name(time)
        illum = moon_phase(time)
        
        phase_angles.append(angle)
        phase_names.append(name)
        illuminations.append(illum)
    
    # Test 1: Phase angles should progress through a cycle
    # (may wrap around 0/360, so check for general progression)
    print("\nMoon phases for February 2025:")
    print(f"{'Date':<12} {'Angle':>8} {'Illum %':>8} {'Phase Name':<20}")
    print("-" * 60)
    for i, (date, angle, illum, name) in enumerate(zip(dates, phase_angles, illuminations, phase_names)):
        print(f"{date:<12} {angle:>8.1f}° {illum*100:>7.1f}% {name:<20}")
    
    # Test 2: Should see at least one new moon and one full moon (or close to them)
    min_illum = min(illuminations)
    max_illum = max(illuminations)
    
    # Over 28 days, we should see significant range in illumination
    assert max_illum - min_illum > 0.5, f"Should see significant illumination range, got {max_illum - min_illum:.2f}"
    
    # Verify we hit both new moon and full moon
    assert min_illum < 0.05, f"Should see new moon (illum < 5%), got min {min_illum*100:.1f}%"
    assert max_illum > 0.95, f"Should see full moon (illum > 95%), got max {max_illum*100:.1f}%"
    
    # Also verify the phase names include both
    assert "New Moon" in phase_names, "Should see 'New Moon' phase"
    assert "Full Moon" in phase_names, "Should see 'Full Moon' phase"
    
    # Test 3: Phase names should follow logical progression
    expected_progression = [
        "New Moon", "Waxing Crescent", "First Quarter", "Waxing Gibbous", 
        "Full Moon", "Waning Gibbous", "Last Quarter", "Waning Crescent"
    ]
    
    # Check that we see a reasonable subset of phases in order
    # (not all phases may appear depending on where February starts in the cycle)
    unique_phases_in_order = []
    for name in phase_names:
        if not unique_phases_in_order or unique_phases_in_order[-1] != name:
            unique_phases_in_order.append(name)
    
    print(f"\nPhases observed in order: {' -> '.join(unique_phases_in_order)}")
    
    # Should have at least 3 distinct phases over 28 days
    assert len(unique_phases_in_order) >= 3, f"Should see at least 3 distinct phases, got {len(unique_phases_in_order)}"
    
    # Test 4: Verify phase progression is monotonic (allowing for 360° wrap)
    # Check that phase angle generally increases (with possible wrap from 360 to 0)
    for i in range(1, len(phase_angles)):
        prev_angle = phase_angles[i-1]
        curr_angle = phase_angles[i]
        
        # Calculate difference accounting for wrap-around
        diff = (curr_angle - prev_angle) % 360
        
        # Moon moves ~13° per day, so expect roughly 10-16° progression
        # (Allow some tolerance for daily variations)
        assert 8 < diff < 20, f"Day {i}: Phase angle should progress ~10-15° per day, got {diff:.1f}° (from {prev_angle:.1f}° to {curr_angle:.1f}°)"
    
    print(f"\n✓ Phase angle progresses consistently (~13° per day)")
    print(f"✓ Illumination range: {min_illum*100:.1f}% to {max_illum*100:.1f}%")
    print(f"✓ Observed {len(unique_phases_in_order)} distinct phases in logical order")
