from astropy.coordinates import EarthLocation, Angle, Latitude, Longitude
import astropy.units as u

# Simple parser: treat plain numeric input as degrees, allow sexagesimal strings to be parsed directly
def _parse_angle_input(s: str) -> Angle:
    s = s.strip()
    if not s:
        raise ValueError("Empty angle string")
    # if it looks like sexagesimal or contains letters, let Angle parse it
    if any(ch.isalpha() for ch in s) or ':' in s or 'd' in s or 'm' in s or 's' in s:
        return Angle(s)
    # otherwise treat as decimal degrees
    return Angle(float(s), u.deg)

def prompt_location():
    lat_s = input("Latitude (deg or D:M:S, e.g. 40.7128 or 40d42m51s): ")
    lon_s = input("Longitude (deg or D:M:S): ")
    h_s = input("Height (m, optional, default 0): ")

    try:
        lat = Latitude(_parse_angle_input(lat_s))
        lon = Longitude(_parse_angle_input(lon_s))
    except Exception as exc:
        raise SystemExit(f"Invalid latitude/longitude input: {exc}")

    height = float(h_s or 0.0) * u.m

    loc = EarthLocation(lat=lat, lon=lon, height=height)
    return loc
