# Eclipse map API: contract and operational feasibility

Research for #245, saved 2026-10-31. This is a proposed implementation path,
not a production API, finalized policy, or accuracy guarantee.
Calendar classification prerequisite: #275.

## User journey and consistency

The calendar reports the maximum phase visible anywhere: total takes precedence
over annular, then partial. The map retains the full scientific classification.
For a hybrid, the calendar says total and the map shows annular and total
segments, with partial visibility outside the central path.

The same documented API should serve the first-party one-click journey,
replacement frontends, and raw research clients. Frontend identity must not
determine correctness, cacheability, or access to the underlying data.

Production needs one canonical event record shared by calendar, contacts and map.
Stable event IDs and calculation revisions must replace the prototype's date-only
IDs and date-window searches. A map request must not silently resolve to a nearby
event. A revision mismatch should be explicit, not produce contradictory results.

## Proposed contract

Candidate route:
`GET /api/v2/astronomical-events/{event_id}/visibility-map?revision=...`.
API version and final route are still decisions, not implemented endpoints.
A capabilities endpoint should advertise supported dates, profiles and revisions.

`VisibilityMapResponse` in `verify_eclipse_visibility_map.py` provides executable
draft Pydantic models and generated examples. Its main fields are:

| Field | Meaning |
|---|---|
| `schema_version`, `algorithm_revision` | Representation and calculation provenance |
| `map_status` | `ready`, `not_eclipse`, `indeterminate`, or `unsupported` |
| `event` | Canonical summary, maximum phase, full classification, contacts and greatest eclipse |
| `no_eclipse` | Explicit negative result and diagnostic reason |
| `geometry` | GeoJSON FeatureCollection, present only for `ready` |
| `layers` | Layer identities, translation keys, ordering and default visibility |
| `time_model` | TT/UT1 relationship, Delta T value/source/uncertainty and ephemeris |
| `accuracy`, `warnings` | Scientific limitations distinct from transport errors |
| `view_hints` | Suggested center, bounds and view; not a second map library |

Solar layers include the partial envelope, maximum-magnitude bands, central
line, umbral/antumbral path, northern/southern limits and greatest-eclipse point.
Hybrid path features identify their local total or annular phase.
Lunar layers include Moon-up regions, totality visibility, contact horizons,
sublunar track and contact points. Lunar visibility is not a solar-style shadow
track on Earth's surface.

GeoJSON uses longitude/latitude, splits antimeridian crossings and handles poles.
Production must document feature properties and sampling/contour accuracy as
strictly as the envelope; the prototype still uses flexible geometry dictionaries.
Magnitude is not obscuration. The map must explain the selected quantity.

Use one machine-readable error envelope: 404 for an unknown event, 409 for a
revision conflict, 422 for invalid input, 429 for caller quota, and 503 for
temporary capacity/unavailability. Scientific uncertainty is not a server error.

Historical dates require explicit calendar and astronomical year numbering.
TT Julian dates are the unambiguous instant; UT1 must not be presented as precise
UTC. The prototype's UT strings use a `Z` suffix for convenience: production
must resolve that misleading notation before freezing the contract.
Supported history and ephemeris coverage remain explicit capability decisions.

## Calculation evidence

Run from the repository root in an isolated environment with NumPy, Astropy,
Pydantic 2, contourpy and Shapely 2:

```sh
python research/verify_eclipse_visibility_map.py
python research/verify_eclipse_visibility_map.py --grid-deg 0.5 \
    --output-dir /tmp/eclipse-map-samples
```

Default execution also compares with the current calendar classifier, requiring
the application's dependencies. `--no-calendar` skips that comparison.
Sample payloads are generated artifacts and are not committed.

The research run recorded 91 passing checks at 1-degree and 0.5-degree grids.
The default run additionally exposes the known #275 mismatch for 2023-04-20:
calendar annular versus map maximum total. That known gap is reported separately
and does not fail the script. It must not be treated as an acceptable production
inconsistency.

