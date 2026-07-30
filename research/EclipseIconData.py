"""
EclipseIconData.py

Calculates Sun and Moon positions and angular sizes at the moment of maximum
annular solar eclipse on 17 February 2026, as seen from the point of greatest
eclipse (64.7°S, 86.8°E), for use in generating the Castle Celestial View icon.

Eclipse reference:
  Date:        Tuesday 17 February 2026
  Max eclipse: ~12:02 UTC (estimated from published circumstances)
  Coordinates: 64.7°S, 86.8°E
  Duration:    ~140 s (annular phase)
  Band width:  ~616 km
"""

from astropy.coordinates import EarthLocation, AltAz, get_sun, get_body
from astropy.time import Time
import astropy.units as u
import astropy.constants as const
import numpy as np


# ---------------------------------------------------------------------------
# Eclipse parameters
# ---------------------------------------------------------------------------

# Point of greatest eclipse (published NASA/USNO coordinates)
LAT = -64.7   # degrees (south)
LON =  86.8   # degrees (east)
HEIGHT = 0    # metres (ice surface, approximate)

# Maximum eclipse time – 12:02:30 UTC is a close estimate from published
# circumstances; adjust if you have the precise contact times.
ECLIPSE_TIME_UTC = '2026-02-17 12:02:30'

# Physical radii (IAU nominal)
R_SUN_KM  = const.R_sun.to(u.km).value     # 695 700 km
R_MOON_KM = 1737.4                          # km (mean lunar radius)

# ---------------------------------------------------------------------------
# Set up observer and time
# ---------------------------------------------------------------------------

location = EarthLocation(lat=LAT * u.deg, lon=LON * u.deg, height=HEIGHT * u.m)
t = Time(ECLIPSE_TIME_UTC, scale='utc')

altaz_frame = AltAz(obstime=t, location=location, pressure=0.0)

# ---------------------------------------------------------------------------
# Sun position and angular size
# ---------------------------------------------------------------------------

sun = get_sun(t)
sun_altaz = sun.transform_to(altaz_frame)

# Distance to Sun (AU → km)
sun_dist_au = sun.distance.to(u.km).value
sun_angular_radius_deg = np.degrees(np.arctan(R_SUN_KM / sun_dist_au))
sun_angular_diameter_deg = sun_angular_radius_deg * 2

# ---------------------------------------------------------------------------
# Moon position and angular size
# ---------------------------------------------------------------------------

moon = get_body('moon', t, location=location)
moon_altaz = moon.transform_to(altaz_frame)

# Distance to Moon (km)
moon_dist_km = moon.distance.to(u.km).value
moon_angular_radius_deg = np.degrees(np.arctan(R_MOON_KM / moon_dist_km))
moon_angular_diameter_deg = moon_angular_radius_deg * 2

# ---------------------------------------------------------------------------
# Annularity ratio (Moon angular diameter / Sun angular diameter)
# < 1.0 → annular eclipse (ring visible)
# ---------------------------------------------------------------------------

annularity_ratio = moon_angular_diameter_deg / sun_angular_diameter_deg

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

print("=" * 60)
print("Annular Solar Eclipse – 17 February 2026")
print(f"Observer:    {abs(LAT):.1f}°S, {LON:.1f}°E  (point of greatest eclipse)")
print(f"UTC time:    {ECLIPSE_TIME_UTC}")
print("=" * 60)

print("\n--- Sun ---")
print(f"  Altitude:          {sun_altaz.alt.deg:.4f}°")
print(f"  Azimuth:           {sun_altaz.az.deg:.4f}°")
print(f"  Distance:          {sun_dist_au / 1.496e8:.6f} AU  ({sun_dist_au:.0f} km)")
print(f"  Angular diameter:  {sun_angular_diameter_deg:.6f}°  ({sun_angular_diameter_deg * 60:.4f} arcmin)")

print("\n--- Moon ---")
print(f"  Altitude:          {moon_altaz.alt.deg:.4f}°")
print(f"  Azimuth:           {moon_altaz.az.deg:.4f}°")
print(f"  Distance:          {moon_dist_km:.0f} km")
print(f"  Angular diameter:  {moon_angular_diameter_deg:.6f}°  ({moon_angular_diameter_deg * 60:.4f} arcmin)")

print("\n--- Eclipse geometry ---")
print(f"  Moon/Sun diameter ratio:  {annularity_ratio:.6f}")
print(f"  {'ANNULAR eclipse confirmed' if annularity_ratio < 1 else 'NOT annular at these values'}")
ring_fraction = 1.0 - annularity_ratio
print(f"  Ring width fraction:      {ring_fraction:.4f}  ({ring_fraction * 100:.2f}% of solar radius visible)")

print("\n--- Suggested Three.js values ---")
print("  (Normalise Sun angular diameter to 1.0 scene unit)")
print(f"  Sun mesh radius:   1.0000")
print(f"  Moon mesh radius:  {annularity_ratio:.6f}")
print(f"  (Moon should be centred on Sun to produce the annular ring)")
print("=" * 60)
