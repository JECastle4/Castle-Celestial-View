import math

from PromptDate import prompt_date
from PromptLocation import prompt_location
from astropy.time import Time
from api.utils import jd_to_weekday
from SunRiseAndSet import sunrise, sunset
from MoonRiseAndSet import moon_rise_set
from MoonPhase import moon_phase, moon_phase_name

# Example
t = prompt_date()
print("Parsed date:", t.iso)

print("ISO (UTC):", t.iso)
print("Julian Date (JD):", t.jd)
print("Modified Julian Date (MJD):", t.mjd)
weekday = jd_to_weekday(t.jd)
daysOfWeek = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
print("Day of the week (0=Sun ... 6=Sat):", weekday)
print("Day of the week:", daysOfWeek[weekday])

loc = prompt_location()
t = sunrise(loc, t.jd)
print("Sunrise time (UTC):", t.iso if t is not None else "Sun never rises on this date at this location")
t = sunset(loc, t.jd)
print("Sunset time (UTC):", t.iso if t is not None else "Sun is circumpolar on this date at this location")

rise_set_tuple = moon_rise_set(loc, math.floor(t.jd))
for time_obj in rise_set_tuple:
    if time_obj is not None:
        print("Moon crossing time (UTC):", time_obj[0].iso)
    else:
        print("Moon never crosses the horizon on this date at this location")

#moon_phase_value = moon_phase(Time(math.floor(t.jd), format='jd'), location=loc)
moon_phase_value = moon_phase(t, location=loc)
moon_phase_name = moon_phase_name(t, location=loc)
print(f"Moon phase: {moon_phase_value*100:.2f}% illuminated. Phase name: {moon_phase_name}.")