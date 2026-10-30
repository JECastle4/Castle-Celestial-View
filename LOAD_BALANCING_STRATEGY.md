# Load Balancing Strategy (Phase 4)

## Overview

Phase 3 established single-instance DDoS protection:
- Rate limiting (5-8 req/min for expensive endpoints, set below capacity)
- Request size limiting (5 MB)
- Adaptive timeout (p95-based load shedding)
- Per-endpoint cost tracking via Prometheus metrics
- Cardinality-bounded metrics to prevent monitoring exhaustion

Phase 4 scales to multi-instance deployments with proper load management and work cancellation.

## Known Limitations from Phase 3

**CPU Capacity Constraint:**
- With 4 CPU cores and 60 seconds per minute: 240 CPU-seconds available per minute
- Batch requests cost ~40s CPU each → max 6 req/min at full capacity
- Events requests cost ~30s CPU each → max 8 req/min at full capacity
- Phase 3 limits set conservatively (5-8 req/min) to stay below capacity

**Timeout doesn't interrupt work:**
- The deadline returns 503 before response headers, while the retained application task finishes
- `asyncio.wait_for()` alone cannot enforce that deadline for shielded synchronous routes
- CPU-bound Astropy calculations (40s each) complete in background
- Under high-volume attack, rejected requests still consume full resources
- This is acceptable for single-instance, but worsens exhaustion at scale

**Fixed-window rate limiting doesn't space requests:**
- "5 per minute" allows all 5 requests to arrive in the first second
- No concurrency control: requests queue in worker threads
- If 5 batch requests (40s CPU each) arrive together: 200s CPU work queued instantly
- 4 CPU cores need 50s to complete (all cores saturated)
- Requests that arrive when the queue is full can time out while work continues
- Without admission control, the queue can grow instead of draining

**Why Phase 3 is still an improvement but incomplete:**
- Rate limiting and adaptive response deadlines help but don't guarantee capacity protection
- Production monitoring is needed to verify load stays below capacity
- Admission control remains necessary for stronger single- and multi-instance protection

## Runtime Monitoring and Cancellation

### Rate limiting is not admission control

Default per-IP limits are 5/minute for batch observations, 8/minute for event
searches, 5/minute for event streams, 30/minute for contact times, and 100/minute
for cheap endpoints. Environment overrides remain supported in `api/rate_limiter.py`.
The export queue paces requests 2.5 seconds apart (at most about 24/minute before
request time), and retries a 429 once after its advertised delay.

A fixed window permits a burst at the beginning of the window. It does not cap
concurrent computations, provide admission control, or prevent duplicate
calculations when several callers miss the cache. In particular, returning a
timeout **does not free a worker thread** or reset the request's rate-limit cost.

### Cancellation contract

The export queue stops queued items and pacing/retry waits immediately when
cancelled, returns completed results, and continues observing the in-flight
promise so late rejection is handled. Details expansion and export share a
contact-time request. Each subscriber can cancel independently; only cancellation
of every subscriber aborts the HTTP request. A caller without a signal keeps its
subscription until settlement. Leaving the view cancels both subscriptions;
starting another search or changing locale does not.

The backend enforces an absolute adaptive deadline even while a synchronous
calculation or stream iterator is running in a thread. Before response headers
it returns 503; after headers it closes the body (SSE receives a timeout error
event). It cannot change a status already sent. Late application sends are
suppressed and task exceptions are observed and logged.

Already-running CPU-bound work continues after timeout or disconnect. A successful
response-cache calculation still populates its cache (contact times use a
600-second TTL). **This is intentional**: a retry before completion misses the
cache and may recompute; a retry after completion can hit it. There is no backend
in-flight deduplication, timeout `Retry-After`, or automatic frontend 503 retry.
Existing per-IP limits still apply. Genuine interruption remains Phase 4.2.

Tasks surviving the HTTP response are retained until settlement. On application
shutdown they get up to five seconds to finish before cancellation is requested.
Cancellation still cannot interrupt running worker threads; the process supervisor
controls the ultimate shutdown bound. Process termination can lose both the
result and its final metrics. Streaming generators normally stop between chunks
on disconnect, but their current worker-thread step may still finish.

### Emitted metrics

Scrape `/api/metrics`. All caches and these metrics are process-local; this does
not add gunicorn multiprocess Prometheus aggregation.

