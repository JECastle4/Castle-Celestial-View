"""Calculate Moon phase and illumination.

This module provides functions to compute the Moon's phase, illumination
fraction, and phase names.
"""
from astropy.coordinates import get_sun, get_body
import numpy as np

def moon_phase(time, location=None):
    """Compute Moon illumination fraction (0=new, 1=full)."""
    sun = get_sun(time)
    moon = (get_body("moon", time, location=location)
            if location is not None
            else get_body("moon", time))

    # Elongation angle (Sun-Moon separation as seen from Earth)
    elongation = sun.separation(moon)
    # Illumination fraction
    # elongation=0° → new moon (illum=0), elongation=180° → full moon (illum=1)
    illum = 0.5 * (1 - np.cos(elongation.rad))
    return illum


def moon_phase_angle(time, location=None):
    """Calculate the Moon's phase angle in ecliptic longitude.
    Parameters
    ----------
    time : Time
        Observation time.
    location : EarthLocation, optional
        Observer location (for topocentric correction).

    Returns
    -------
    float
        Phase angle in degrees (0-360).
        0-180 = waxing (new → full)
        180-360 = waning (full → new)
    """
    sun = get_sun(time)
    moon = (get_body("moon", time, location=location)
            if location is not None
            else get_body("moon", time))
    # Calculate ecliptic longitudes
    sun_lon = sun.geocentrictrueecliptic.lon.deg
    moon_lon = moon.geocentrictrueecliptic.lon.deg

    # Phase angle (0-360, measures Moon ahead of Sun in ecliptic)
    phase_angle = (moon_lon - sun_lon) % 360

    return phase_angle


def moon_phase_name(time, location=None):
    """Get textual moon phase name."""
    # Get illumination fraction
    illum = moon_phase(time, location=location)
    illum_pct = illum * 100

    # Get phase angle to determine waxing vs waning
    phase_angle = moon_phase_angle(time, location=location)

    # Determine phase name
    if phase_angle < 180:  # Waxing
        if illum_pct < 3:
            phase_name = "New Moon"
        elif illum_pct < 47:
            phase_name = "Waxing Crescent"
        elif illum_pct < 53:
            phase_name = "First Quarter"
        elif illum_pct < 97:
            phase_name = "Waxing Gibbous"
        else:
            phase_name = "Full Moon"
    else:  # Waning
        if illum_pct > 97:
            phase_name = "Full Moon"
        elif illum_pct > 53:
            phase_name = "Waning Gibbous"
        elif illum_pct > 47:
            phase_name = "Last Quarter"
        elif illum_pct > 3:
            phase_name = "Waning Crescent"
        else:
            phase_name = "New Moon"

    return phase_name
