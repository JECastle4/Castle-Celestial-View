# Global solar classification experiment

`validate_global_solar_eclipses.py` validates the known geometries for issue #275.
The validated implementation is now exposed by
`api/services/eclipse_classification.py`; map rendering remains out of scope.

## Production integration

The astronomical-events service resolves solar classification through
`classify_solar_eclipse` and uses the same geometry for global solar contacts.
POST, SSE and lazy contact eligibility retain the whole-event classification.
Response codes are independent of translated labels:

- `global_eclipse_type`: retains `HYBRID` when both strong phases occur.
- `maximum_eclipse_phase`: `TOTAL` for hybrids, otherwise the global phase.
- `classification_revision`: identifies the numerical/radius convention.
- `classification_warning`: makes out-of-range solar ephemeris circumstances
  explicit instead of claiming verified timing accuracy for the 2185 reference.
  The API resolves the warning from its language resources using the requested
  locale. Downloads preserve that localized text as `classificationWarning` in JSON (null
  when absent) and `Classification Warning` on every CSV row (empty when absent),
  including rows whose contact times could not be loaded.

Calendar labels describe **Maximum phase anywhere**, not the observer's local
phase. `date` remains the new/full-moon timestamp and `greatest_eclipse_time`
retains the legacy geocentric minimum-separation meaning. `size_ratio` remains a
geocentric diagnostic, so a hybrid can display Total with a ratio below one.
Solar contact keys retain first/last global penumbral and total-or-annular
footprint meanings; axis intersections and hybrid-transition times are not
substituted for footprint contacts. Calculation failures are errors, never an
alternative classification or no-eclipse fallback. SSE failures terminate with
`calculation-error` and do not emit successful completion metadata.

Lunar classification and contacts retain the existing shadow convention and
`lunar-shadow-v1` revision; the two marginal lunar reference failures are separate
follow-up work. The five solar hybrid expected failures have been cleared.

The research runner now calls the production numerical search directly, rather
than maintaining a second classifier. Its 23 synthetic checks and 84 catalog
sampling/seed variations pass against this shared core. Production classification,
contacts and events integration tests cover 94% of classifier statements.
Thirteen published contact comparisons use explicit 90--120 second tolerances:
these validate minute-scale global timing, not certified subsecond predictions.

Numerical responsibilities are separated into `eclipse_geometry.py` (cones and
daylight surface optimization), `eclipse_ephemeris.py` (shared phase/timing
calculations), and `eclipse_classification.py` (search orchestration and results).
Classification and contacts share a per-search geometry/surface cache. The legacy
detection entry points delegate downward without a circular service dependency.
Closest-approach, witness validation, central-path transitions, phase searches
and contact crossings are independently testable helpers; the refactor preserves
the sampling order and numerical tolerances of the validated model.
The service result groups immutable axis diagnostics in `central_path`
(`SolarCentralPath`); HTTP responses and research JSON retain their existing shapes.

## Run

The PEP 723 headers declare the research runner's dependencies. Production uses
the shared finite-distance geometry core in `api/services/eclipse_classification.py`
and declares SciPy in both `requirements.txt` and `pyproject.toml`.

```sh
uv run research/test_global_solar_geometry.py
uv run research/test_global_solar_references.py
uv run research/validate_global_solar_eclipses.py
uv run research/validate_global_solar_eclipses.py --step-seconds 60 --json
uv run research/validate_global_solar_eclipses.py --radius-model repository --json
uv run research/validate_global_solar_eclipses.py --date "2023-04-20 04:17"
uv run research/validate_global_solar_eclipses.py --reference-date 2003-05-31 --check-stability
```

Reference runs exit unsuccessfully for any wrong type, maximum-phase code, or
central/non-central status. Exceptions and astronomical warnings remain visible.
JSON includes numerical surface witnesses, radius convention, dependency versions,
revision, axis phase transitions, and performance counters. Approximate input times only seed the search; expected types are
never passed to the solver.
The CLI now loads all **21 solar cases** from the API reference fixture, rather
than maintaining a separate 15-case list. Lunar cases are intentionally excluded.
Two fixture entries have computed rather than independently published geometry;
the JSON output preserves that distinction as `reference_verification`.

`--reference-date` is repeatable. `--check-stability` repeats selected references
with half the time-grid spacing and a seed shifted by 17 minutes, asserting exact
global-type, maximum-phase, centrality, and hybrid-sequence parity. This is a sensitivity check,
not an independent reference or a proof that all grid alignments are safe.