Cases cover modern total, annular, hybrid and partial solar eclipses; Arctic
and Antarctic paths; 1919; the proposed 585 BC eclipse; total, partial and
penumbral lunar eclipses; and solar/lunar negative cases.

For the modern and 1919 solar fixtures, greatest times differed by about
0.6-12.4 seconds, locations by less than 0.2 degrees, and central durations
by less than one second. Width differences were about 0.1-2.1 km.
The 2023 hybrid produces annular-total-annular path segments.
The ancient case only checks classification and intersection with Asia Minor,
not an independently verified precise historical path.

These are exploratory checks, not independent certification. Reference values
were recovered through web search because direct NASA/JPL downloads failed.
They must be checked against original tables before becoming production fixtures.
Some cases only assert classification and geometry validity. Tolerances are
explicit in the script and do not establish precision everywhere.

Useful source tables:

- NASA solar catalog: https://eclipse.gsfc.nasa.gov/SEcat5/SEcatalog.html
- NASA 2023: https://eclipse.gsfc.nasa.gov/OH/OH2023.html
- NASA 2024: https://eclipse.gsfc.nasa.gov/OH/OH2024.html
- NASA 2025: https://eclipse.gsfc.nasa.gov/OH/OH2025.html
- NASA Delta T: https://eclipse.gsfc.nasa.gov/SEcat5/deltatpoly.html
- EclipseWise lunar reference:
  https://www.eclipsewise.com/lunar/LEprime/2001-2100/LE2025Sep07Tprime.html

Remaining accuracy work:

- Choose the production ephemeris and supported date range; built-in ephemeris
  results do not prove all-history precision.
- Use observed Earth rotation where available and an explicit historical Delta T
  model elsewhere. The polynomial gives roughly 74 seconds in 2024 versus
  roughly 69 seconds observed.
- Agree the lunar atmospheric shadow enlargement: computed 2025 lunar
  magnitudes were about 0.005 lower and durations about 60 seconds shorter
  than reference values.
- Prototype confidence/uncertainty fields are illustrative, not calibrated
  statistical guarantees. Longitude uncertainty does not describe every source
  of position error.
- Refine horizon treatment, limb effects, near-grazing classification, narrow
  hybrid transitions and non-central eclipses. Grid sampling is not a proof of
  accurate boundary geometry or exact global maximum magnitude.

## Performance evidence and limits

Single-process service-level samples, excluding HTTP, concurrent traffic,
serialization overhead at the API boundary and deployment effects:

| Work | Observed wall time / compact JSON |
|---|---|
| Solar map, 1-degree grid | About 1.6-2.2 seconds |
| Solar map, 0.5-degree grid | About 3.3-4.2 seconds |
| Lunar map | About 1.1-1.7 seconds |
| Ready solar payloads | About 11-103 KiB |
| Largest sampled lunar payload | About 163 KiB |

These are not p95 measurements, CPU budgets or safe concurrency estimates.
Provisional goals from the earlier investigation were warm p95 <=250 ms,
cold p95 <=5 seconds and payload <=2 MiB. None is a verified production SLO.

## Existing operational wiring and gaps

- `api/routes/events.py`: rate limiting wraps response caching, so cached
  responses still consume the endpoint allowance. Calendar/contact TTL is
  600 seconds.
- `api/rate_limiter.py`: fixed-window per-IP limits with process-local memory;
  defaults include 8/minute calendar searches, 5/minute stream starts and
  30/minute contacts. Fixed windows allow bursts; per-IP limits alone cannot
  protect global capacity or fairly serve shared institutional IPs.
- `api/cache.py`: global cache has 256 entries, a 100 MiB estimated memory
  cap and a 10 MiB entry cap. Keys include locale. Simultaneous misses are
  not coalesced. The decorator discovers Pydantic request models, so a plain
  path/query GET cannot assume caching will work automatically.
- `api/metrics.py` and `api/main.py`: HTTP, cache lifecycle, 429, errors,
  timeout and abandoned-work metrics already exist. Reuse rather than duplicate
  them. Add bounded route handling for the new nested endpoint.
- HTTP timeout/disconnect does not reliably terminate synchronous calculations.
  A response deadline is not admission control.

