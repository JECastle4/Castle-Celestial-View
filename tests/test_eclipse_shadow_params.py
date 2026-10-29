import pytest
from astropy.time import Time

import api.services.eclipse_contact_times as contact_times
import api.services.eclipse_detection as eclipse_detection


@pytest.mark.parametrize(
    'shadow_calculator',
    [
        eclipse_detection.calculate_earth_shadow_cone,
        eclipse_detection.calculate_moon_shadow_cone,
    ],
)
def test_shadow_calculator_uses_supplied_parameters(monkeypatch, shadow_calculator):
    params = {'sun_dist_km': 150_000_000, 'moon_dist_km': 384_000}

    def unexpected_ephemeris_query(_time):
        pytest.fail('shadow calculator repeated the ephemeris query')

    monkeypatch.setattr(eclipse_detection, 'get_sun_moon_parameters', unexpected_ephemeris_query)

    shadow = shadow_calculator(Time('2026-08-12 18:11:00', scale='utc'), params)

    assert 'umbral_radius_km' in shadow
    assert 'penumbral_radius_km' in shadow


def test_lunar_contact_search_passes_parameters_to_shadow_calculator(monkeypatch):
    params = {'moon_ang_radius_deg': 0.3, 'antisolar_separation_deg': 0.0}
    received_params = []
    parameter_queries = []

    def get_params(time):
        parameter_queries.append(time)
        return params

    def calculate_shadow(_time, supplied_params):
        received_params.append(supplied_params)
        return {'umbral_radius_ang': 0.4, 'penumbral_radius_ang': 0.5}

    monkeypatch.setattr(contact_times, 'get_sun_moon_parameters', get_params)
    monkeypatch.setattr(contact_times, 'calculate_earth_shadow_cone', calculate_shadow)

    contact_times.calculate_lunar_contact_times(
        Time('2026-08-12 18:11:00', scale='utc'),
        search_window_hours=1,
    )

    assert len(parameter_queries) == len(received_params)
    assert all(received is params for received in received_params)


def test_solar_contact_search_passes_parameters_to_shadow_calculator(monkeypatch):
    params = {'moon_dist_km': 384_000, 'sun_moon_separation_deg': 0.0}
    received_params = []
    parameter_queries = []

    def get_params(time):
        parameter_queries.append(time)
        return params

    def calculate_shadow(_time, supplied_params):
        received_params.append(supplied_params)
        return {'penumbral_radius_km': 100_000, 'umbral_radius_km': 50_000}

    monkeypatch.setattr(contact_times, 'get_sun_moon_parameters', get_params)
    monkeypatch.setattr(contact_times, 'calculate_moon_shadow_cone', calculate_shadow)

    contact_times.calculate_solar_contact_times(
        Time('2026-08-12 18:11:00', scale='utc'),
        search_window_hours=1,
    )

    assert len(parameter_queries) == len(received_params)
    assert all(received is params for received in received_params)
