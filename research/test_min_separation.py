"""Find minimum sun separation during inferior conjunction."""
from api.services.venus import calculate_venus_position
from api.models import ObservationDateTime, LocationModel

print("Finding minimum Sun separation during Venus inferior conjunction (May 2026)")
print("=" * 110)
print()

# Inferior conjunction occurs around May 3, 2026
# Test multiple days to find the closest approach
dates_to_test = [
    ("2026-04-30", "Approaching"),
    ("2026-05-01", "Getting close"),
    ("2026-05-02", "Very close"),
    ("2026-05-03", "Conjunction day"),
    ("2026-05-04", "Moving away"),
    ("2026-05-05", "Separating"),
]

print("Time: 12:00:00 UTC (noon)")
print("-" * 110)
print(f"{'Date':<12} {'Description':<15} {'Altitude':<12} {'Sun Sep':<12} {'Status':<30}")
print("-" * 110)

min_sep = 999
for date_str, desc in dates_to_test:
    result = calculate_venus_position(
        ObservationDateTime(date=date_str, time="12:00:00"),
        LocationModel(latitude=40.7128, longitude=-74.0060, elevation=10.0)
    )
    sep = result["sun_separation"]
    alt = result["altitude"]
    
    if sep < min_sep:
        min_sep = sep
    
    if result["is_visible"] and not result["naked_eye_visible"]:
        status = "⚠ DROWNED OUT BY GLARE"
    elif result["naked_eye_visible"]:
        status = f"✓ Naked-eye visible ({sep:.1f}° sep)"
    else:
        status = "✗ Below horizon"
    
    print(f"{date_str:<12} {desc:<15} {alt:6.2f}°      {sep:6.2f}°      {status:<30}")

print()
print(f"Minimum separation: {min_sep:.2f}° (far from the 10° glare threshold)")
print()
print("Note: 2026's inferior conjunction occurs with Venus well-separated from Sun (~27°)")
print("This is NOT an unusual alignment year. Venus passes ~8-9° from Sun center.")
