"""Low-level shared ephemeris and phase timing helpers for eclipse services."""

import threading
from collections import OrderedDict

import numpy as np
from astropy.coordinates import EarthLocation, get_body, get_sun
import astropy.units as u

GEOCENTRIC = EarthLocation.from_geocentric(0 * u.km, 0 * u.km, 0 * u.km)
_INV_PHI = (np.sqrt(5) - 1) / 2


class _BoundedCache:
    """Thread-safe bounded LRU for shared greatest-eclipse timestamps."""

    def __init__(self, maximum_size=1024):
        self.maximum_size = maximum_size
        self.entries = OrderedDict()
        self.lock = threading.RLock()

    def get(self, key):
        """Return a cached value while refreshing its recency."""
        with self.lock:
            if key not in self.entries:
                return None
            self.entries.move_to_end(key)
            return self.entries[key]

    def set(self, key, value):
        """Store a value and evict oldest entries beyond the bound."""
        with self.lock:
            self.entries[key] = value
            self.entries.move_to_end(key)
            while len(self.entries) > self.maximum_size:
                self.entries.popitem(last=False)

    def clear(self):
        """Discard all cached timestamps."""
        with self.lock:
            self.entries.clear()


GREATEST_ECLIPSE_CACHE = _BoundedCache()


def sun_moon_separation_deg(time_obj):
    """Return geocentric Sun–Moon angular separation in degrees."""
    sun = get_sun(time_obj)
    moon = get_body("moon", time_obj, location=GEOCENTRIC)
    return sun.separation(moon).degree


def is_new_moon(time_obj, tolerance_deg=10):
    """Return whether the geocentric phase angle is within the new-moon limit."""
    return sun_moon_separation_deg(time_obj) < tolerance_deg


def find_greatest_eclipse_time(
    approx_time, is_lunar, search_window_hours=24, iterations=40,
    lunar_separation=None, solar_separation=None,
):
    """Minimize the established geocentric separation around syzygy."""
    cache_key = (approx_time.iso, is_lunar, search_window_hours, iterations)
    cached = GREATEST_ECLIPSE_CACHE.get(cache_key)
    if cached is not None:
        return cached
    if is_lunar:
        if lunar_separation is None:
            raise ValueError("A lunar separation function is required")
        separation = lunar_separation
    else:
        separation = solar_separation or sun_moon_separation_deg

    left = approx_time - search_window_hours * u.hour
    right = approx_time + search_window_hours * u.hour
    span = right - left
    inner_left = right - span * _INV_PHI
    inner_right = left + span * _INV_PHI
    value_left = separation(inner_left)
    value_right = separation(inner_right)
    for _ in range(iterations):
        if value_left < value_right:
            right = inner_right
            inner_right = inner_left
            value_right = value_left
            span = right - left
            inner_left = right - span * _INV_PHI
            value_left = separation(inner_left)
        else:
            left = inner_left
            inner_left = inner_right
            value_left = value_right
            span = right - left
            inner_right = left + span * _INV_PHI
            value_right = separation(inner_right)
    result = left + (right - left) / 2
    GREATEST_ECLIPSE_CACHE.set(cache_key, result)
    return result
