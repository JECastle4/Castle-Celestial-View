"""Test Venus visibility edge case: above horizon but drowned out by solar glare."""
from api.services.venus import calculate_venus_position

print("=" * 120)
print("VENUS SOLAR GLARE TEST - Finding cases where Venus is above horizon but NOT naked-eye visible")
print("=" * 120)
print()

# Test a date during inferior conjunction (late April / early May 2026)
# Venus is very close to the Sun at this time
test_dates = [
    ("2026-04-20", "18:00:00", "Late conjunction - Venus close to Sun"),
    ("2026-04-25", "18:00:00", "Conjunction period - getting closer"),
    ("2026-04-28", "18:00:00", "Near inferior conjunction"),
    ("2026-05-01", "18:00:00", "Exiting conjunction"),
    ("2026-05-05", "18:00:00", "Well clear of Sun"),
]

for date_str, time_str, description in test_dates:
    result = calculate_venus_position(date_str, time_str, 40.7128, -74.0060, 10.0)
    
    status = "✓ NAKED-EYE VISIBLE" if result['naked_eye_visible'] else "⚠ DROWNED OUT BY SUN" if result['is_visible'] else "✗ BELOW HORIZON"
    
    print(f"{date_str} {time_str} - {description}")
    print(f"  Status: {status}")
    print(f"  Altitude: {result['altitude']:6.2f}° | Sun separation: {result['sun_separation']:6.2f}°")
    print(f"  is_visible={result['is_visible']} | naked_eye_visible={result['naked_eye_visible']}")
    print()

print("=" * 120)
print("EXPLANATION:")
print("=" * 120)
print()
print("• is_visible=True + naked_eye_visible=False means:")
print("  Venus is geometrically above the horizon, but too close to the Sun to be seen.")
print("  It's drowned out by solar glare and requires special instruments (solar scope, etc.) to observe.")
print()
print("• The ~10° sun_separation threshold is typical for naked-eye visibility.")
print("  At elongations < 10°, Venus is lost in twilight or solar glare.")
print()
