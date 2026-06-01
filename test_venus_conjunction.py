"""Test Venus during conjunction when glare is most likely."""
from api.services.venus import calculate_venus_position

print("Testing Venus visibility when Sun is nearby (conjunction period)")
print("=" * 120)
print()

# During inferior conjunction (April-May 2026), Venus passes close to the Sun
# Test various times to catch when Venus is above horizon but too close to Sun
test_cases = [
    ("2026-04-15", "12:00:00", "Before conjunction - midday (Sun high)"),
    ("2026-04-20", "12:00:00", "Approaching conjunction - midday"),
    ("2026-04-25", "12:00:00", "Near conjunction - midday"),
    ("2026-04-28", "12:00:00", "Near inferior conjunction - midday"),
    ("2026-05-01", "12:00:00", "After conjunction - midday"),
]

print("Testing at NOON when Sun is highest in sky:")
print("-" * 120)

for date_str, time_str, desc in test_cases:
    result = calculate_venus_position(date_str, time_str, 40.7128, -74.0060, 10.0)
    
    if result["is_visible"] and not result["naked_eye_visible"]:
        status = "⚠ DROWNED OUT - Above horizon but too close to Sun!"
    elif result["naked_eye_visible"]:
        status = "✓ Visible to naked eye"
    else:
        status = "✗ Below horizon"
    
    print(f"{date_str} - {desc}")
    print(f"  Altitude: {result['altitude']:7.2f}° | Sun separation: {result['sun_separation']:6.2f}°")
    print(f"  Status: {status}")
    print()
