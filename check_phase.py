from api.services.venus import calculate_venus_position
from api.models import ObservationDateTime, LocationModel

result = calculate_venus_position(
    ObservationDateTime(date='2026-06-15', time='12:00:00'),
    LocationModel(latitude=0, longitude=0, elevation=0)
)

print(f'Phase name: {result["phase_name"]}')
print(f'Phase angle: {result["phase_angle"]:.1f}°')
print(f'Illumination: {result["illumination"]:.4f} ({result["illumination"]*100:.2f}%)')