## Geometry and search

Both apparent Sun and Moon vectors come from Astropy's bundled ephemeris in GCRS.
They are rotated together into CIRS using ERFA's precession/nutation matrix.
Earth is the WGS84 ellipsoid, oriented about the celestial intermediate pole.

For Sun-Moon distance `D`, the external tangent cone has
`sin(alpha) = (R_sun - R_moon) / D`. At distance `d` along the shadow axis its
signed radius is `(R_moon - d sin(alpha)) / cos(alpha)`. Positive radius gives
umbra; negative gives antumbra. The internal tangent gives the penumbral cone.
This replaces the production small-angle/geocentric-radius approximations.

The experiment searches an eight-hour interval around the supplied timestamp:

1. Find the axis/ellipsoid intersection interval by solving its discriminant.
   Inspect the near, daylight surface, not the back of Earth.
2. Inspect the central path, including explicit points just inside each end.
   This avoids skipping short annular segments such as the 2013 hybrid's.
3. Refine signed radius extrema along the central path, so narrow total phases
   such as the 1986 hybrid do not depend on catching a positive grid sample.
4. For phases not already demonstrated, optimize cone clearance on the daylight
   ellipsoid across the time grid and refine every sampled local maximum.
   Cone footprints can intersect Earth even when the axis never does; both
   non-central reference cases exercise this.
5. Check every retained witness by a separate apparent-disk angular-overlap
   calculation and verify that it lies on the daylight WGS84 surface.

The initial and supplementary time grids use vectorized ephemerides without
interpolating the Sun/Moon positions. A conservative spatial clearance bound
uses a sphere containing WGS84: the cone radius is bounded over Earth's axial
extent, and transverse distance is bounded below by axis offset minus Earth's
maximum radius. Negative bounds skip unnecessary surface optimizations;
positive bounds are never accepted as occurrence witnesses. Temporal maxima of
these bounds are also refined, including for axis-miss events, and the closest
approach is explicitly inspected even if it falls between grid samples.
Screened negative `searched_max_clearances_km` values may be upper bounds,
not measured surface maxima.

Surface optimization uses additional azimuth seeds and cached phase evaluations.
A validated strong-phase witness also supplies a partial-overlap witness,
avoiding a redundant penumbral search. Both window ends are checked regardless
of which phases were found; a hybrid cannot bypass search-window closure checks.

Both total and annular witnesses produce `global_type=HYBRID`, independently of
which is present at greatest eclipse. `maximum_phase=TOTAL` for a hybrid.
Partial and none require that neither stronger phase was found.

There is a 1-metre *numerical* clearance threshold and millisecond axis-root
tolerance. These are not estimates of physical accuracy. Non-convergence,
unbracketed searches, positive penumbral clearance at the window ends, invalid
witnesses, or a numerically borderline absent phase raise errors. Near-tangent
axis intersections within the scaled-ellipsoid 1-metre numerical tolerance also
raise instead of silently choosing central versus non-central.

`hybrid_sequence` and `axis_phase_transitions_utc` describe central-line phase
changes, not global footprint contact times. A detected transition without
validated witnesses for both phases is indeterminate rather than a total-only
or annular-only result.

## Observed reference results

The original reference fixture cites NASA/Espenak classifications and includes exact
expected types, not lists of acceptable alternatives. Dates are UTC dates.
All fifteen cases matched with NASA's radius convention at 120-second sampling.
The original ten cases also matched NASA's convention at 60-second sampling
and repository radii at 60-second sampling.

Explicit stability checks passed for 2003-05-31, 2013-11-03, 2014-04-29, and
2043-04-09: their classifications did not change with 60-second sampling or a
17-minute shifted search seed.

| Date | Expected and computed global type | Calendar maximum | Production classifier | Axis intersects Earth |
|---|---|---|---|---|
| 1986-10-03 | Hybrid | Total | Annular | Yes |
| 2005-04-08 | Hybrid | Total | Annular | Yes |
| 2013-11-03 | Hybrid | Total | Total | Yes |
| 2023-04-20 | Hybrid | Total | Annular | Yes |
| 2017-08-21 | Total | Total | Total | Yes |
| 2023-10-14 | Annular | Annular | Annular | Yes |
| 2025-03-29 | Partial | Partial | Partial | No |
| 2014-04-29 | Annular | Annular | Annular | No |
| 2043-04-09 | Total | Total | Total | No |
| 2023-05-19 | None | None | None | No |
| 2003-05-31 | Annular | Annular | Annular | Yes |
| 2022-10-25 | Partial | Partial | Partial | No |
| 2025-09-21 | Partial | Partial | Partial | No |
| 2026-02-17 | Annular | Annular | Annular | Yes |
| 2026-08-12 | Total | Total | Total | Yes |

