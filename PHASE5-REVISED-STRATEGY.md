# Issue #206 Phase 5 - Revised Pen Test & Future Work Strategy

## Previous Approach vs. Reality Check

### What We Initially Planned
Generic OWASP Top 10 penetration testing:
- SQL injection, command injection, XXS testing
- Authentication/authorization bypass
- Session management attacks
- Elaborate fuzzing

### Why That Was Wrong For This API
✅ **Already Verified Safe**:
- No database (no SQL injection vector)
- No user strings parsed as commands (no command injection)
- Type-validated inputs (Pydantic) before astropy (no injection into calculations)
- No user authentication (no session to bypass)
- Stateless (one request doesn't affect another)

**Conclusion**: Classic vulnerability testing is not the priority.

---

## New Approach: Stability & Resource Safety Focus

### What Actually Matters
1. **Does it crash ungracefully?** → Test boundary violations
2. **Does it hang forever?** → Test timeouts & hanging processes
3. **Does it leak resources?** → Test memory/connections over time
4. **Does it recover from errors?** → Test error handling
5. **Does it handle concurrency?** → Test simultaneous requests

### Why This Matters
- **Current State**: Single-instance production server
- **Real Risk**: A request that hangs or leaks resources can bring down the entire API
- **Security Impact**: Availability is part of security (DoS prevention)
- **Operability**: Need to know how the system fails before it scales

---

## Two Tickets Created

### Ticket 1: Issue #207 - Scaling & Performance (DEFERRED)
**Status**: Future work  
**Created**: [ISSUE-207-TEMPLATE.md](./ISSUE-207-TEMPLATE.md)  
**Scope**:
- Rate limiting (per-IP throttling)
- Load balancing (multi-server architecture)
- Server farm strategy (horizontal scaling)
- Monitoring and metrics

**Why Deferred**:
- Application is single-instance now
- Architectural decisions (don't make yet)
- Better addressed AFTER stability is proven

### Ticket 2: Issue #208 - Stability & Crash Prevention (IMMEDIATE)
**Status**: Ready for pen testing  
**Created**: [PENTEST-REVISED-STABILITY-FOCUS.md](./PENTEST-REVISED-STABILITY-FOCUS.md)  
**Scope**:
- Boundary constraint violations (what breaks at limits?)
- Hanging process detection (does it timeout or hang forever?)
- Resource cleanup (memory leaks? connection leaks?)
- Error handling (graceful degradation or crash?)
- Concurrency safety (can multiple requests coexist?)

**Why Immediate**:
- Single-instance server means one bad request kills the whole API
- Need to know failure modes BEFORE load increases
- Foundational for any future scaling work

---

## Pen Test Work Plan

### Phase 1: Manual Boundary Testing (2-4 hours)
Test edge cases manually with HTTPie:
- Coordinate boundaries (90.0000001, etc.)
- Date boundaries (1582, 2100, etc.)
- Frame count boundaries (1, 2, 10000, 10001)
- Time range logic (inverted times, same times, etc.)

**Deliverable**: List of bugs found (if any)

### Phase 2: Hanging Process Testing (2 hours)
Test for indefinite hangs:
- High frame count (10000) + short time span
- Concurrent batch requests while one is running
- Kill mid-stream and verify cleanup

**Deliverable**: Timeout requirements & recovery procedures

### Phase 3: Resource Monitoring (2-4 hours)
Test resource safety:
- Memory growth over 100 sequential batch requests
- Failed request cleanup (no orphaned generators)
- Concurrency limits (how many simultaneous batches can run?)

**Deliverable**: Resource leak documentation or fixes needed

### Phase 4: Error Handling (1-2 hours)
Test crash resistance:
- Malformed JSON, invalid dates, extreme values
- Verify all errors return HTTP 4xx/5xx (no crashes)
- Verify no stack traces in responses

**Deliverable**: Error handling baseline documentation

---

## Testing Tools Available

### Simple (No Setup)
- **HTTPie**: Manual boundary testing
- **curl**: Timeout testing, SSE stream inspection
- **System monitoring**: `ps aux`, `watch`, memory tracking

### Moderate (Basic Python)
- **Python stress test script**: Concurrent load, resource monitoring
- **psutil**: Memory/CPU tracking programmatically

### Advanced (If Needed)
- **WFuzz**: Fuzzing parameter combinations
- **Locust**: Sustained load testing
- **Strace/ltrace**: System call tracing (debug hangs)

---

## Expected Outcomes

### Best Case
✅ No crashes or hangs found  
✅ Memory stable over 100+ requests  
✅ Graceful error handling verified  
✅ Ready for Issue #207 planning (scaling strategy)

### Likely Case
⚠️ Edge cases found (e.g., frame_count=10000 is slow but not broken)  
⚠️ Timeouts needed (30-60 sec per request)  
⚠️ Memory acceptable but monitor  
→ Create Issue #208 with specific fixes

### Worst Case
🔴 Crashes found on boundary violations  
🔴 Hangs detected (no timeout, server blocks)  
🔴 Memory leaks confirmed  
→ Create Issue #208 with blockers (fix before pen test passes)

---

## Resource Allocation

| Phase | Effort | Tools | Owner |
|---|---|---|---|
| Phase 1: Boundaries | 2-4 hrs | HTTPie, curl | You (manual) |
| Phase 2: Hangs | 2 hrs | curl, system monitor | You (manual) |
| Phase 3: Resources | 2-4 hrs | Python script, psutil | You + script |
| Phase 4: Error Handling | 1-2 hrs | HTTPie, manual | You (manual) |
| **Total** | **~10-14 hours** | **Simple tools** | **Distributed** |

---

## Git Workflow

1. **Now**: Review both documents
   - [ISSUE-207-TEMPLATE.md](./ISSUE-207-TEMPLATE.md)
   - [PENTEST-REVISED-STABILITY-FOCUS.md](./PENTEST-REVISED-STABILITY-FOCUS.md)

2. **Create Issue #207** in GitHub (copy template, set to future milestone)

3. **Create Issue #208** in GitHub (reference pen test scope)

4. **Execute Pen Test** (use revised scope)

5. **Document Findings** (create GitHub issues for any crashes/hangs found)

6. **Fix & Close** Issue #208 (or mark resolved if no critical issues)

7. **Then Schedule** Issue #207 (scaling/performance) for next release

---

## Key Difference from Phase 5 Original Plan

| Original (Generic OWASP) | Revised (Stability-Focused) |
|---|---|
| Burp, Postman fuzzing | HTTPie boundary testing |
| Injection attack scenarios | Crash/hang scenarios |
| Authentication bypass tests | Concurrency safety tests |
| Session hijacking | Resource leak detection |
| Result: False sense of security | Result: Real operational confidence |

---

**Next Step**: Review the two documents and decide on pen test execution approach.