| Metric | Runtime meaning |
|--------|-----------------|
| `http_requests_total`, `http_request_duration_seconds` | HTTP outcomes, including unhandled pre-response 500s; streams retain the status actually sent. |
| `http_requests_in_progress` | HTTP requests still owned by middleware, not all backend CPU work. |
| `cache_hits_total`, `cache_misses_total` | Response-cache lookup outcomes. |
| `cache_memory_bytes`, `cache_entry_count` | Estimated retained response bytes and entries, updated on cache mutations. Not RSS or immediately purged live-only data. |
| `cache_evictions_total` | LRU removals for memory/capacity limits, attributed to the removed entry's endpoint. |
| `cache_expirations_total` | Expired entries discovered and removed on access, purge or statistics collection. Not requests expiring before processing. |
| `errors_total` | One bounded failure classification per request; 404/405 and other unmapped 4xx remain visible in HTTP metrics only. |
| `timeout_exceeded_total`, `rate_limit_exceeded_total` | Deadline enforcement and 429 responses respectively. |
| `abandoned_work_total{endpoint,reason}` | Work completing after a deadline (`timeout`) or an observed vanished connection (`client_disconnect`). |
| `abandoned_work_duration_seconds` | Total wall-clock runtime of completed abandoned work, not CPU time or time since disconnect. |
| `abandoned_work_in_progress` | Non-streaming tasks still running after their response deadline, not all disconnected or queued work. |

Error categories are `invalid_input` (400), `payload_too_large` (413),
`request_validation` (422), `rate_limited` (429), `timeout` (explicit deadline),
`server_error` (other 5xx), `unhandled_exception` (escaping before/non-streaming
failure), and `stream_error` (escaping during a stream). Labels never include
exception messages or raw unmatched paths. Cache labels use the bounded decorated
function names; HTTP labels use matched route templates (including router
prefixes such as `/api/v1`) or `unknown`. This keeps completed-request samples
aligned with the pre-route labels used by adaptive timeout tracking.

Expiration is lazy: an idle cache can retain expired entries until a later
operation removes them. Replacement and explicit clear are neither expiry nor
eviction. Use expiration and miss rates to tune cache policy, not as evidence of
requests lost in a queue.

Disconnect detection is a non-blocking check before non-streaming response
headers. It observes that the connection is gone **by completion**, not when or
why it vanished. A reverse proxy may hide browser cancellation or cause the
upstream disconnect itself. Own timeout responses are excluded to avoid counting
the same operation twice. Streams and work that never settles are not included
in disconnect-completion metrics.

### Deployment alignment

Both supplied nginx API configurations set send/read inactivity timeouts to
250 seconds, above the backend's 240-second maximum expensive-request budget.
The contact-time browser timeout remains 240 seconds, so network overhead can
still produce a client/server race at that boundary. Existing deployments need
the manual nginx configuration update described in `DEPLOYMENT_GUIDE.md`.

### Reproducing runtime checks

Install `requirements-dev.txt`, then run:

```bash
python -m pytest tests/test_runtime_evidence.py tests/test_request_lifecycle.py \
  tests/test_cache_lifecycle_metrics.py --no-cov
```

The live harness starts a fresh interpreter, preserving real rate limiting and
metric emission instead of pytest's test-mode substitutes. It uses production
routes/middleware with deterministic astronomy service fixtures; it verifies HTTP
lifecycle behavior, not astronomical accuracy. Its control routes exist only in
`tests/runtime_app.py` and must never be deployed.

Optional Linux deployment and soak checks:

```bash
docker pull nginx:stable-alpine
RUN_NGINX_TESTS=true RUN_LONG_NGINX_TESTS=true \
  python -m pytest tests/test_runtime_proxy.py --no-cov
RUN_RUNTIME_SOAK=true python -m pytest tests/test_runtime_soak.py --no-cov -s
```

The proxy checks require a running local Docker daemon and execute the supplied
API location directives without production TLS/static-site paths. The long
check sends a real 130-second request. The mixed-workload soak runs for ten
minutes, checks exact metric deltas, and measures process RSS/thread stability.
Gunicorn tests run on Unix only; Docker/long/soak checks are opt-in.
Streaming disconnect checks synchronize on worker entry/completion and HTTP
metrics, not garbage-collection-dependent generator finalization.

For browser cancellation and export/timeout recovery, with the backend Python
environment on `PATH`:

```bash
cd frontend
CI=true RATE_LIMIT_ENABLED=false \
  npx playwright test tests/e2e/events-locale-timezone.spec.ts \
  tests/e2e/events-eclipses-aug-sep-2026.spec.ts
```

Install the project's Playwright browsers first. These checks cover all four
configured browsers, including a real browser abort observed by API metrics.
They also verify a real SSE deadline and subsequent recovery, shared contact
requests populating both details and CSV downloads, deferred locale refresh
after JSON export, and 429 recovery/503 partial exports. Intercepted export
fixtures use actual browser downloads; the astronomical suite compares rendered
solar/lunar contact times with real API responses. The live-server helper
uses bounded startup/shutdown and attaches backend logs to Playwright results.

## Phase 4.1: Admission Control

**Goal:** Reject requests before accepting them, not after timeouts complete.

