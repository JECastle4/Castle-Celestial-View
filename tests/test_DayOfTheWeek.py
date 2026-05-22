# tests/test_dayofweek.py
from api.utils import jd_to_weekday

def test_jd_to_weekday_saturday():
    assert jd_to_weekday(2451545.0) == 6  # 2000-01-01 is Saturday

def test_jd_fraction_to_weekday_sunday():
    assert jd_to_weekday(2451545.5) == 0  # 2000-01-01 is Sunday

def test_jd_fraction_to_weekday_saturday():
    assert jd_to_weekday(2451545.4999) == 6  # Just before midnight is still Saturday