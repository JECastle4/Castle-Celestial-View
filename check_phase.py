from api.services.venus import calculate_venus_position

result = calculate_venus_position(
    date_str='2026-06-15',
    time_str='12:00:00',
    latitude=0,
    longitude=0,
    elevation=0
)

print(f'Phase name: {result["phase_name"]}')
print(f'Phase angle: {result["phase_angle"]:.1f}°')
print(f'Illumination: {result["illumination"]:.4f} ({result["illumination"]*100:.2f}%)')