**Implementation:**
1. Track in-flight work count per endpoint (incremented on accept, decremented on completion)
2. Calculate per-endpoint throughput capacity (requests per minute) based on observed p95 duration:
   - `throughput_capacity = (CPUs × 60 seconds) / p95_duration_seconds`
   - Example (Batch): (4 CPUs × 60s) / 40s = 6 requests/min
   - Example (Events): (4 CPUs × 60s) / 30s = 8 requests/min
   - Example (Position): (4 CPUs × 60s) / 2s = 120 requests/min
3. Convert to concurrent capacity for admission check: concurrent = throughput_capacity / (60s / avg_request_duration)
   - Batch: 6 req/min ÷ (60s / 40s) = 6 ÷ 1.5 = 4 in-flight
   - Events: 8 req/min ÷ (60s / 30s) = 8 ÷ 2 = 4 in-flight
4. Reject with 503 + Retry-After header if in-flight >= concurrent capacity threshold
5. Ensures CPU budget is only consumed by accepted requests (not rejected ones)

**Benefits:**
- Clients get immediate 503 when capacity full (not timeout after 40s+ of background work)
- No CPU work wasted on rejected requests
- Per-endpoint capacity adapts automatically as p95 duration changes
- Natural back-pressure: busy endpoint rejects, client retries elsewhere
- Natural back-pressure: fast endpoints admit more, slow endpoints admit fewer
- Complements rate limiting: spaces requests across time + limits concurrent work
- Can be implemented entirely at application level (no load balancer changes)

**Algorithm Example (batch endpoint):**
```
p95_duration = 40 seconds
cpus = 4
throughput_capacity = 4 × 60 / 40 = 6 requests/min
concurrent_capacity = 6 / (60 / 40) = 4 in-flight requests

if in_flight_count >= 4:
    reject 503 with Retry-After: (40 / 4) = 10 seconds
else:
    accept request, increment in_flight_count
    on completion: decrement in_flight_count
```

**Dependencies:**
- Metrics tracking of in-flight work (HTTP `record_request_start/end` alone is
  insufficient: it excludes detached tasks and is not an admission counter)
- Thread-safe counter per endpoint (`threading.Lock` or `asyncio.Lock`)
- P95 duration from Prometheus metrics (already calculated)

**Files to modify:**
- `api/metrics.py`: Add `get_in_flight_count(endpoint)` method, expose p95 duration
- `api/timeout_logic.py`: Add `calculate_admission_capacity(endpoint)` based on p95 duration
- `api/main.py`: New `admission_control_middleware()` before `timeout_middleware()`
- Tests: `tests/test_admission_control.py` (capacity calculation, rejection behavior)

**Timeline:** 2-3 days

## Phase 4.2: Cancellable Work

**Goal:** Terminate CPU-bound work mid-execution when timeout fires.

**Implementation:**
1. Move expensive Astropy calculations to `concurrent.futures.ProcessPoolExecutor`
2. Wrap executor calls with timeout using `asyncio.wait_for(loop.run_in_executor(...))`
3. When timeout fires, cancel the executor task via `Future.cancel()`
4. **Note:** `Future.cancel()` does NOT send SIGTERM or interrupt already-running work. Requires explicit:
   - Worker process recycling after N requests (to clear memory/handles)
   - Or, cooperative cancellation via shared flag that worker checks between sub-tasks
   - Or, separate SIGTERM handler tied to request timeout (requires worker cooperation)
   - CPU-bound Astropy work will complete its current calculation regardless of cancellation

**Benefits of ProcessPoolExecutor foundation:**
- Moves expensive calculations out of event loop (better concurrency model)
- Enables future explicit process termination or cooperative cancellation
- Foundation for future graceful shutdown with work cancellation
- Prepares codebase for resource cleanup strategies
- **Note:** Without explicit termination or cooperative cancellation, CPU-bound work still completes even if timeout fires (resources are NOT freed immediately in this phase)

**Complexity vs. Value:**
- Medium complexity: refactor calculation paths, process lifecycle management
- Low value for single-instance (admission control is sufficient)
- High value for multi-instance under extreme load
- Overhead: process startup/teardown, IPC cost

**Decision:** Defer to Phase 4.2 (only if admission control insufficient under production load)

**Calculation endpoints affected:**
- `api/routes/bodies.py`: All position endpoints (sun, moon, Venus, planets)
- `api/routes/events.py`: Eclipse detection and contact-time endpoints
- `api/routes/batch.py`: Batch observations endpoint

**Timeline:** 1 week

## Phase 4.3: Multi-Instance Deployment

**Goal:** Distribute load across multiple instances with coordinated admission control.

