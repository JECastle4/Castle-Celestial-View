#!/usr/bin/env python
"""Check which Venus phases are observed throughout 2026."""

from api.services.venus import calculate_venus_position
from api.models import ObservationDateTime, LocationModel

print("\nVenus Phases Observed Throughout 2026 (Monthly Analysis)")
print("="*80)
print(f"{'Month':<8} {'Date':<12} {'Illumination':<15} {'Phase':<12}")
print("="*80)

phases_observed = set()
for month in range(1, 13):
    result = calculate_venus_position(
        ObservationDateTime(date=f"2026-{month:02d}-15", time="12:00:00"),
        LocationModel(latitude=40.7128, longitude=-74.0060, elevation=0.0)
    )
    phase_name = result["phase_name"]
    illumination = result["illumination"]
    phases_observed.add(phase_name)
    
    month_name = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][month]
    print(f"{month_name:<8} 2026-{month:02d}-15  {illumination*100:6.1f}%         {phase_name:<12}")

print("="*80)
print(f"\nPhases observed in 2026: {sorted(phases_observed)}\n")
print("Phase Thresholds (based on illumination):")
print("  - New:     0-10%")
print("  - Crescent: 10-35%")
print("  - Quarter:  35-50%")
print("  - Gibbous:  50-90%")
print("  - Full:     90-100%\n")
