# add to SunPositionFromEarthLocation.py
from PromptDate import prompt_date
from PromptLocation import prompt_location

from astropy.coordinates import get_sun, AltAz

import astropy.units as u

loc = prompt_location()
print("Earth Location:")
print("  Latitude:", loc.lat)
print("  Longitude:", loc.lon)
print("  Height:", loc.height)

t = prompt_date()
print("Julian Date (JD):", t.jd)

# AltAz frame (optional: set pressure=0 to ignore refraction)
aa = AltAz(obstime=t, location=loc, pressure=0.0)

# Sun position at that time/location
sun_altaz = get_sun(t).transform_to(aa)
print("Altitude:", sun_altaz.alt.to(u.deg))
print("Azimuth: ", sun_altaz.az.to(u.deg))
if (sun_altaz.alt.degree < 0):
    print("The Sun is below the horizon at this time/location." )