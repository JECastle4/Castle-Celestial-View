#!/usr/bin/env python3
"""
Issue #245 research: eclipse visibility-map API contract + feasibility proof.

Purpose
-------
1. Pin down the response contract for
   ``GET /api/v2/astronomical-events/{event_id}/visibility-map`` as concrete
   Pydantic models (``VisibilityMapResponse`` below). Every sample payload
   produced by this script is validated against those models and against
   RFC 7946 GeoJSON rules (lon/lat ranges, closed rings, antimeridian split).
2. Prove the map data can be calculated for solar (partial, annular, total,
   hybrid, polar) and lunar (penumbral, partial, total) eclipses, including
   historical dates, and that a non-eclipse returns a consistent
   ``not_eclipse`` envelope instead of geometry.
3. Compare computed values against published NASA/EclipseWise reference
   values with explicit tolerances, and report timings and payload sizes.
4. Show the calendar-consistency gap tracked in #275 (the current calendar
   classifier reports a hybrid as annular; the map reports "total" as the
   maximum phase anywhere).

Method
------
Solar: Besselian elements (x, y, d, mu, l1, l2, f1, f2) are derived from
Astropy geocentric apparent Sun/Moon positions in the true-equator-of-date
(TETE) frame, with Greenwich apparent sidereal time from ERFA using an
explicit Delta T (UT1 = TT - Delta T). This avoids Astropy's frozen IERS
extrapolation (TT-UT1 ~= 69 s for all future dates; wrong by hours in
antiquity). The central line, northern/southern umbral limits (WGS84
ellipsoid), local total/annular type along the path, greatest eclipse and a
global maximum-magnitude raster (Sun above horizon) are all vectorised.
Magnitude bands are traced with contourpy; paths are split at the
antimeridian with shapely.

Lunar: geocentric Moon/antisolar separation with Danjon shadow radii, contact
times by sign change on a dense time grid, sublunar track, and Moon-above-
horizon visibility fractions per phase on a global grid.

Run (from repository root; needs numpy, astropy, contourpy, shapely, pydantic)::

    python research/verify_eclipse_visibility_map.py
    python research/verify_eclipse_visibility_map.py --grid-deg 0.5 \
        --output-dir /tmp/eclipse-map-samples

Limitations (research only, not production code): builtin Astropy ephemeris
(JPL kernels were not reachable here), no lunar limb profile, no refraction,
spherical great-circle distances for path width, 1-minute raster sampling.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional

import numpy as np
import erfa
import astropy.units as u
from astropy.coordinates import TETE, get_body, get_sun
from astropy.time import Time
from astropy.utils import iers
from astropy.utils.exceptions import AstropyWarning
import contourpy
import shapely
from pydantic import BaseModel, Field, model_validator
from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Polygon, box, mapping
from shapely.ops import unary_union

iers.conf.auto_download = False
iers.conf.auto_max_age = None
warnings.filterwarnings("ignore", category=erfa.ErfaWarning)  # "dubious year" for ancient dates
warnings.filterwarnings("ignore", category=AstropyWarning)

REPO_ROOT = Path(__file__).resolve().parents[1]

SCHEMA_VERSION = "1.0"
ALGORITHM_REVISION = "research-2026.1"

A_KM = 6378.137                 # WGS84 equatorial radius
E2 = 0.00669437999014           # WGS84 first eccentricity squared
R_SUN_KM = 696000.0             # NASA canon solar radius
K_PENUMBRA = 0.2725076          # Moon radius / Earth radius (penumbral, IAU)
K_UMBRA = 0.272281              # smaller k for umbral contacts (limb valleys, NASA)
MEAN_EARTH_RADIUS_KM = 6371.0088
SIDEREAL_DEG_PER_SECOND = 360.0 / 86164.0905
GREGORIAN_START_JD = 2299160.5  # 1582-10-15 00:00


# ---------------------------------------------------------------------------
# API contract (proposed). These models are the source of truth for the
# research payloads; production would move them into api/models.py.
# ---------------------------------------------------------------------------

MapStatus = Literal["ready", "not_eclipse", "indeterminate", "unsupported"]
CalendarType = Literal["partial", "annular", "total", "penumbral"]
Classification = Literal["partial", "annular", "total", "hybrid", "penumbral"]
LocalType = Literal["partial", "annular", "total"]


class TimeInstant(BaseModel):
    """An instant carried in both scales so the UI never re-derives Delta T."""
    ut: str = Field(description="ISO-8601-style UT1 (~UTC) in `calendar`, astronomical year numbering")
    tt_jd: float = Field(description="Terrestrial Time Julian Date (exact, unambiguous)")
    calendar: Literal["gregorian", "julian"]


class GeoPoint(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class EventSummary(BaseModel):
    """Canonical event record; must be identical to the calendar's record."""
    event_id: str
    kind: Literal["solar", "lunar"]
    calendar_type: CalendarType = Field(description="Maximum phase anywhere on Earth (#275)")
    classification: Classification = Field(description="Full classification incl. hybrid")
    centrality: Optional[Literal["central", "non_central"]] = None
    local_types_present: list[LocalType] = []
    greatest_eclipse: TimeInstant
    greatest_point: Optional[GeoPoint] = None
    gamma: float
    magnitude: float = Field(description="Solar: eclipse magnitude; lunar: umbral magnitude")
    penumbral_magnitude: Optional[float] = None
    central_duration_s: Optional[float] = None
    path_width_km: Optional[float] = None
    contacts: dict[str, Optional[TimeInstant]] = {}


class NoEclipseDetail(BaseModel):
    reason: Literal["outside_shadow", "no_syzygy_in_window"]
    nearest_syzygy: Optional[TimeInstant] = None
    shadow_margin: Optional[float] = Field(
        None, description="Positive = inside shadow threshold; units documented per kind")


class TimeModel(BaseModel):
    dynamical_scale: Literal["TT"] = "TT"
    universal_scale: Literal["UT1"] = "UT1"
    delta_t_s: float
    delta_t_sigma_s: float
    delta_t_source: Literal["espenak_meeus_2006", "iers_observed", "override"]
    ephemeris: str


class Accuracy(BaseModel):
    confidence: Literal["high", "medium", "low"]
    longitude_uncertainty_deg: float
    along_track_uncertainty_km: float
    notes: list[str] = []


class Layer(BaseModel):
    id: str
    geometry_kind: Literal["point", "line", "polygon"]
    label_key: str = Field(description="i18n key, never a translated string")
    feature_count: int
    default_visible: bool
    z_index: int


class ViewHints(BaseModel):
    bbox: Optional[list[float]] = None
    center: Optional[GeoPoint] = None
    suggested_view: Literal["mercator", "polar_north", "polar_south", "global"]


class WarningItem(BaseModel):
    code: str
    message_key: str
    params: dict[str, Any] = {}


class VisibilityMapResponse(BaseModel):
    schema_version: Literal["1.0"]
    algorithm_revision: str
    map_status: MapStatus
    query: dict[str, Any]
    event: Optional[EventSummary] = None
    no_eclipse: Optional[NoEclipseDetail] = None
    geometry: Optional[dict[str, Any]] = Field(None, description="RFC 7946 FeatureCollection")
    layers: list[Layer] = []
    time_model: TimeModel
    accuracy: Accuracy
    view_hints: Optional[ViewHints] = None
    warnings: list[WarningItem] = []

    @model_validator(mode="after")
    def _status_consistency(self):
        if self.map_status == "ready":
            assert self.event is not None and self.geometry is not None, "ready needs event+geometry"
            assert self.no_eclipse is None
        else:
            assert self.geometry is None and not self.layers, "geometry only when ready"
        if self.map_status == "not_eclipse":
            assert self.event is None and self.no_eclipse is not None
        return self


# ---------------------------------------------------------------------------
# Time: calendars, Delta T
# ---------------------------------------------------------------------------

def calendar_to_jd(year: int, month: int, day: float) -> float:
    """Meeus ch. 7. Julian calendar before 1582-10-15, Gregorian after."""
    gregorian = (year, month, day) >= (1582, 10, 15)
    y, m = (year - 1, month + 12) if month <= 2 else (year, month)
    b = 0
    if gregorian:
        a = math.floor(y / 100)
        b = 2 - a + math.floor(a / 4)
    return math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + day + b - 1524.5


