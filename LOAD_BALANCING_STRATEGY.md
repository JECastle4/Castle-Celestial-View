# Load Balancing Strategy (Phase 4)

## Overview

Phase 3 established single-instance DDoS protection:
- Rate limiting (10 req/min for expensive endpoints)
- Request size limiting (5 MB)
- Adaptive timeout (p95-based load shedding)
- Per-endpoint cost tracking via Prometheus metrics
- Cardinality-bounded metrics to prevent monitoring exhaustion

Phase 4 scales to multi-instance deployments with proper load management and work cancellation.

## Known Limitations from Phase 3

**Timeout doesn't interrupt work:**
- `asyncio.wait_for()` returns 503 to client but worker thread continues running
- CPU-bound Astropy calculations (40s each) complete in background
- Under high-volume attack, rejected requests still consume full resources
- This is acceptable for single-instance, but worsens exhaustion at scale

**Why this matters:**
- 10 req/min rate limit spaces requests across time ✓
- But if requests queue up waiting for CPU, 10 slow requests = 400s total work
- With 4 CPU cores, 400s work / 4 CPUs = 100s real time (all cores saturated)
- New requests that time out still consume that 100s capacity
- Without admission control, the queue grows even though all requests time out

**Current DDoS policy (from PENTEST-REVISED-STABILITY-FOCUS.md):**
- Batch operations: ~40s CPU per request, limit to 10/min = 400s CPU/min = 6.67s CPU/sec
- Event detection: ~30s CPU per request, limit to 15/min = 450s CPU/min = 7.5s CPU/sec
- With 4 CPU cores (240s CPU/sec available), these limits are well-spaced
- Single-instance protection is adequate until you need multi-instance

## Phase 4.1: Admission Control

**Goal:** Reject requests before accepting them, not after timeouts complete.

**Implementation:**
1. Track in-flight work count per endpoint (incremented on accept, decremented on completion)
2. Calculate per-endpoint capacity based on expected duration:
   - `capacity = CPUs × 1 second / p95_duration`
   - Example: 4 CPUs, 40s p95 batch = 4 × 1 / 40 = 0.1 concurrent (max ~1 every 10s)
   - Example: 4 CPUs, 2s p95 position = 4 × 1 / 2 = 2 concurrent
3. Reject with 503 + Retry-After if in-flight >= capacity threshold
4. Ensures work budget is only consumed by accepted requests

**Benefits:**
- Clients get immediate 503 when capacity full (not timeout after seconds)
- No background work consuming CPU for rejected requests
- Natural back-pressure: fast endpoints admit more, slow endpoints admit fewer
- Complements rate limiting: spaces requests across time + limits concurrent work
- Can be implemented entirely at application level (no load balancer changes)

**Algorithm Example (batch endpoint):**
```
p95_duration = 40 seconds
cpus = 4
capacity = 4 × 1 second / 40 = 0.1 concurrent

if in_flight_count >= 1:  # 0.1 rounds up to 1
    reject 503 with Retry-After: 10
else:
    accept request, increment in_flight_count
    on completion: decrement in_flight_count
```

**Dependencies:**
- Metrics tracking of in-flight work (already have `record_request_start/end`)
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
3. When timeout fires, cancel the executor task (sends SIGTERM to child process)
4. Worker process handles SIGTERM gracefully (cleanup and exit)

**Benefits:**
- Truly interrupts CPU-bound work (not just event loop cancellation)
- Resources freed immediately when timeout fires
- Compatible with multi-instance graceful shutdown (same signal handling)
- Enables request cancellation for long-running streams

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
- Single instance: ~400s CPU budget/min (4 CPUs × 60s / ~40s avg batch)
- N instances: ~400N s CPU budget/min
- Rate limiter already configured per IP: 10 batch/min, 15 events/min
- Load balancer distributes evenly, admission control prevents overload

**Infrastructure:**
- Kubernetes StatefulSet or Docker Compose orchestration
- Prometheus scrape config for multi-instance metrics
- Nginx upstream health checks
- CI/CD pipeline for rolling updates

**Timeline:** Infrastructure work (not in this story)

## Success Criteria

**Single-instance (Phase 3 - Current):**
- ✓ DDoS requests timeout after adaptive budget
- ✓ Rate limiting prevents request flood (10 batch/min)
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
- 1 instance: ~10 batch/min (400s CPU budget / 40s per request)
- 2 instances: ~20 batch/min with admission control (both instances at capacity)
- N instances: ~10N batch/min with load balancer + admission control

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

- `api/main.py`: `timeout_middleware()` docstring (lines ~661) - documents Phase 3 limitation
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
