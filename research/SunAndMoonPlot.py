import numpy as np
from astropy.time import Time
from astropy.coordinates import get_body, get_sun, GeocentricTrueEcliptic
import astropy.units as u
import matplotlib.pyplot as plt

start = Time("2025-12-01 00:00", scale="utc")
times = start + np.linspace(0, 365, 365*24) * u.day

moon = get_body('moon', times)
sun = get_sun(times)

moon_ecl = moon.transform_to(GeocentricTrueEcliptic(obstime=times))
sun_ecl = sun.transform_to(GeocentricTrueEcliptic(obstime=times))

moon_lon = moon_ecl.lon.wrap_at(360*u.deg).deg
sun_lon = sun_ecl.lon.wrap_at(360*u.deg).deg
delta = ((moon_lon - sun_lon + 180) % 360) - 180  # signed separation

plt.figure(figsize=(8,3))
plt.plot(times.jd - times.jd[0], moon_lon, label="Moon ecl. lon (deg)")
plt.plot(times.jd - times.jd[0], sun_lon, label="Sun ecl. lon (deg)")
plt.xlabel("Days since start")
plt.ylabel("Ecliptic longitude (deg)")
plt.legend()
plt.tight_layout()
plt.show()

print("Moon advances ~", np.mean(np.diff(moon_lon)), "deg per day (mean)")
print("Synodic separation (Moon - Sun) ranges over:", delta.min(), "to", delta.max(), "deg")