def jd_to_calendar(jd: float) -> tuple[int, int, float, str]:
    z = math.floor(jd + 0.5)
    f = jd + 0.5 - z
    if z < 2299161:
        a = z
        cal = "julian"
    else:
        alpha = math.floor((z - 1867216.25) / 36524.25)
        a = z + 1 + alpha - math.floor(alpha / 4)
        cal = "gregorian"
    b = a + 1524
    c = math.floor((b - 122.1) / 365.25)
    d = math.floor(365.25 * c)
    e = math.floor((b - d) / 30.6001)
    day = b - d - math.floor(30.6001 * e) + f
    month = e - 1 if e < 14 else e - 13
    year = c - 4716 if month > 2 else c - 4715
    return year, month, day, cal


def parse_date(text: str) -> float:
    """'YYYY-MM-DD' (astronomical year, may be negative) -> JD at 00:00 UT."""
    sign = -1 if text.startswith("-") else 1
    y, m, d = text.lstrip("-").split("-")
    return calendar_to_jd(sign * int(y), int(m), int(d))


def format_ut(jd_ut: float) -> tuple[str, str]:
    year, month, dayf, cal = jd_to_calendar(jd_ut)
    day = int(dayf)
    secs = round((dayf - day) * 86400)
    if secs == 86400:  # rounding spill-over; re-run on the next day
        return format_ut(jd_ut + 0.5 / 86400)
    hh, rem = divmod(secs, 3600)
    mm, ss = divmod(rem, 60)
    ys = f"{year:04d}" if year >= 0 else f"-{-year:04d}"
    return f"{ys}-{month:02d}-{day:02d}T{hh:02d}:{mm:02d}:{ss:02d}Z", cal


def delta_t_espenak_meeus(year: float) -> float:
    """Espenak & Meeus (2006) polynomial expressions for Delta T (seconds)."""
    y = year
    if y < -500 or y >= 2150:
        uu = (y - 1820) / 100
        return -20 + 32 * uu ** 2
    if y < 500:
        uu = y / 100
        return (10583.6 - 1014.41 * uu + 33.78311 * uu ** 2 - 5.952053 * uu ** 3
                - 0.1798452 * uu ** 4 + 0.022174192 * uu ** 5 + 0.0090316521 * uu ** 6)
    if y < 1600:
        uu = (y - 1000) / 100
        return (1574.2 - 556.01 * uu + 71.23472 * uu ** 2 + 0.319781 * uu ** 3
                - 0.8503463 * uu ** 4 - 0.005050998 * uu ** 5 + 0.0083572073 * uu ** 6)
    if y < 1700:
        t = y - 1600
        return 120 - 0.9808 * t - 0.01532 * t ** 2 + t ** 3 / 7129
    if y < 1800:
        t = y - 1700
        return 8.83 + 0.1603 * t - 0.0059285 * t ** 2 + 0.00013336 * t ** 3 - t ** 4 / 1174000
    if y < 1860:
        t = y - 1800
        return (13.72 - 0.332447 * t + 0.0068612 * t ** 2 + 0.0041116 * t ** 3 - 0.00037436 * t ** 4
                + 0.0000121272 * t ** 5 - 0.0000001699 * t ** 6 + 0.000000000875 * t ** 7)
    if y < 1900:
        t = y - 1860
        return (7.62 + 0.5737 * t - 0.251754 * t ** 2 + 0.01680668 * t ** 3
                - 0.0004473624 * t ** 4 + t ** 5 / 233174)
    if y < 1920:
        t = y - 1900
        return -2.79 + 1.494119 * t - 0.0598939 * t ** 2 + 0.0061966 * t ** 3 - 0.000197 * t ** 4
    if y < 1941:
        t = y - 1920
        return 21.20 + 0.84493 * t - 0.076100 * t ** 2 + 0.0020936 * t ** 3
    if y < 1961:
        t = y - 1950
        return 29.07 + 0.407 * t - t ** 2 / 233 + t ** 3 / 2547
    if y < 1986:
        t = y - 1975
        return 45.45 + 1.067 * t - t ** 2 / 260 - t ** 3 / 718
    if y < 2005:
        t = y - 2000
        return (63.86 + 0.3345 * t - 0.060374 * t ** 2 + 0.0017275 * t ** 3
                + 0.000651814 * t ** 4 + 0.00002373599 * t ** 5)
    if y < 2050:
        t = y - 2000
        return 62.92 + 0.32217 * t + 0.005589 * t ** 2
    return -20 + 32 * ((y - 1820) / 100) ** 2 - 0.5628 * (2150 - y)


def delta_t_sigma(year: float) -> float:
    """Morrison & Stephenson style uncertainty ~0.8 t^2 s, t in centuries from 1820.

    Floors at 1 s: for modern dates production should use IERS observed values,
    while the polynomial alone is several seconds off (e.g. 2024 model 73.9 s vs
    observed ~69.2 s).
    """
    t = (year - 1820) / 100
    return max(1.0, 0.8 * t * t)


def jd_to_year(jd: float) -> float:
    return 2000.0 + (jd - 2451545.0) / 365.25


def time_instant(jd_tt: float, dt_s: float) -> TimeInstant:
    ut, cal = format_ut(jd_tt - dt_s / 86400)
    return TimeInstant(ut=ut, tt_jd=round(float(jd_tt), 6), calendar=cal)


# ---------------------------------------------------------------------------
# Ephemeris and Besselian elements
# ---------------------------------------------------------------------------

