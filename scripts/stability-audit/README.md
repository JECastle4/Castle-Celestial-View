# Stability Audit Toolkit

Internal audit tools for production stability verification. Run periodically to verify API resilience against crashes, hangs, resource leaks, and boundary violations.

**Status**: Ad-hoc audit (manual, as-needed)  
**Target**: Production (but works locally)  
**Extensibility**: Add new tests as issues are discovered  

---

## Quick Start

### Local Testing (Development Environment)
```bash
cd scripts/stability-audit

# Run all audits
./run-all-audits.sh

# Run specific audit
python test-boundaries.py
python test-resource-safety.py
python test-concurrency.py
python test-error-handling.py
python test-astropy-limits.py
```

### Production Testing
```bash
./run-all-audits.sh --target https://castlecelestialview.net

# Or individual test
python test-boundaries.py --target https://castlecelestialview.net
```

### Generate Report
```bash
./run-all-audits.sh --target https://castlecelestialview.net --report audit-$(date +%Y%m%d).html
```

---

## Test Modules

### 1. `test-boundaries.py`
**Purpose**: Verify API handles coordinate, date, and frame count boundaries gracefully.

**Tests**:
- Coordinate poles (±90° latitude)
- International Date Line (±180° longitude)
- Extreme elevations (+10km, -1km)
- Ancient dates (1900s)
- Far future dates (2100+)
- Frame count progression (2, 10, 50, 100)

**Success**: All boundary inputs return HTTP 200 with expected frames (or HTTP 422 if invalid)

**Failure Indicators**: 
- 500 errors (internal crash)
- Timeout/502 (hangs)
- Mismatched frame counts

**Runtime**: ~5 minutes

---

### 2. `test-astropy-limits.py`
**Purpose**: Identify astropy calculation limits, IERS data coverage, and date range boundaries.

**Tests**:
- IERS data availability (date ranges where calculations work)
- Coordinate edge cases (poles, date line)
- Time span edge cases (extreme density vs. sparse)
- Precision loss detection (far future dates)

**Success**: Establishes safe operating boundaries for astropy

**Failure Indicators**:
- NaN/inf in results
- Graceful degradation below expected accuracy
- Unexpected precision loss

**Runtime**: ~3 minutes

---

### 3. `test-resource-safety.py`
**Purpose**: Detect memory leaks, connection leaks, and resource cleanup issues.

**Tests**:
- Memory growth over 100 sequential batch requests
- Connection pool exhaustion (if applicable)
- Generator cleanup (kill mid-stream, verify server recovers)
- File handle tracking (open/close balance)

**Success**: 
- Memory growth <10% over 100 requests
- All resources freed after request completes
- Server responsive after failed requests

**Failure Indicators**:
- Memory grows unbounded
- Connection count climbs indefinitely
- Orphaned processes/generators
- Server unresponsive after errors

**Runtime**: ~8 minutes

---

### 4. `test-concurrency.py`
**Purpose**: Verify API handles simultaneous requests safely.

**Tests**:
- 10 concurrent batch requests (frame_count=20)
- Mixed batch request sizes under load (70% small: 5 frames, 20% large: 50 frames, 10% invalid)
- Race condition detection (idempotency checks)
- Concurrent request performance

**Success**:
- All requests complete successfully
- No response corruption or interleaving
- Error rate <1%
- No cascading failures

**Failure Indicators**:
- Some requests fail randomly
- Corrupted responses (mixed data)
- Cascading failures (one bad request breaks others)
- Memory spikes

**Runtime**: ~10 minutes

---

### 5. `test-error-handling.py`
**Purpose**: Ensure API crashes gracefully without disclosing sensitive information.

**Tests**:
- Malformed JSON/requests
- Invalid date/time formats
- Out-of-range values (beyond Pydantic validation)
- Incomplete requests (missing required fields)
- Extreme payloads (1MB strings)

**Success**:
- All errors return HTTP 4xx/5xx
- Error messages don't leak stack traces
- No server crashes
- Error format consistent (JSON)

**Failure Indicators**:
- 500 errors (should be 4xx)
- HTML error pages (should be JSON)
- Stack traces in responses
- Server becomes unresponsive

**Runtime**: ~3 minutes

---

## Test Infrastructure

### Common Options (All Scripts)
```
--target URL          API target (default: http://localhost:8000)
--timeout SECONDS     Request timeout (default: 120)
--verbose             Verbose output (show every test)
--json                Output JSON only (no console output)
```

### Output Format

**Console Output** (default):
```
[boundaries] North Pole (latitude=90.0)... ✓ PASS
[boundaries] Frame Count = 10000... ✗ FAIL: Timeout after 120s
[resource-safety] Memory leak detection... ✓ PASS

===== TEST SUMMARY =====
Total:    45
Passed:   43 ✓
Failed:    2 ✗
Errors:    0 ⚠

Results saved to: audit-results-20260801.json
```

