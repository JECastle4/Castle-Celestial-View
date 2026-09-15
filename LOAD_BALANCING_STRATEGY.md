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
- `asyncio.wait_for()` returns 503 to client but worker thread continues running
- CPU-bound Astropy calculations (40s each) complete in background
- Under high-volume attack, rejected requests still consume full resources
- This is acceptable for single-instance, but worsens exhaustion at scale

**Fixed-window rate limiting doesn't space requests:**
- "5 per minute" allows all 5 requests to arrive in the first second
- No concurrency control → requests queue in background threads
- If 5 batch requests (40s CPU each) arrive together: 200s CPU work queued instantly
- 4 CPU cores need 50s to complete (all cores saturated)
- Requests that arrive when queue is full will timeout while work continues
- Without admission control, queue grows instead of draining

**Why Phase 3 is still an improvement but incomplete:**
- Rate limiting + adaptive timeout + conservative limits help but don't guarantee protection
- Requires production monitoring to verify load stays below capacity
- Works well for single-instance; insufficient for multi-instance where admission control is critical

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