## Recommended implementation path

### Versioned artifacts and cache hierarchy

Treat a map as a reproducible scientific artifact, keyed by:

`event_id + calculation_revision + time_model_revision + quality_profile + representation_version`

Include every result-affecting option; canonicalize defaults. Revisions must
cover ephemeris/Delta T data updates and contact/classification policy.
Keep translation keys in artifacts rather than translated labels so locale,
theme and frontend do not fragment the calculation cache.

Use a bounded memory cache over a persistent artifact store. Give map artifacts
a separate budget from calendar/batch responses. Historical maps do not become
scientifically stale after ten minutes; revision changes determine invalidation.
Do not silently serve an older revision when an exact revision was requested.

Revision-qualified immutable URLs can use long-lived HTTP caching and ETags;
unversioned aliases need revalidation. Define compression and representation
variants correctly. Definite negative results may be cached by revision, with
bounds against arbitrary-input cache pollution. Do not cache transient failures
as `not_eclipse`.

### Coalescing and admission

One calculation per artifact key; concurrent callers await the same result.
For multi-process deployments, coordinate this across workers, including lock
ownership, expiry, failure cleanup and atomic artifact publication.

Distinct cold keys enter a bounded worker pool and bounded queue. Choose worker
count from deployment CPU/memory measurements alongside calendar workload.
Queue time counts toward the response deadline. Completed shared work may still
populate the artifact cache after one waiter disconnects; detach that waiter,
not other users. Define hard execution limits independently of HTTP timeouts.

### Quotas and public research access

Separate request/bandwidth protection from new-computation admission:

| Control | Scope |
|---|---|
| Delivery allowance | All requests, including cache hits and conditional requests |
| Cold-computation allowance | Distinct newly admitted artifacts, not cache hits or shared waits |
| Execution/queue cap | Global capacity, independent of caller count |

Use anonymous per-IP quotas initially; research API keys can later offer
explicit quotas without penalizing shared institutional IPs. Trust proxy
headers only through the existing trusted-proxy policy. Never privilege
first-party traffic based on a client-supplied frontend identifier.

Reject caller quota exhaustion with 429 and capacity exhaustion with 503,
both with documented Retry-After behaviour. Ensure quota accounting and
single-flight admission cannot race or silently bypass cold-work limits.
Final numbers remain configurable and must follow load measurements, not
single-request benchmarks.

Start with synchronous interactive delivery if measured capacity supports it.
If sustained bulk research is needed, add a separate bounded job/batch interface
with 202, job identity and polling rules rather than unbounded interactive work.
Do not add batch jobs or API-key infrastructure merely to save this research.

### Metrics

Reuse existing HTTP/cache metrics and extend with bounded labels:

- Artifact outcomes: memory hit, persistent hit, shared wait, cold calculation.
- Calculation duration by stage, queue wait, running workers and queue depth.
- Caller-quota versus capacity rejections; calculation failures and payload size.
- Scientific statuses and calendar/map revision or classification mismatches.

Keep HTTP requests distinct from actual calculations: ten shared callers are
ten requests but one computation. Never use event IDs, dates, IPs, API keys or
arbitrary query values as Prometheus labels; use structured diagnostic logs.

### Required performance scenarios

Before setting default quotas or claiming an SLO:

1. Many requests for one cold key execute exactly one calculation.
2. Many distinct keys cannot exceed worker, queue or memory bounds.
3. Warm-map latency remains acceptable during research and calendar traffic.
4. Persistent artifacts survive restart and are shared across API workers.
5. Exceptions, worker crashes, deadlines and disconnects release waiters and
   admission slots correctly without corrupt artifacts.
6. Cache churn, negative queries, conditional requests and multi-client bursts
   are measured with rate limiting enabled.
7. Metrics account for hits, waits, actual work and rejections exactly once.
8. Calendar/map revision and classification consistency remains intact.

The evidence supports proceeding to implementation design. This branch adds
research only: no routes, production dependencies, cache changes, quota policy
or production observability changes are enabled.
