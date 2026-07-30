from api.services.venus import calculate_venus_position
from api.models import ObservationDateTime, LocationModel

for month in range(1, 13):
    result = calculate_venus_position(
        ObservationDateTime(date=f'2026-{month:02d}-15', time='12:00:00'),
        LocationModel(latitude=0, longitude=0, elevation=0)
    )
    phase_type = 'Wax' if result['phase_angle'] < 180 else 'Wan'
    print(f'{month:2d}: PA={result["phase_angle"]:6.1f}° ({phase_type}) Illum={result["illumination"]*100:5.1f}% ({result["phase_name"]})')