**Requirements:**
- Load balancer (nginx/HAProxy) distributes requests across instances
- Shared metrics backend (Prometheus) for cross-instance capacity tracking
- Graceful shutdown orchestration (admission control rejects new work, waits for in-flight)
- Health check endpoint (includes in-flight work depth)

**Load Balancer Configuration:**
- Sticky sessions optional (no state affinity needed)
- Health check endpoint: `/health` returns 503 if in-flight work exceeds threshold
- Retry-After header parsing for backoff (when instance rejects 503)
- Per-instance weight adjustment based on in-flight depth

**Capacity Calculation:**
- Single instance: 240s CPU budget/min (4 CPUs × 60s = 240s available)
  - Batch endpoint: 240s ÷ 40s/req = 6 requests/min max throughput
  - Events endpoint: 240s ÷ 30s/req = 8 requests/min max throughput
- N instances: 240N s CPU budget/min
- Rate limiter already configured per IP: 5 batch/min, 8 events/min (conservative defaults; admission control required for multi-instance)
- Admission control per endpoint prevents overload: batch capacity ~4 in-flight, events capacity ~4 in-flight
- Load balancer distributes evenly, admission control at each instance prevents overload

**Infrastructure:**
- Kubernetes StatefulSet or Docker Compose orchestration
- Prometheus scrape config for multi-instance metrics
- Nginx upstream health checks
- CI/CD pipeline for rolling updates

**Timeline:** Infrastructure work (not in this story)

## Success Criteria

**Single-instance (Phase 3 - Current):**
- ✓ DDoS requests timeout after adaptive budget
- ✓ Rate limiting prevents request flood (5 batch/min, 8 events/min)
- ✓ Adaptive timeout reduces budget under load
- ✓ Metrics prevent cardinality explosion

**Multi-instance Phase 4.1:**
- [ ] Admission control rejects work before accepting
- [ ] Clients receive immediate 503 when capacity full
- [ ] No background CPU waste for rejected requests
- [ ] In-flight work tracked accurately per endpoint
- [ ] Retry-After header guides backoff

**Multi-instance Phase 4.2:**
- [ ] Timeouts interrupt CPU-bound work
- [ ] Resources freed immediately when timeout fires
- [ ] SIGTERM handled gracefully in worker processes
- [ ] No background work continues after rejection

**Capacity under load:**
- 1 instance: ~6 batch/min (240s CPU budget / 40s per request) for 4-core system
  - Calculation: (4 cores × 60s) / 40s per request = 6 requests/minute max throughput
  - Rate limiting at 5/min provides 83% headroom; 8 events/min uses 100% peak capacity
- 2 instances: ~12 batch/min with admission control (both at 6/min each)
- N instances: ~6N batch/min with load balancer + admission control per 4-core instance
- Adjust scaling factors for different CPU counts: (CPU_count × 60s) / p95_duration

## Timeline

| Phase | Work | Duration | Status |
|-------|------|----------|--------|
| 3.1 | Rate limiting | Done | ✓ |
| 3.2 | Metrics + in-progress tracking | Done | ✓ |
| 3.3 | Adaptive timeout + streaming | Done | ✓ |
| 4.1 | Admission control | 2-3 days | Deferred |
| 4.2 | Cancellable work (ProcessPoolExecutor) | 1 week | Deferred |
| 4.3 | Multi-instance deployment | Infrastructure | Deferred |

## Dependencies

- Phase 3 complete (rate limiting + metrics + adaptive timeout) ✓
- Prometheus metrics backend running (for in-flight tracking)
- P95 duration calculation available (already in `api/timeout_logic.py`)
- Load balancer configured (for Phase 4.3)

## Related Documentation

- `api/main.py`: `TimeoutMiddleware` docstring - documents Phase 3 limitations
- `api/timeout_logic.py`: Adaptive timeout calculation (p95-based load shedding)
- `api/metrics.py`: In-flight request tracking via `record_request_start/end`
- `api/rate_limiter.py`: Per-endpoint rate limits (LIMIT_EXPENSIVE_BATCH, LIMIT_EXPENSIVE_EVENTS)
- `PENTEST-REVISED-STABILITY-FOCUS.md`: DDoS policy and CPU budgets per endpoint
- `PHASE5-VERIFICATION-AND-PENTEST-READINESS.md`: Security validation criteria

## Rationale

**Why defer to Phase 4?**
1. Single-instance protection is proven by rate limiting + adaptive timeout
2. Admission control and cancellable work are better tackled together
3. Multi-instance deployment is an infrastructure story, not a code story
4. Admitting work then timing it out is acceptable until you scale

**Why implement this later?**
1. When you need multiple instances, admission control becomes critical
2. Load balancer placement makes admission control easier (at reverse proxy)
3. Graceful shutdown with cancellable work is safer for rolling deploys
4. ProcessPoolExecutor overhead not justified until you have concurrency bottleneck