**JSON Output**:
```json
{
  "timestamp": "2026-08-01T14:30:00",
  "target": "https://castlecelestialview.net",
  "summary": {
    "total": 45,
    "passed": 43,
    "failed": 2,
    "errors": 0
  },
  "critical_issues": [
    "Frame Count = 10000: Timeout after 120s",
    "..."
  ],
  "results": [
    {
      "test": "North Pole",
      "category": "boundaries",
      "status": "PASS",
      "duration_sec": 2.34,
      "details": {...}
    },
    ...
  ]
}
```

---

## Sample Workflows

### Weekly Production Audit
```bash
# Monday 9 AM
ssh user@production-server
cd Castle-Celestial-View
./scripts/stability-audit/run-all-audits.sh --target http://localhost:8000 \
  --report audit-weekly-$(date +%Y%m%d).html

# Results saved to audit-weekly-20260801.html
# Review for any regressions vs. previous audit
```

### Pre-Release Stability Check
```bash
# Before deploying v1.1.1
./scripts/stability-audit/run-all-audits.sh --target http://staging.castlecelestialview.net

# If all PASS, safe to deploy
# If any FAIL, investigate before release
```

### Investigate Reported Issue
```bash
# User reports frame_count=10000 fails
python test-boundaries.py --target http://localhost:8000 --verbose

# Get detailed output of what's happening
# Results -> GitHub issue #208 (Stability & Crash Prevention)
```

### Expand Test Suite
```bash
# Discovered new edge case? Add it!
# Edit test-boundaries.py, add new test function
# Run: python test-boundaries.py --verbose
# If stable, commit and document
```

---

## Interpreting Results

### PASS (Green)
Request completed successfully, returned expected data, no errors.

### FAIL (Yellow)
Request succeeded but validation failed (e.g., frame count mismatch, memory growth exceeded threshold).

### ERROR (Red)
Request crashed, timed out, or threw unhandled exception. **Critical—investigate immediately.**

### Performance Thresholds
| Metric | Threshold | Impact |
|--------|-----------|--------|
| Memory growth (100 requests) | <10% | No leak |
| Response time (frame_count=1000) | <30 sec | Acceptable |
| Concurrent requests (10 simultaneous) | 0 failures | Thread-safe |
| Error rate (100 mixed requests) | <1% | Robust |

---

## Extending the Audit Suite

### Add New Test Category
```python
# scripts/stability-audit/test-new-category.py
import argparse
import json
from datetime import datetime

class NewCategoryAudit:
    def __init__(self, target="http://localhost:8000", timeout=120):
        self.target = target
        self.timeout = timeout
        self.results = []
    
    def test_something(self):
        """Test description."""
        # Make request
        # Validate result
        # Return status + details
        pass
    
    def run_all(self):
        """Run all tests in this category."""
        self.test_something()
        return self.results

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default="http://localhost:8000")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    
    audit = NewCategoryAudit(target=args.target, timeout=args.timeout)
    results = audit.run_all()
    
    # Output results...
```

Then update `run-all-audits.sh` to include the new test.

---

## Troubleshooting

### Script Won't Run
```bash
# Make sure Python 3.8+ is available
python --version

# Make sure required packages installed
pip install httpx pydantic

# Make sure shell scripts are executable
chmod +x run-all-audits.sh
```

### Target API Unreachable
```bash
# Test connectivity
curl http://localhost:8000/docs

# Check server status
ssh user@production-server
systemctl status gunicorn  # or however it's running

# Use --target to point to correct URL
python test-boundaries.py --target http://staging.internal.net:8000
```

### Tests Timeout
```bash
# Increase timeout
python test-boundaries.py --timeout 300

# Check server CPU/memory
ssh user@production-server
top -b -n 1

# May indicate real performance issue (see FAIL vs. ERROR distinction)
```

### Unexpected Results
```bash
# Run with verbose output
./run-all-audits.sh --verbose

# Save JSON results for analysis
./run-all-audits.sh --json > audit-debug.json

# Review output, file GitHub issue with results
```

---

## Integration with Issue #208

**These audits directly support Issue #208: Stability & Crash Prevention**

- Failed audits → Create GitHub issues with specific findings
- Performance data → Estimate resource requirements
- Edge cases discovered → Update test-astropy-limits.py
- New vulnerabilities → Add tests to catch regression

---

## File Structure
```
scripts/stability-audit/
├── README.md                      # This file
├── run-all-audits.sh              # Master orchestrator
├── test-boundaries.py             # Boundary condition testing
├── test-astropy-limits.py         # IERS/astropy edge cases
├── test-resource-safety.py        # Memory/connection leaks
├── test-concurrency.py            # Simultaneous request handling
├── test-error-handling.py         # Crash resistance
└── .gitignore                     # Exclude results files
```

---

## Status & Roadmap

**Current**: Core 5 test categories implemented  
**Planned**: 
- Load testing (sustained high traffic)
- Regression detection (compare against baseline)
- Automated alerting (email on CRITICAL failures)
- Dashboard/visualization (historical trend tracking)

---

**Last Updated**: 2026-08-01  
**Owner**: Internal Security/Stability Team  
**Related Issues**: #206 (Security Hardening), #208 (Stability & Crash Prevention)