For the 2023 hybrid, retained total and annular witnesses have roughly 22.67 km
and 5.45 km of cone clearance respectively with NASA radii. These are positive
existence witnesses, **not** independently validated greatest magnitudes, greatest
durations, map boundaries, or maximum-clearance instants.

The synthetic checks cover near-side selection, total/annular/partial/none,
non-central footprints, polar alignment, a night-side antumbra that must not
create a false hybrid, and local partial visibility during a globally total
event.

### Hardened solver validation (v4)

All 21 solar catalog cases match their exact global classification, calendar
maximum, centrality, and recorded hybrid sequence with NASA radii. The same
classifications also match with repository radii. Additional references include
the 2031 and 2049 hybrids, the 2185 central-one-limit total, the 2044
central-one-limit annular, the 2043 non-central annular and the tiny 2011 partial.

The regression suite repeats **every case** at:

- 120-second sampling and the reference seed;
- 60-second sampling and the reference seed;
- 600-second sampling with the seed shifted 17 minutes earlier;
- 120-second sampling with the seed shifted 91 seconds later.

All **84 runs** must agree exactly on classification and sequence. Serialized
central-axis interval boundaries and phase transitions must repeat within
0.02 seconds; this tests numerical repeatability, **not astronomical timing
accuracy**. Every saved witness is rechecked with a fresh ephemeris query at
its serialized timestamp. The 2013 initial annular segment must last between
10 and 20 seconds (computed as approximately 15.04 seconds with NASA radii).
There are also 23 synthetic/numerical tests, including a central path shorter
than the coarse time step, spatial-bound checks, batched/scalar ephemeris parity,
non-finite optimizer output, strict surface-witness validation and axis tangency.

Measured 120-second catalog runs took approximately 0.7-3.5 seconds per case in
this environment. The 2023 hybrid takes about 0.7 seconds, non-central 2014
annular about 2.4 seconds and negative control about 0.7 seconds, compared with
approximately 5.7, 9.9 and 9.3 seconds respectively before hardening. These are
local measurements, not production latency guarantees.

The marginal 1986 total witness remains about **25 metres** with NASA radii and
1.53 km with repository radii. Its type is repeatable, but its margins and phase
transition times remain sensitive to the chosen radius/limb convention.

## What "partial" means

A genuinely **globally partial** eclipse has no totality or annularity anywhere.
A **local partial** phase can occur during a total, annular, or hybrid global
event. An instantaneous assessment is also not a classification of a whole
event.

The experiment found no real-date example where the existing production
classifier reports Partial but this solver finds Total or Annular. Its partial
reference agrees. Therefore this research must not be described as demonstrating
that particular defect, or as proving that hybrids are the only possible errors
in the approximate production geometry.

## Edge-case coverage

The maximum-phase reference matrix now includes all three NASA arrangements:

| Published arrangement | Reference coverage |
|---|---|
| Central, two limits | Ordinary total 2017-08-21 and annular 2023-10-14 |
| Central, one limit | Annular 2003-05-31 |
| Non-central, one limit | Annular 2014-04-29 and total 2043-04-09 |

This covers **maximum-phase classification for examples of each arrangement**.
The validation script does not compute the number of track limits; the labels
above come from published references.

## API reference catalog

