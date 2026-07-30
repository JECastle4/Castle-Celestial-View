from PromptDate import prompt_date
from PromptLocation import prompt_location

from astropy.coordinates import AltAz, get_body

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

# Moon position at that time/location
moon = get_body('moon', t, location=loc)         # pass location for topocentric parallax if supported
moon_altaz = moon.transform_to(AltAz(obstime=t, location=loc))
print("Altitude:", moon_altaz.alt.to(u.deg))
print("Azimuth: ", moon_altaz.az.to(u.deg))
if (moon_altaz.alt.degree < 0):
    print("The moon is below the horizon at this time/location." )