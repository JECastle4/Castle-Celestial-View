# /// script
# requires-python = ">=3.10"
# dependencies = ["astropy", "numpy", "scipy"]
# ///
"""Scan a year range for solar eclipse arrangements and hybrid sequences.

Besselian-style test on the fundamental plane (through Earth's centre,
perpendicular to the shadow axis) against Earth's WGS84 projection:

- central: the shadow axis meets Earth at some instant;
- two limits: the whole umbral/antumbral circle fits inside Earth at some instant;
- hybrid sequence: umbral sign along the central line (T = umbra, A = antumbra).

Usage: uv run research/scan_eclipse_arrangements.py 2001 2101 > scan.jsonl
"""
import json
import sys
import warnings

import erfa
import numpy as np
from astropy import units as u
from astropy.coordinates import get_body, get_sun
from astropy.time import Time

from validate_global_solar_eclipses import EARTH_AXES_KM, GEOCENTRIC, RADIUS_MODELS

R = RADIUS_MODELS["nasa"]
SYNODIC_DAYS = 29.530588853
REFERENCE_NEW_MOON = Time("2000-01-06 18:14", scale="utc")


def vectors(times):
    rotation = erfa.c2i06a(times.tt.jd1, times.tt.jd2)
    sun = get_sun(times).cartesian.xyz.to_value(u.km)
    moon = get_body("moon", times, location=GEOCENTRIC).cartesian.xyz.to_value(u.km)
    return (np.einsum("nij,jn->ni", rotation, sun),
            np.einsum("nij,jn->ni", rotation, moon))


def discriminant(points, axis):
    """Non-negative where a line through each point along axis meets Earth."""
    m = points / EARTH_AXES_KM
    n = axis / EARTH_AXES_KM
    mn = np.sum(m * n, -1)
    return mn ** 2 - np.sum(n * n, -1) * (np.sum(m * m, -1) - 1)


def geometry(times):
    sun, moon = vectors(times)
    difference = moon - sun
    distance = np.linalg.norm(difference, axis=1)
    axis = difference / distance[:, None]
    umbral_sine = (R.sun_km - R.central_moon_km) / distance
    penumbral_sine = (R.sun_km + R.penumbral_moon_km) / distance
    to_plane = -np.sum(moon * axis, 1)
    centre = moon + to_plane[:, None] * axis
    umbra = (R.central_moon_km - to_plane * umbral_sine) / np.sqrt(1 - umbral_sine ** 2)
    penumbra = ((R.penumbral_moon_km + to_plane * penumbral_sine)
                / np.sqrt(1 - penumbral_sine ** 2))
    return moon, axis, umbral_sine, centre, umbra, penumbra


def circle_inside(axis, centre, radius, samples=72):
    """Minimum discriminant on the shadow circle; positive means fully on Earth."""
    first = np.cross(axis, [0, 0, 1.0])
    first /= np.linalg.norm(first, axis=1)[:, None]
    second = np.cross(axis, first)
    angle = np.linspace(0, 2 * np.pi, samples, endpoint=False)
    points = centre[:, None, :] + np.abs(radius)[:, None, None] * (
        np.cos(angle)[None, :, None] * first[:, None, :]
        + np.sin(angle)[None, :, None] * second[:, None, :])
    return discriminant(points, np.repeat(axis[:, None, :], samples, 1)).min(1)


def nearest_touches(axis, centre, radius):
    offset = np.linalg.norm(centre, axis=1)
    nearest = centre - (centre / offset[:, None]) * np.minimum(np.abs(radius), offset)[:, None]
    return bool(np.max(discriminant(nearest, axis)) >= 0)


def central_sequence(moon, axis, umbral_sine):
    m = moon / EARTH_AXES_KM
    n = axis / EARTH_AXES_KM
    mn = np.sum(m * n, 1)
    nn = np.sum(n * n, 1)
    disc = mn ** 2 - nn * (np.sum(m * m, 1) - 1)
    hit = disc >= 0
    along = (-mn[hit] - np.sqrt(disc[hit])) / nn[hit]
    radius = (R.central_moon_km - along * umbral_sine[hit]) / np.sqrt(1 - umbral_sine[hit] ** 2)
    phases = ["T" if value > 0 else "A" for value in radius]
    return "-".join(p for i, p in enumerate(phases) if i == 0 or phases[i - 1] != p)


def scan(start_year, end_year):
    start = Time(f"{start_year}-01-01", scale="utc")
    end = Time(f"{end_year}-01-01", scale="utc")
    first = int((start - REFERENCE_NEW_MOON).jd / SYNODIC_DAYS) - 1
    last = int((end - REFERENCE_NEW_MOON).jd / SYNODIC_DAYS) + 1
    for lunation in range(first, last + 1):
        approximate = REFERENCE_NEW_MOON + lunation * SYNODIC_DAYS * u.day
        coarse = approximate + np.arange(-48, 48.01, 1) * u.hour
        centre = geometry(coarse)[3]
        gamma = np.linalg.norm(centre, axis=1) / EARTH_AXES_KM[0]
        best = int(np.argmin(gamma))
        if gamma[best] > 1.75:
            continue
        times = coarse[best] + np.arange(-240, 240.1, 0.25) * u.min
        moon, axis, umbral_sine, centre, umbra, penumbra = geometry(times)
        greatest = int(np.argmin(np.linalg.norm(centre, axis=1)))
        if not start <= times[greatest] < end or not nearest_touches(axis, centre, penumbra):
            continue
        record = {"utc": times[greatest].utc.iso[:16],
                  "gamma_abs": round(float(np.linalg.norm(centre[greatest]) / EARTH_AXES_KM[0]), 4),
                  "type": "PARTIAL", "arrangement": None, "central_sequence": None}
        if nearest_touches(axis, centre, umbra):
            central = bool(np.max(discriminant(centre, axis)) >= 0)
            two_limits = bool(np.max(circle_inside(axis, centre, umbra)) > 0)
            sequence = central_sequence(moon, axis, umbral_sine) if central else None
            record["type"] = ("HYBRID" if sequence and "-" in sequence
                              else "TOTAL" if umbra[greatest] > 0 else "ANNULAR")
            record["arrangement"] = ("non_central_one_limit" if not central
                                     else "central_two_limits" if two_limits
                                     else "central_one_limit")
            record["central_sequence"] = sequence
        print(json.dumps(record), flush=True)


if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    scan(int(sys.argv[1]), int(sys.argv[2]))