`tests/fixtures/eclipse_reference_cases.json` collects 30 solar and lunar cases
for the production implementation, exercised by
`tests/test_eclipse_reference_cases.py`. It covers every calendar type, all three
arrangements for both total and annular eclipses, `A-T-A` and `A-T` hybrids,
tiny/deep partial solar eclipses, and marginal lunar cases (shortest totality,
near-total partial, total penumbral, barely penumbral). Current failures are
strict xfails: the hybrids (#275) and two lunar cases where the production
shadow omits atmospheric enlargement (2015-04-04 reports Partial, 2016-08-18
reports No Eclipse).

Additional examples were derived with a Besselian-style limit scan
(`uv run research/scan_eclipse_arrangements.py 2001 2101`, about 4 minutes per
century). An eclipse
has two limits if the umbral/antumbral circle ever fits inside Earth's WGS84
projection on the fundamental plane, and is central if the axis ever meets it.
The scan reproduced NASA's published counts exactly: 228 eclipses, 78 partial,
0 central one-limit and 5 non-central (1901-2000); 224, 77, 2 central one-limit
annulars and 3 non-central (2001-2100); and the 6 and 7 hybrids per century.
Notable results:

- No central one-limit **total** occurs from 1801 to 2184. The catalog uses
  2185-07-26 (NASA type `Ts`).
- 2044-02-28 (central one-limit annular) and 2043-10-03 (non-central annular)
  are computed examples matching the century counts.
- 2026-02-17 has two limits despite gamma of about -0.974.
- No hybrid between 1901 and 2200 begins total and ends annular; 2013-11-03 is
  the only two-segment (`A-T`) hybrid. Non-central hybrids are not covered.

The 2003 case is particularly useful: the axis intersects Earth for only about
11.5 minutes, yet the eclipse is annular, not partial. The two non-central cases
demonstrate that an axis miss does not imply a partial eclipse: the finite-width
umbra or antumbra can still intersect Earth.

Six hybrids exercise annular-to-total transitions, including the short initial
annular segment in 2013 and the marginal 1986 event. Ordinary and additional
high-latitude partial references guard against falsely promoting a partial event.
The ordinary new-moon negative control guards against inventing an eclipse.
Partial/none axis-miss booleans are not NASA's "non-central, one limit" category:
that category applies to total and annular eclipses with a central-phase footprint.

The synthetic checks additionally cover near-/far-side selection,
non-central footprints, local partial during global total, polar alignment,
longitude-rotation invariance, exact cone tangency and 10-metre offsets on both
sides of the strong-phase/partial transition, invalid inputs, unsupported phases,
and optimizer non-convergence. Invalid/failing calculations raise rather than
returning a false `NONE`.

## Accuracy limits and production implications

This is positive evidence for the surface-cone approach, **not a certified
all-history solver** or production-ready map engine:

- Surface optimization is multi-start numerical search, not a rigorous global
  exclusion proof. Fixed-grid absence checks can still miss a sufficiently
  narrow unsampled feature. The spatial bound excludes phases only at evaluated
  times, not throughout arbitrary unsampled temporal intervals. Coverage is
  deliberately the known catalog, not a universal exclusion proof.
- The default uses NASA's eclipse convention: solar radius 696000 km,
  central lunar radius `0.272281 * 6378.137` km, and penumbral lunar radius
  `0.2725076 * 6378.137` km. The alternative uses the repository's nominal
  radii (695700 and 1737.4 km). These conventions are materially different.
- For the 1986 hybrid, the retained total witness drops from about 1.53 km with
  repository radii to **0.025 km** with NASA radii. Matching its type is not
  evidence of 25-metre astronomical accuracy: ephemeris and limb uncertainty
  could change this marginal outcome.
- The vectors are apparent positions as seen from Earth's center, with no
  independently validated observer-dependent light-time/aberration treatment,
  lunar limb profile, observer elevation, refraction, or solar limb model.
- The solar-center daylight cap is geometric. Sunrise/sunset circumstances
  involving only part of the solar disk are not validated here.
- Classification uses TT-driven ephemerides and an axisymmetric Earth. Earth's
  rotation angle/longitude is unnecessary for this global experiment. It does
  **not** validate historical/future longitude predictions or a Delta-T model.
  UTC conversion uses Astropy's available leap-second tables; future-date and
  IERS/polar-motion warnings remain visible, including for 2043. The 2185
  reference is outside ERFA's stated 1900-2100 solar-ephemeris accuracy interval;
  a matching type does not validate numerical circumstances at that epoch.
- Most reference **types** have published sources; the 2044-02-28 and 2043-10-03
  entries remain computed controls. Hybrid-sequence regression expectations are
  recorded research results, not a newly independent oracle. Computed timings, coordinates,
  margins, and durations have not been checked against independent Besselian
  elements/path circumstances. NASA/EclipseWise pages were discoverable through
  web research, but direct fetching was unavailable in this environment.

Before integration, independently validate numerical circumstances, choose and
version the ephemeris/radius/time conventions, define the supported epoch and
uncertainty policy, and make calendar/map/contact consumers share that canonical
analysis. Preserve existing date/contact meanings. No lunar algorithms were
modified by this solar-only hardening; the lunar fixture's known failures remain.