def sun_moon_tete_km(jd_tt: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Geocentric apparent Sun/Moon vectors (km), true equator & equinox of date."""
    t = Time(np.atleast_1d(jd_tt), format="jd", scale="tt")
    frame = TETE(obstime=t)
    sun = get_sun(t).transform_to(frame).cartesian.xyz.to_value(u.km)
    moon = get_body("moon", t).transform_to(frame).cartesian.xyz.to_value(u.km)
    return sun, moon


def gast_rad(jd_tt: np.ndarray, dt_s: float) -> np.ndarray:
    jd_ut1 = jd_tt - dt_s / 86400.0
    ut_int = np.floor(jd_ut1)
    tt_int = np.floor(jd_tt)
    return erfa.gst06a(ut_int, jd_ut1 - ut_int, tt_int, jd_tt - tt_int)


@dataclass
class Besselian:
    jd_tt: np.ndarray
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    d: np.ndarray
    mu: np.ndarray
    l1: np.ndarray
    l2: np.ndarray
    tan_f1: np.ndarray
    tan_f2: np.ndarray
    x_dot: np.ndarray       # per hour
    y_dot: np.ndarray
    d_dot: np.ndarray
    mu_dot: np.ndarray

    def take(self, idx) -> "Besselian":
        return Besselian(**{k: getattr(self, k)[idx] for k in self.__dataclass_fields__})


def besselian(jd_tt: np.ndarray, dt_s: float) -> Besselian:
    """Vectorised Besselian elements (Earth equatorial radii; angles radians)."""
    jd_tt = np.atleast_1d(np.asarray(jd_tt, dtype=float))
    s_km, m_km = sun_moon_tete_km(jd_tt)
    sun, moon = s_km / A_KM, m_km / A_KM
    axis = sun - moon
    g = np.linalg.norm(axis, axis=0)
    k = axis / g
    d = np.arcsin(k[2])
    a = np.arctan2(k[1], k[0])
    x = -moon[0] * np.sin(a) + moon[1] * np.cos(a)
    y = (-moon[0] * np.sin(d) * np.cos(a) - moon[1] * np.sin(d) * np.sin(a)
         + moon[2] * np.cos(d))
    z = (moon * k).sum(axis=0)
    f1 = np.arcsin((R_SUN_KM / A_KM + K_PENUMBRA) / g)
    f2 = np.arcsin((R_SUN_KM / A_KM - K_UMBRA) / g)
    l1 = z * np.tan(f1) + K_PENUMBRA / np.cos(f1)
    l2 = z * np.tan(f2) - K_UMBRA / np.cos(f2)
    mu = np.mod(gast_rad(jd_tt, dt_s) - a, 2 * np.pi)
    if jd_tt.size > 1:
        hours = (jd_tt - jd_tt[0]) * 24.0
        rate = lambda arr: np.gradient(arr, hours)  # noqa: E731
        x_dot, y_dot, d_dot, mu_dot = rate(x), rate(y), rate(d), rate(np.unwrap(mu))
    else:
        x_dot = y_dot = d_dot = mu_dot = np.full_like(x, np.nan)
    return Besselian(jd_tt, x, y, z, d, mu, l1, l2, np.tan(f1), np.tan(f2),
                     x_dot, y_dot, d_dot, mu_dot)


def rho_terms(lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """rho*cos(phi'), rho*sin(phi') for a sea-level observer at geodetic lat."""
    s = np.sin(lat)
    den = np.sqrt(1 - E2 * s * s)
    return np.cos(lat) / den, (1 - E2) * s / den


def observer_coords(lat, lon, d, mu):
    rc, rs = rho_terms(lat)
    h = mu + lon
    xi = rc * np.sin(h)
    eta = rs * np.cos(d) - rc * np.cos(h) * np.sin(d)
    zeta = rs * np.sin(d) + rc * np.cos(h) * np.cos(d)
    return xi, eta, zeta, h, rc


def fundamental_to_geodetic(xi, eta, d, mu):
    """Point on the WGS84 surface with fundamental-plane coords (xi, eta)."""
    rho1 = np.sqrt(1 - E2 * np.cos(d) ** 2)
    sd1 = np.sin(d) / rho1
    cd1 = np.sqrt(1 - E2) * np.cos(d) / rho1
    eta1 = eta / rho1
    zeta1_sq = 1 - xi ** 2 - eta1 ** 2
    valid = zeta1_sq >= -1e-12
    zeta1 = np.sqrt(np.clip(zeta1_sq, 0, None))
    sin_phi1 = np.clip(eta1 * cd1 + zeta1 * sd1, -1, 1)
    theta = np.arctan2(xi, zeta1 * cd1 - eta1 * sd1)
    lat = np.arctan(np.tan(np.arcsin(sin_phi1)) / np.sqrt(1 - E2))
    lon = np.mod(theta - mu + np.pi, 2 * np.pi) - np.pi
    return lat, lon, valid


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    a = (np.sin((lat2 - lat1) / 2) ** 2
         + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2)
    return float(2 * MEAN_EARTH_RADIUS_KM * np.arcsin(np.sqrt(a)))


def parabolic_min(t: np.ndarray, f: np.ndarray) -> float:
    i = int(np.clip(np.argmin(f), 1, len(f) - 2))
    y0, y1, y2 = f[i - 1], f[i], f[i + 1]
    den = y0 - 2 * y1 + y2
    off = 0.5 * (y0 - y2) / den if den != 0 else 0.0
    return float(t[i] + off * (t[i + 1] - t[i]))


# ---------------------------------------------------------------------------
# GeoJSON helpers (RFC 7946: lon in [-180, 180], split at the antimeridian)
# ---------------------------------------------------------------------------

def _round_coords(obj, nd: int):
    if isinstance(obj, (list, tuple)):
        if obj and isinstance(obj[0], (int, float)):
            return [round(float(v), nd) for v in obj]
        return [_round_coords(o, nd) for o in obj]
    return obj


def _split_unwrapped(geom, nd: int) -> list[dict]:
    """Clip a geometry in unwrapped longitudes into [-180,180] tiles."""
    minx, _, maxx, _ = geom.bounds
    parts = []
    for k in range(math.floor((minx + 180) / 360), math.floor((maxx + 180) / 360) + 1):
        tile = geom.intersection(box(-180 + 360 * k, -90, 180 + 360 * k, 90))
        if tile.is_empty:
            continue
        tile = affinity.translate(tile, xoff=-360 * k)
        for g in getattr(tile, "geoms", [tile]):
            if g.geom_type in ("LineString", "Polygon") and not g.is_empty and g.length > 0:
                parts.append(g)
    return parts


def line_features(lon_deg, lat_deg, props: dict, nd: int = 4) -> list[dict]:
    lon_deg, lat_deg = np.asarray(lon_deg), np.asarray(lat_deg)
    ok = np.isfinite(lon_deg) & np.isfinite(lat_deg)
    lon_deg, lat_deg = lon_deg[ok], lat_deg[ok]
    if len(lon_deg) < 2:
        return []
    lon_u = np.degrees(np.unwrap(np.radians(lon_deg)))
    parts = _split_unwrapped(LineString(np.column_stack([lon_u, lat_deg])), nd)
    if not parts:
        return []
    coords = [_round_coords([list(c) for c in p.coords], nd) for p in parts]
    geom = ({"type": "LineString", "coordinates": coords[0]} if len(coords) == 1
            else {"type": "MultiLineString", "coordinates": coords})
    return [{"type": "Feature", "geometry": geom, "properties": props}]


def ring_polygon_features(lon_deg, lat_deg, props: dict, nd: int = 4) -> list[dict]:
    """Closed ring (e.g. north limit + reversed south limit) -> split polygon."""
    lon_deg, lat_deg = np.asarray(lon_deg), np.asarray(lat_deg)
    ok = np.isfinite(lon_deg) & np.isfinite(lat_deg)
    lon_deg, lat_deg = lon_deg[ok], lat_deg[ok]
    if len(lon_deg) < 3:
        return []
    lon_u = np.degrees(np.unwrap(np.radians(lon_deg)))
    pts = list(zip(lon_u, lat_deg))
    winding = lon_u[-1] - lon_u[0]
    if abs(winding) > 180:  # ring encircles a pole: close it through the pole
        pole = 90.0 if np.mean(lat_deg) > 0 else -90.0
        pts += [(lon_u[-1], pole), (lon_u[0], pole)]
    poly = Polygon(pts).buffer(0)
    parts = [p for p in _split_unwrapped(poly, nd) if p.geom_type == "Polygon"]
    return polygons_to_features(parts, props, nd)


def polygons_to_features(polys, props: dict, nd: int) -> list[dict]:
    polys = [p for p in polys if not p.is_empty and p.area > 0]
    if not polys:
        return []
    mp = MultiPolygon(polys) if len(polys) > 1 else polys[0]
    # Snap to the output grid with topology repair, so rounding cannot create
    # self-intersections or overlapping parts.
    mp = shapely.set_precision(unary_union(mp), 10 ** -nd)
    if mp.is_empty:
        return []
    if mp.geom_type == "GeometryCollection":
        kept = [g for g in mp.geoms if g.geom_type in ("Polygon", "MultiPolygon")]
        mp = unary_union(kept)
        if mp.is_empty:
            return []
    geom = _round_coords(mapping(mp)["coordinates"], nd)
    return [{"type": "Feature",
             "geometry": {"type": mp.geom_type, "coordinates": geom},
             "properties": props}]


def filled_band_polygons(lon_deg, lat_deg, field, lower, upper, simplify_deg):
    gen = contourpy.contour_generator(lon_deg, lat_deg, field,
                                      fill_type=contourpy.FillType.OuterOffset)
    points_list, offsets_list = gen.filled(lower, upper)
    polys = []
    for pts, offs in zip(points_list, offsets_list):
        rings = [pts[offs[i]:offs[i + 1]] for i in range(len(offs) - 1)]
        poly = Polygon(rings[0], rings[1:]).buffer(0)
        if simplify_deg:
            poly = poly.simplify(simplify_deg, preserve_topology=True)
        polys.extend(getattr(poly, "geoms", [poly]))
    return polys


def contour_lines(lon_deg, lat_deg, field, level):
    gen = contourpy.contour_generator(lon_deg, lat_deg, field,
                                      line_type=contourpy.LineType.Separate)
    return gen.lines(level)


def validate_feature_collection(fc: dict) -> list[str]:
    """RFC 7946 sanity checks. Returns a list of problems (empty = valid)."""
    problems = []

    def check_positions(coords, where):
        arr = np.asarray(coords, dtype=float)
        if arr.ndim != 2 or arr.shape[1] != 2:
            problems.append(f"{where}: bad position array")
            return
        if np.any(np.abs(arr[:, 0]) > 180) or np.any(np.abs(arr[:, 1]) > 90):
            problems.append(f"{where}: coordinate out of range")
        if len(arr) > 1:
            jumps = np.abs(np.diff(arr[:, 0])) > 180
            # Edges running along a pole (|lat| = 90) legitimately span 360 deg.
            at_pole = (np.abs(arr[:-1, 1]) >= 89.999) & (np.abs(arr[1:, 1]) >= 89.999)
            if np.any(jumps & ~at_pole):
                problems.append(f"{where}: segment crosses antimeridian unsplit")

    for i, f in enumerate(fc.get("features", [])):
        g = f["geometry"]
        where = f"feature[{i}]({f['properties'].get('layer')})"
        t = g["type"]
        if t == "Point":
            check_positions([g["coordinates"]], where)
        elif t == "LineString":
            check_positions(g["coordinates"], where)
        elif t == "MultiLineString":
            for ln in g["coordinates"]:
                check_positions(ln, where)
        elif t in ("Polygon", "MultiPolygon"):
            polys = [g["coordinates"]] if t == "Polygon" else g["coordinates"]
            for poly in polys:
                for ring in poly:
                    check_positions(ring, where)
                    if ring[0] != ring[-1] or len(ring) < 4:
                        problems.append(f"{where}: ring not closed / too short")
                shp = Polygon(poly[0], poly[1:])
                if not shp.is_valid:
                    problems.append(f"{where}: invalid polygon")
        else:
            problems.append(f"{where}: unexpected geometry {t}")
    return problems


def bbox_of(features: list[dict]) -> Optional[list[float]]:
    """RFC 7946 sec. 5.2 bbox; west > east when it crosses the antimeridian."""
    xs, ys = [], []

    def walk(c):
        if isinstance(c[0], (int, float)):
            xs.append(c[0]); ys.append(c[1])
        else:
            for cc in c:
                walk(cc)
    for f in features:
        walk(f["geometry"]["coordinates"])
    if not xs:
        return None
    lons = np.unique(np.round(np.asarray(xs) % 360, 6))
    gaps = np.diff(np.concatenate([lons, [lons[0] + 360]]))
    i = int(np.argmax(gaps))
    west, east = lons[(i + 1) % len(lons)], lons[i]
    to180 = lambda v: float(round((v + 180) % 360 - 180, 3))  # noqa: E731
    if gaps[i] < 1e-9 or lons[-1] - lons[0] < 1e-9:
        west, east = -180.0, 180.0
    else:
        west, east = to180(west), to180(east)
    if gaps.max() <= 360 / len(lons) * 1.5:   # covers all longitudes
        west, east = -180.0, 180.0
    return [west, round(min(ys), 3), east, round(max(ys), 3)]


def suggested_view(center: Optional["GeoPoint"]) -> str:
    if center is None:
        return "global"
    if center.lat > 60:
        return "polar_north"
    if center.lat < -60:
        return "polar_south"
    return "mercator"


def build_layers(features: list[dict], spec: list[tuple]) -> list[Layer]:
    layers = []
    for z, (lid, kind, default_visible) in enumerate(spec):
        count = sum(1 for f in features if f["properties"]["layer"] == lid)
        if count:
            layers.append(Layer(id=lid, geometry_kind=kind, label_key=f"eclipseMap.layers.{lid}",
                                feature_count=count, default_visible=default_visible, z_index=z))
    return layers


def accuracy_for(year: float, sigma_s: float, extra_notes: list[str]) -> Accuracy:
    lon_unc = sigma_s * SIDEREAL_DEG_PER_SECOND
    if 1800 <= year <= 2200 and sigma_s <= 10:
        confidence = "high"
    elif lon_unc <= 0.5:
        confidence = "medium"
    else:
        confidence = "low"
    notes = list(extra_notes)
    if confidence != "high":
        notes.append("Delta T uncertainty shifts all geometry east-west; show as a band, not a line.")
    return Accuracy(confidence=confidence,
                    longitude_uncertainty_deg=round(lon_unc, 4),
                    along_track_uncertainty_km=round(lon_unc * math.pi / 180 * A_KM, 1),
                    notes=notes)


# ---------------------------------------------------------------------------
# Solar eclipse map
# ---------------------------------------------------------------------------

SHADOW_INDETERMINATE_BAND = 0.003   # fundamental-plane units (~19 km) either side of contact
MAGNITUDE_BANDS = [(1e-4, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 10.0)]
SOLAR_LAYER_SPEC = [
    ("partial_envelope", "polygon", True),
    ("magnitude_bands", "polygon", True),
    ("umbral_path", "polygon", True),
    ("northern_limit", "line", True),
    ("southern_limit", "line", True),
    ("central_line", "line", True),
    ("greatest_eclipse", "point", True),
]


def central_details(b: Besselian, lat, lon):
    """Local circumstances for observers at (lat, lon) at the matching samples."""
    xi, eta, zeta, h, rc = observer_coords(lat, lon, b.d, b.mu)
    big_l1 = b.l1 - zeta * b.tan_f1
    big_l2 = b.l2 - zeta * b.tan_f2
    a_ = b.x_dot - b.mu_dot * rc * np.cos(h)
    c_ = b.y_dot - (b.mu_dot * xi * np.sin(b.d) - zeta * b.d_dot)
    n = np.hypot(a_, c_)
    return {
        "L1": big_l1, "L2": big_l2,
        "duration_s": 7200.0 * np.abs(big_l2) / n,
        "sun_alt_deg": np.degrees(np.arcsin(np.clip(zeta, -1, 1))),
        "magnitude": (big_l1 - big_l2) / (big_l1 + big_l2),
    }


def umbral_limits(b: Besselian):
    """Northern/southern umbral (antumbral) limits, iterated on the ellipsoid."""
    sides = {}
    for side in (1, -1):
        xi, eta = b.x.copy(), b.y.copy()
        for _ in range(8):
            lat, lon, _ = fundamental_to_geodetic(xi, eta, b.d, b.mu)
            xo, _eo, zo, h, rc = observer_coords(lat, lon, b.d, b.mu)
            big_l2 = np.abs(b.l2 - zo * b.tan_f2)
            a_ = b.x_dot - b.mu_dot * rc * np.cos(h)
            c_ = b.y_dot - (b.mu_dot * xo * np.sin(b.d) - zo * b.d_dot)
            n = np.hypot(a_, c_)
            xi = b.x + side * big_l2 * c_ / n
            eta = b.y - side * big_l2 * a_ / n
        lat, lon, valid = fundamental_to_geodetic(xi, eta, b.d, b.mu)
        sides[side] = (np.where(valid, lat, np.nan), np.where(valid, lon, np.nan))
    north, south = (sides[1], sides[-1])
    if np.nanmean(north[0]) < np.nanmean(south[0]):
        north, south = south, north
    return north, south


def solar_magnitude_raster(b: Besselian, grid_deg: float):
    lats = np.arange(-90, 90 + grid_deg / 2, grid_deg)
    lons = np.arange(-180, 180 + grid_deg / 2, grid_deg)
    lat_r, lon_r = np.meshgrid(np.radians(lats), np.radians(lons), indexing="ij")
    rc, rs = rho_terms(lat_r)
    best = np.zeros(lat_r.shape)
    for k in range(len(b.x)):
        h = b.mu[k] + lon_r
        ch = np.cos(h)
        sd, cd = math.sin(b.d[k]), math.cos(b.d[k])
        xi = rc * np.sin(h)
        eta = rs * cd - rc * ch * sd
        zeta = rs * sd + rc * ch * cd
        big_l1 = b.l1[k] - zeta * b.tan_f1[k]
        big_l2 = b.l2[k] - zeta * b.tan_f2[k]
        mag = (big_l1 - np.hypot(b.x[k] - xi, b.y[k] - eta)) / (big_l1 + big_l2)
        mag[zeta <= 0] = 0.0
        np.maximum(best, mag, out=best)
    return lons, lats, best


def runs(values: np.ndarray):
    """Yield (value, start, stop_inclusive) for consecutive equal values."""
    start = 0
    for i in range(1, len(values) + 1):
        if i == len(values) or values[i] != values[start]:
            yield values[start], start, i - 1
            start = i


def ut_of(jd_tt: float, dt_s: float) -> str:
    return format_ut(jd_tt - dt_s / 86400)[0]


def find_solar_greatest(jd_guess_tt: float, dt_s: float) -> Optional[float]:
    coarse = jd_guess_tt + np.arange(-1.5, 1.5 + 1e-9, 1 / 96)
    b = besselian(coarse, dt_s)
    dist = np.where(b.z > 0, np.hypot(b.x, b.y), np.inf)
    i = int(np.argmin(dist))
    if i in (0, len(coarse) - 1):
        return None
    fine = coarse[i] + np.arange(-1800, 1800 + 1, 10) / 86400
    bf = besselian(fine, dt_s)
    return parabolic_min(fine, np.hypot(bf.x, bf.y))


def solar_map(date_text: str, grid_deg: float, dt_override: Optional[float] = None):
    timings = {}
    t0 = time.perf_counter()
    jd_noon_ut = parse_date(date_text) + 0.5
    year = jd_to_year(jd_noon_ut)
    dt_s = dt_override if dt_override is not None else delta_t_espenak_meeus(year)
    sigma = delta_t_sigma(year)
    time_model = TimeModel(delta_t_s=round(dt_s, 2), delta_t_sigma_s=round(sigma, 1),
                           delta_t_source="override" if dt_override is not None else "espenak_meeus_2006",
                           ephemeris="astropy-builtin (ERFA epv00 Sun, ELP-2000/82 Moon)")
    query = {"kind": "solar", "date": date_text}
    acc_notes = ["Shadow edges use mean lunar radius; limb profile can move limits ~1 km."]

    t_ge = find_solar_greatest(jd_noon_ut + dt_s / 86400, dt_s)
    if t_ge is None:
        env = VisibilityMapResponse(
            schema_version=SCHEMA_VERSION, algorithm_revision=ALGORITHM_REVISION,
            map_status="not_eclipse", query=query,
            no_eclipse=NoEclipseDetail(reason="no_syzygy_in_window"),
            time_model=time_model, accuracy=accuracy_for(year, sigma, acc_notes))
        return env, {"timings": timings}

    jd = t_ge + np.arange(-4 * 3600, 4 * 3600 + 1, 15) / 86400
    b = besselian(jd, dt_s)
    bg = besselian(t_ge + np.array([-30, 0, 30]) / 86400, dt_s).take(slice(1, 2))
    timings["elements_s"] = time.perf_counter() - t0

    rho1 = np.sqrt(1 - E2 * np.cos(b.d) ** 2)
    m_ell = np.hypot(b.x, b.y / rho1)
    pen_margin = (1 + b.l1) - m_ell
    max_margin = float(pen_margin.max())
    gamma = float(np.sign(bg.y[0]) * np.hypot(bg.x[0], bg.y[0]))

    if max_margin < SHADOW_INDETERMINATE_BAND:
        status = "not_eclipse" if max_margin < -SHADOW_INDETERMINATE_BAND else "indeterminate"
        warnings_ = [] if status == "not_eclipse" else [WarningItem(
            code="SHADOW_GRAZE", message_key="eclipseMap.warnings.shadowGraze",
            params={"margin": round(max_margin, 5)})]
        env = VisibilityMapResponse(
            schema_version=SCHEMA_VERSION, algorithm_revision=ALGORITHM_REVISION,
            map_status=status, query=query,
            no_eclipse=(NoEclipseDetail(reason="outside_shadow",
                                        nearest_syzygy=time_instant(t_ge, dt_s),
                                        shadow_margin=round(max_margin, 5))
                        if status == "not_eclipse" else None),
            time_model=time_model, accuracy=accuracy_for(year, sigma, acc_notes),
            warnings=warnings_)
        return env, {"gamma": gamma, "timings": timings, "max_margin": max_margin}

    window = np.where(pen_margin > 0)[0]
    w0, w1 = int(window[0]), int(window[-1])

    # --- central line, local type, limits -------------------------------------
    t1 = time.perf_counter()
    central = (b.x ** 2 + (b.y / rho1) ** 2) < 1
    cidx = np.where(central)[0]
    features: list[dict] = []
    local_types: list[str] = []
    width_km = duration_s = None
    if len(cidx):
        bc = b.take(cidx)
        lat, lon, _ = fundamental_to_geodetic(bc.x, bc.y, bc.d, bc.mu)
        det = central_details(bc, lat, lon)
        types = np.where(det["L2"] < 0, "total", "annular")
        local_types = sorted(set(types.tolist()))
        (nlat, nlon), (slat, slon) = umbral_limits(bc)
        for typ, s, e in runs(types):
            e2 = min(e + 1, len(cidx) - 1)
            props = {"local_type": str(typ), "start": ut_of(bc.jd_tt[s], dt_s),
                     "end": ut_of(bc.jd_tt[e2], dt_s)}
            seg = slice(s, e2 + 1)
            features += line_features(np.degrees(lon[seg]), np.degrees(lat[seg]),
                                      {"layer": "central_line", **props})
            ring_lon = np.concatenate([np.degrees(nlon[seg]), np.degrees(slon[seg])[::-1]])
            ring_lat = np.concatenate([np.degrees(nlat[seg]), np.degrees(slat[seg])[::-1]])
            features += ring_polygon_features(ring_lon, ring_lat, {"layer": "umbral_path", **props})
        features += line_features(np.degrees(nlon), np.degrees(nlat), {"layer": "northern_limit"})
        features += line_features(np.degrees(slon), np.degrees(slat), {"layer": "southern_limit"})
    elif float(((1 + np.abs(b.l2)) - m_ell).max()) > 0:
        local_types = ["total" if bg.l2[0] < 0 else "annular"]   # non-central umbral graze
    timings["central_s"] = time.perf_counter() - t1

    # --- greatest eclipse point ----------------------------------------------
    bg3 = besselian(t_ge + np.array([-30, 0, 30]) / 86400, dt_s)
    is_central = bool(bg.x[0] ** 2 + (bg.y[0] / math.sqrt(1 - E2 * math.cos(bg.d[0]) ** 2)) ** 2 < 1)
    if is_central:
        glat, glon, _ = fundamental_to_geodetic(bg.x, bg.y, bg.d, bg.mu)
        det = central_details(bg3.take(slice(1, 2)), glat, glon)
        magnitude = float(det["magnitude"][0])
        duration_s = float(det["duration_s"][0])
        sun_alt = float(det["sun_alt_deg"][0])
        (nl, nlo), (sl, slo) = umbral_limits(bg3.take(slice(1, 2)))
        if np.isfinite([nl[0], sl[0]]).all():
            width_km = haversine_km(nl[0], nlo[0], sl[0], slo[0])
    else:
        m_g = math.hypot(bg.x[0], bg.y[0] / math.sqrt(1 - E2 * math.cos(bg.d[0]) ** 2))
        glat, glon, _ = fundamental_to_geodetic(bg.x / m_g, bg.y / m_g, bg.d, bg.mu)
        delta = math.hypot(bg.x[0], bg.y[0]) * (1 - 1 / m_g)
        magnitude = float((bg.l1[0] - delta) / (bg.l1[0] + bg.l2[0]))
        sun_alt = 0.0
    gpoint = GeoPoint(lat=round(math.degrees(glat[0]), 4), lon=round(math.degrees(glon[0]), 4))
    features.append({"type": "Feature",
                     "geometry": {"type": "Point", "coordinates": [gpoint.lon, gpoint.lat]},
                     "properties": {"layer": "greatest_eclipse", "time": ut_of(t_ge, dt_s),
                                    "magnitude": round(magnitude, 5),
                                    "sun_altitude_deg": round(sun_alt, 1),
                                    "duration_s": None if duration_s is None else round(duration_s, 1)}})

    # --- partial visibility raster -> magnitude bands -------------------------
    t2 = time.perf_counter()
    sub = np.arange(w0, w1 + 1, 4)                        # 1-minute sampling
    lons, lats, mag = solar_magnitude_raster(b.take(sub), grid_deg)
    timings["raster_s"] = time.perf_counter() - t2
    t3 = time.perf_counter()
    simplify = grid_deg / 4
    env_polys = filled_band_polygons(lons, lats, mag, 1e-4, 10.0, simplify)
    features += polygons_to_features(env_polys, {"layer": "partial_envelope"}, 2)
    for lo, hi in MAGNITUDE_BANDS:
        polys = filled_band_polygons(lons, lats, mag, lo, hi, simplify)
        features += polygons_to_features(polys, {"layer": "magnitude_bands", "magnitude_min": lo,
                                                 "magnitude_max": None if hi >= 10 else hi}, 2)
    timings["contours_s"] = time.perf_counter() - t3

    # --- classification ------------------------------------------------------
    if "total" in local_types and "annular" in local_types:
        classification = "hybrid"
    elif local_types:
        classification = local_types[0]
    else:
        classification = "partial"
    calendar_type = ("total" if "total" in local_types
                     else "annular" if "annular" in local_types else "partial")
    contacts = {
        "eclipse_begins": time_instant(b.jd_tt[w0], dt_s),
        "central_phase_begins": time_instant(b.jd_tt[cidx[0]], dt_s) if len(cidx) else None,
        "central_phase_ends": time_instant(b.jd_tt[cidx[-1]], dt_s) if len(cidx) else None,
        "eclipse_ends": time_instant(b.jd_tt[w1], dt_s),
    }
    ge = time_instant(t_ge, dt_s)
    event = EventSummary(
        event_id=f"solar-{ge.ut[:ge.ut.index('T')]}", kind="solar",
        calendar_type=calendar_type, classification=classification,
        centrality=("central" if len(cidx) else "non_central") if local_types else None,
        local_types_present=sorted(set(local_types) | {"partial"}),
        greatest_eclipse=ge, greatest_point=gpoint, gamma=round(gamma, 5),
        magnitude=round(magnitude, 5),
        central_duration_s=None if duration_s is None else round(duration_s, 1),
        path_width_km=None if width_km is None else round(width_km, 1),
        contacts=contacts)

    focus = [f for f in features if f["properties"]["layer"] in ("umbral_path", "central_line")]
    bbox = bbox_of(focus or [f for f in features if f["properties"]["layer"] == "partial_envelope"])
    warnings_ = []
    if "hybrid" == classification:
        warnings_.append(WarningItem(code="HYBRID_PATH", message_key="eclipseMap.warnings.hybrid",
                                     params={"local_types": local_types}))
    env = VisibilityMapResponse(
        schema_version=SCHEMA_VERSION, algorithm_revision=ALGORITHM_REVISION, map_status="ready",
        query=query, event=event,
        geometry={"type": "FeatureCollection", "features": features},
        layers=build_layers(features, SOLAR_LAYER_SPEC), time_model=time_model,
        accuracy=accuracy_for(year, sigma, acc_notes),
        view_hints=ViewHints(bbox=bbox, center=gpoint, suggested_view=suggested_view(gpoint)),
        warnings=warnings_)
    timings["total_s"] = time.perf_counter() - t0
    return env, {"timings": timings, "dt_s": dt_s,
                 "central_points": int(len(cidx)), "max_margin": max_margin}


# ---------------------------------------------------------------------------
# Lunar eclipse map
# ---------------------------------------------------------------------------

LUNAR_INDETERMINATE_MAG = 0.005
LUNAR_LAYER_SPEC = [
    ("visible_partly", "polygon", True),
    ("visible_entire_eclipse", "polygon", True),
    ("totality_visible", "polygon", False),
    ("moon_horizon_at_contact", "line", False),
    ("sublunar_track", "line", True),
    ("contact_points", "point", True),
    ("greatest_eclipse", "point", True),
]


def lunar_quantities(jd_tt: np.ndarray, dt_s: float) -> dict:
    """Danjon shadow radii and Moon geometry (radians)."""
    jd_tt = np.atleast_1d(jd_tt)
    s, m = sun_moon_tete_km(jd_tt)
    ds, dm = np.linalg.norm(s, axis=0), np.linalg.norm(m, axis=0)
    anti, mh = -s / ds, m / dm
    sep = np.arccos(np.clip((anti * mh).sum(axis=0), -1, 1))
    pi_m, pi_s = np.arcsin(A_KM / dm), np.arcsin(A_KM / ds)
    s_s, s_m = np.arcsin(R_SUN_KM / ds), np.arcsin(K_PENUMBRA * A_KM / dm)
    pi1 = 0.998340 * pi_m
    ru, rp = 1.01 * pi1 + pi_s - s_s, 1.01 * pi1 + pi_s + s_s
    dec = np.arcsin(mh[2])
    return {
        "jd": jd_tt, "sep": sep, "ru": ru, "rp": rp, "s_m": s_m, "pi_m": pi_m,
        "ra": np.arctan2(mh[1], mh[0]), "dec": dec, "gast": gast_rad(jd_tt, dt_s),
        "umag": (ru + s_m - sep) / (2 * s_m), "pmag": (rp + s_m - sep) / (2 * s_m),
        "gamma": np.sign(dec - np.arcsin(anti[2])) * np.sin(sep) * dm / A_KM,
    }


def _first_last_crossing(jd: np.ndarray, f: np.ndarray):
    pos = np.where(f > 0)[0]
    if not len(pos):
        return None, None
    i0, i1 = int(pos[0]), int(pos[-1])

    def interp(a, b):
        return float(jd[a] + (0 - f[a]) / (f[b] - f[a]) * (jd[b] - jd[a]))
    start = interp(i0 - 1, i0) if i0 > 0 else float(jd[i0])
    end = interp(i1, i1 + 1) if i1 < len(jd) - 1 else float(jd[i1])
    return start, end


def sublunar(q: dict, i) -> tuple[float, float]:
    lon = (math.degrees(q["ra"][i] - q["gast"][i]) + 180) % 360 - 180
    return math.degrees(q["dec"][i]), lon


def lunar_map(date_text: str, grid_deg: float, dt_override: Optional[float] = None):
    timings = {}
    t0 = time.perf_counter()
    jd_noon_ut = parse_date(date_text) + 0.5
    year = jd_to_year(jd_noon_ut)
    dt_s = dt_override if dt_override is not None else delta_t_espenak_meeus(year)
    sigma = delta_t_sigma(year)
    time_model = TimeModel(delta_t_s=round(dt_s, 2), delta_t_sigma_s=round(sigma, 1),
                           delta_t_source="override" if dt_override is not None else "espenak_meeus_2006",
                           ephemeris="astropy-builtin (ERFA epv00 Sun, ELP-2000/82 Moon)")
    query = {"kind": "lunar", "date": date_text}
    acc_notes = ["Contact times are global; Moon-up regions ignore refraction (~0.6 deg)."]
    accuracy = accuracy_for(year, sigma, acc_notes)

    coarse = jd_noon_ut + dt_s / 86400 + np.arange(-1.5, 1.5 + 1e-9, 1 / 96)
    qc = lunar_quantities(coarse, dt_s)
    i = int(np.argmin(qc["sep"]))
    if i in (0, len(coarse) - 1):
        return VisibilityMapResponse(
            schema_version=SCHEMA_VERSION, algorithm_revision=ALGORITHM_REVISION,
            map_status="not_eclipse", query=query,
            no_eclipse=NoEclipseDetail(reason="no_syzygy_in_window"),
            time_model=time_model, accuracy=accuracy), {"timings": timings}
    fine = coarse[i] + np.arange(-1800, 1801, 10) / 86400
    t_ge = parabolic_min(fine, lunar_quantities(fine, dt_s)["sep"])
    qg = lunar_quantities(np.array([t_ge]), dt_s)
    pmag, umag = float(qg["pmag"][0]), float(qg["umag"][0])

    if pmag < LUNAR_INDETERMINATE_MAG:
        status = "not_eclipse" if pmag < -LUNAR_INDETERMINATE_MAG else "indeterminate"
        return VisibilityMapResponse(
            schema_version=SCHEMA_VERSION, algorithm_revision=ALGORITHM_REVISION,
            map_status=status, query=query,
            no_eclipse=(NoEclipseDetail(reason="outside_shadow", nearest_syzygy=time_instant(t_ge, dt_s),
                                        shadow_margin=round(pmag, 5))
                        if status == "not_eclipse" else None),
            time_model=time_model, accuracy=accuracy,
            warnings=[] if status == "not_eclipse" else [WarningItem(
                code="SHADOW_GRAZE", message_key="eclipseMap.warnings.shadowGraze",
                params={"penumbral_magnitude": round(pmag, 5)})]), {"timings": timings}

    jd = t_ge + np.arange(-5 * 3600, 5 * 3600 + 1, 20) / 86400
    q = lunar_quantities(jd, dt_s)
    p1, p4 = _first_last_crossing(jd, q["rp"] + q["s_m"] - q["sep"])
    u1, u4 = _first_last_crossing(jd, q["ru"] + q["s_m"] - q["sep"])
    u2, u3 = _first_last_crossing(jd, q["ru"] - q["s_m"] - q["sep"])
    classification = "total" if umag >= 1 else "partial" if umag > 0 else "penumbral"
    timings["contacts_s"] = time.perf_counter() - t0

    # --- Moon-up visibility per phase on a global grid ------------------------
    t1 = time.perf_counter()
    lats = np.arange(-90, 90 + grid_deg / 2, grid_deg)
    lons = np.arange(-180, 180 + grid_deg / 2, grid_deg)
    lat_r, lon_r = np.meshgrid(np.radians(lats), np.radians(lons), indexing="ij")
    sin_lat, cos_lat = np.sin(lat_r), np.cos(lat_r)

    def moon_alt(qq, k):
        sa = (sin_lat * math.sin(qq["dec"][k])
              + cos_lat * math.cos(qq["dec"][k]) * np.cos(qq["gast"][k] + lon_r - qq["ra"][k]))
        alt = np.arcsin(np.clip(sa, -1, 1))
        return alt - qq["pi_m"][k] * np.cos(alt)        # topocentric (parallax) correction

    def fraction_visible(start, end):
        n = max(2, int(math.ceil((end - start) * 1440 / 5)) + 1)
        qq = lunar_quantities(np.linspace(start, end, n), dt_s)
        count = np.zeros(lat_r.shape)
        for k in range(n):
            count += moon_alt(qq, k) > 0
        return count / n, qq

    frac_pen, q_track = fraction_visible(p1, p4)
    features: list[dict] = []
    simplify = grid_deg / 4
    features += polygons_to_features(filled_band_polygons(lons, lats, frac_pen, 1e-6, 0.999, simplify),
                                     {"layer": "visible_partly", "phase": "penumbral"}, 2)
    features += polygons_to_features(filled_band_polygons(lons, lats, frac_pen, 0.999, 1.5, simplify),
                                     {"layer": "visible_entire_eclipse", "phase": "penumbral"}, 2)
    if u2 is not None:
        frac_tot, _ = fraction_visible(u2, u3)
        features += polygons_to_features(
            filled_band_polygons(lons, lats, frac_tot, 0.999, 1.5, simplify),
            {"layer": "totality_visible", "phase": "total"}, 2)
    contacts_jd = {"p1": p1, "u1": u1, "u2": u2, "greatest": t_ge, "u3": u3, "u4": u4, "p4": p4}
    present = {k: v for k, v in contacts_jd.items() if v is not None}
    qk = lunar_quantities(np.array(list(present.values())), dt_s)
    for k, (name, jdv) in enumerate(present.items()):
        lat_c, lon_c = sublunar(qk, k)
        layer = "greatest_eclipse" if name == "greatest" else "contact_points"
        features.append({"type": "Feature",
                         "geometry": {"type": "Point", "coordinates": [round(lon_c, 4), round(lat_c, 4)]},
                         "properties": {"layer": layer, "contact": name, "time": ut_of(jdv, dt_s)}})
        alt = np.degrees(moon_alt(qk, k))
        for seg in contour_lines(lons, lats, alt, 0.0):
            features += line_features(seg[:, 0], seg[:, 1],
                                      {"layer": "moon_horizon_at_contact", "contact": name}, 2)
    track = [sublunar(q_track, k) for k in range(len(q_track["jd"]))]
    features += line_features([t[1] for t in track], [t[0] for t in track], {"layer": "sublunar_track"})
    timings["visibility_s"] = time.perf_counter() - t1

    glat, glon = sublunar(qg, 0)
    ge = time_instant(t_ge, dt_s)
    event = EventSummary(
        event_id=f"lunar-{ge.ut[:ge.ut.index('T')]}", kind="lunar",
        calendar_type=classification, classification=classification,
        greatest_eclipse=ge, greatest_point=GeoPoint(lat=round(glat, 4), lon=round(glon, 4)),
        gamma=round(float(qg["gamma"][0]), 5), magnitude=round(umag, 5),
        penumbral_magnitude=round(pmag, 5),
        contacts={k: (time_instant(v, dt_s) if v is not None else None)
                  for k, v in contacts_jd.items() if k != "greatest"})
    env = VisibilityMapResponse(
        schema_version=SCHEMA_VERSION, algorithm_revision=ALGORITHM_REVISION, map_status="ready",
        query=query, event=event, geometry={"type": "FeatureCollection", "features": features},
        layers=build_layers(features, LUNAR_LAYER_SPEC), time_model=time_model, accuracy=accuracy,
        view_hints=ViewHints(bbox=[-180, -90, 180, 90], center=event.greatest_point,
                             suggested_view="global"))
    timings["total_s"] = time.perf_counter() - t0
    return env, {"timings": timings, "dt_s": dt_s,
                 "durations_s": {"penumbral": (p4 - p1) * 86400,
                                 "umbral": None if u1 is None else (u4 - u1) * 86400,
                                 "total": None if u2 is None else (u3 - u2) * 86400}}


# ---------------------------------------------------------------------------
# Reference cases. Values from NASA GSFC / EclipseWise (Espenak) as surfaced via
# web search on 2026-xx (direct NASA/JPL access was unavailable). `None` = not
# asserted. TD = Terrestrial Dynamical Time (independent of Delta T).
# ---------------------------------------------------------------------------

SOLAR_CASES = [
    {"date": "2024-04-08", "expect": "ready", "classification": "total", "calendar_type": "total",
     "td": "18:18:29", "lat": 25.3, "lon": -104.1, "gamma": 0.3431, "mag": 1.0566,
     "duration_s": 268, "width_km": 198, "delta_t": 74.0},
    {"date": "2023-04-20", "expect": "ready", "classification": "hybrid", "calendar_type": "total",
     "td": "04:17:56", "lat": -9.6, "lon": 125.8, "gamma": -0.3952, "mag": 1.0132,
     "duration_s": 76, "width_km": 49},
    {"date": "2023-10-14", "expect": "ready", "classification": "annular", "calendar_type": "annular",
     "td": "18:00:41", "lat": 11.4, "lon": -83.1, "gamma": 0.3753, "mag": 0.9520,
     "duration_s": 317, "width_km": 187},
    {"date": "2025-03-29", "expect": "ready", "classification": "partial", "calendar_type": "partial",
     "td": "10:48:36", "lat": 61.1, "lon": -77.1, "gamma": 1.0405, "mag": 0.9376},
    {"date": "2026-08-12", "expect": "ready", "classification": "total", "calendar_type": "total",
     "td": "17:47:06", "lat": 65.2, "lon": -25.2, "gamma": 0.8977, "mag": 1.0386,
     "duration_s": 138, "width_km": 294},
    {"date": "1919-05-29", "expect": "ready", "classification": "total", "calendar_type": "total",
     "td": "13:08:55", "lat": 4.38, "lon": -16.71, "gamma": -0.2955, "mag": 1.0719,
     "duration_s": 411, "width_km": 244, "delta_t": 21.0},
    {"date": "2021-12-04", "expect": "ready", "classification": "total", "calendar_type": "total"},
    {"date": "2025-08-23", "expect": "not_eclipse"},
    # Thales' eclipse (Julian calendar, astronomical year -584 = 585 BC). Only
    # the type and "central line crosses Asia Minor" are asserted.
    {"date": "-0584-05-28", "expect": "ready", "classification": "total", "calendar_type": "total",
     "crosses_box": (26.0, 36.0, 45.0, 42.0)},
]

LUNAR_CASES = [
    {"date": "2025-09-07", "expect": "ready", "classification": "total", "td": "18:12:58",
     "umag": 1.3638, "pmag": 2.3459, "gamma": -0.2752,
     "durations_s": {"penumbral": 19642, "umbral": 12602, "total": 4962}},
    {"date": "2024-09-18", "expect": "ready", "classification": "partial"},
    {"date": "2024-03-25", "expect": "ready", "classification": "penumbral"},
    {"date": "2025-08-09", "expect": "not_eclipse"},
]

TOL = {"td_s": 20, "latlon_deg": 0.3, "gamma": 0.002, "mag": 0.003, "duration_frac": 0.05,
       "width_frac": 0.05, "umag": 0.01, "pmag": 0.01, "lunar_duration_s": 90}


class Checker:
    def __init__(self):
        self.rows = []

    def add(self, case, metric, got, ref, ok, note=""):
        self.rows.append((case, metric, got, ref, ok, note))

    def approx(self, case, metric, got, ref, tol):
        if ref is None:
            return
        ok = got is not None and abs(got - ref) <= tol
        self.add(case, metric, None if got is None else round(got, 4), ref, ok, f"±{tol}")

    def equal(self, case, metric, got, ref):
        if ref is not None:
            self.add(case, metric, got, ref, got == ref)

    @property
    def failures(self):
        return [r for r in self.rows if not r[4]]


def td_seconds_of_day(jd_tt: float) -> float:
    return ((jd_tt + 0.5) % 1.0) * 86400


def hms_to_s(text: str) -> float:
    h, m, s = (float(v) for v in text.split(":"))
    return h * 3600 + m * 60 + s


def line_crosses_box(fc: dict, layer: str, box_: tuple) -> bool:
    w, s, e, n = box_
    for f in fc["features"]:
        if f["properties"]["layer"] != layer:
            continue
        g = f["geometry"]
        lines = [g["coordinates"]] if g["type"] == "LineString" else g["coordinates"]
        for ln in lines:
            if LineString(ln).intersects(box(w, s, e, n)):
                return True
    return False


def calendar_classification(env: VisibilityMapResponse) -> Optional[str]:
    """Run the *current* calendar classifier at the computed greatest eclipse."""
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from api.services.eclipse_detection import check_eclipse_at_time  # noqa: WPS433
    jd = env.event.greatest_eclipse.tt_jd if env.event else env.no_eclipse.nearest_syzygy.tt_jd
    t = Time(jd, format="jd", scale="tt").utc
    res = check_eclipse_at_time(t, is_lunar=env.query["kind"] == "lunar")
    return res["eclipse_type"].lower() if res["is_eclipse"] else "none"


def run_case(kind: str, case: dict, grid_deg: float, checker: Checker, use_calendar: bool,
             output_dir: Optional[Path]):
    fn = solar_map if kind == "solar" else lunar_map
    started = time.perf_counter()
    env, diag = fn(case["date"], grid_deg, case.get("delta_t"))
    diag["wall_s"] = time.perf_counter() - started
    label = f"{kind} {case['date']}"
    payload = env.model_dump(mode="json")
    VisibilityMapResponse.model_validate(payload)              # round-trip contract check
    body = json.dumps(payload, separators=(",", ":"))
    checker.equal(label, "map_status", env.map_status, case["expect"])
    if env.geometry is not None:
        problems = validate_feature_collection(env.geometry)
        checker.add(label, "geojson_valid", len(problems), 0, not problems, "; ".join(problems[:3]))
    ev = env.event
    if ev is not None:
        checker.equal(label, "classification", ev.classification, case.get("classification"))
        checker.equal(label, "calendar_type", ev.calendar_type, case.get("calendar_type"))
        if case.get("td"):
            diff = td_seconds_of_day(ev.greatest_eclipse.tt_jd) - hms_to_s(case["td"])
            checker.approx(label, "greatest_td_offset_s", diff, 0.0, TOL["td_s"])
        if kind == "solar":
            checker.approx(label, "lat", ev.greatest_point.lat, case.get("lat"), TOL["latlon_deg"])
            checker.approx(label, "lon", ev.greatest_point.lon, case.get("lon"), TOL["latlon_deg"])
            checker.approx(label, "gamma", ev.gamma, case.get("gamma"), TOL["gamma"])
            checker.approx(label, "magnitude", ev.magnitude, case.get("mag"), TOL["mag"])
            if case.get("duration_s"):
                checker.approx(label, "duration_s", ev.central_duration_s, case["duration_s"],
                               round(case["duration_s"] * TOL["duration_frac"], 1))
            if case.get("width_km"):
                checker.approx(label, "path_width_km", ev.path_width_km, case["width_km"],
                               round(case["width_km"] * TOL["width_frac"], 1))
            if case.get("crosses_box"):
                hit = line_crosses_box(env.geometry, "central_line", case["crosses_box"])
                checker.add(label, "central_line_in_asia_minor", hit, True, hit,
                            f"ΔT σ≈{env.time_model.delta_t_sigma_s:.0f}s ⇒ ±"
                            f"{env.accuracy.longitude_uncertainty_deg:.1f}° lon")
        else:
            checker.approx(label, "umbral_mag", ev.magnitude, case.get("umag"), TOL["umag"])
            checker.approx(label, "penumbral_mag", ev.penumbral_magnitude, case.get("pmag"), TOL["pmag"])
            checker.approx(label, "gamma", ev.gamma, case.get("gamma"), TOL["gamma"] * 2)
            for phase, ref in (case.get("durations_s") or {}).items():
                checker.approx(label, f"{phase}_duration_s", diag["durations_s"][phase], ref,
                               TOL["lunar_duration_s"])
    cal = None
    if use_calendar and (env.event or env.no_eclipse and env.no_eclipse.nearest_syzygy):
        year = jd_to_year((env.event.greatest_eclipse if env.event else env.no_eclipse.nearest_syzygy).tt_jd)
        if year >= 1900:
            cal = calendar_classification(env)
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"{kind}_{case['date']}.json").write_text(json.dumps(payload, indent=1))
    return env, diag, len(body), cal


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--grid-deg", type=float, default=1.0)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--no-calendar", action="store_true",
                        help="skip comparison with the current calendar classifier")
    parser.add_argument("--only", default=None, help="run a single date, e.g. 2023-04-20")
    args = parser.parse_args()

    checker = Checker()
    summary = []
    for kind, cases in (("solar", SOLAR_CASES), ("lunar", LUNAR_CASES)):
        for case in cases:
            if args.only and case["date"] != args.only:
                continue
            env, diag, size, cal = run_case(kind, case, args.grid_deg, checker,
                                            not args.no_calendar, args.output_dir)
            ev = env.event
            summary.append({
                "case": f"{kind} {case['date']}", "status": env.map_status,
                "map_calendar_type": ev.calendar_type if ev else "-",
                "classification": ev.classification if ev else "-",
                "current_calendar": cal or "n/a",
                "features": len(env.geometry["features"]) if env.geometry else 0,
                "payload_kib": round(size / 1024, 1),
                "time_s": round(diag["wall_s"], 2),
                "confidence": env.accuracy.confidence,
            })
            if cal is not None and ev is not None and cal != ev.calendar_type:
                checker.add(f"{kind} {case['date']}", "current_calendar_matches_map", cal,
                            ev.calendar_type, False, "known gap -> issue #275")

    print(f"\nGrid: {args.grid_deg}°   schema {SCHEMA_VERSION}   {ALGORITHM_REVISION}\n")
    cols = list(summary[0].keys())
    widths = {c: max(len(c), *(len(str(r[c])) for r in summary)) for c in cols}
    print("  ".join(c.ljust(widths[c]) for c in cols))
    for r in summary:
        print("  ".join(str(r[c]).ljust(widths[c]) for c in cols))

    print("\nReference checks")
    for case, metric, got, ref, ok, note in checker.rows:
        print(f"  {'PASS' if ok else 'FAIL'}  {case:<18} {metric:<30} got={got!s:<12} ref={ref!s:<10} {note}")
    known = [r for r in checker.failures if "#275" in r[5]]
    real = [r for r in checker.failures if "#275" not in r[5]]
    print(f"\n{len(checker.rows) - len(checker.failures)} passed, {len(real)} failed, "
          f"{len(known)} known calendar gaps (#275)")
    return 1 if real else 0


if __name__ == "__main__":
    sys.exit(main())
