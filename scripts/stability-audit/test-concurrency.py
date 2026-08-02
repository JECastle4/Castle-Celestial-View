#!/usr/bin/env python3
"""
Concurrency Testing - Stability Audit
======================================
Tests for concurrent request handling, race conditions, and thread safety.

TESTS INCLUDED:
- Multiple concurrent batch requests (10 simultaneous)
- Mixed request types under load (70% single, 20% batch, 10% invalid)
- Race condition detection (idempotency verification)
- Cascading failure detection (API stability after errors)
"""

import json
import sys
import time
import argparse
import threading
from datetime import datetime
from typing import Dict, Any, List
import random
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import httpx
except ImportError:
    print("Error: httpx not installed. Install with: pip install httpx")
    sys.exit(1)


class ConcurrencyAudit:
    """Test API concurrency and thread safety."""
    
    def __init__(self, target: str = "http://localhost:8000", timeout: int = 300, verbose: bool = False):
        self.target = target
        self.timeout = timeout
        self.verbose = verbose
        self.results: List[Dict[str, Any]] = []
        self.lock = threading.Lock()
    
    def log(self, msg: str):
        """Print only if verbose."""
        if self.verbose:
            print(f"[{threading.current_thread().name}] {msg}")
    
    def test(self, name: str, category: str, test_func) -> Dict[str, Any]:
        """Run a single test and record results."""
        result = {
            "test": name,
            "category": category,
            "status": "PASS",
            "message": "",
            "duration_sec": 0,
            "error": None,
            "details": {}
        }
        
        print(f"[{category}] {name}...", end=" ", flush=True)
        start = time.time()
        
        try:
            details = test_func()
            result["details"] = details
            print("PASS")
        except AssertionError as e:
            result["status"] = "FAIL"
            result["message"] = str(e)
            print(f"FAIL")
            self.log(f"  {e}")
        except Exception as e:
            result["status"] = "ERROR"
            result["error"] = {
                "type": type(e).__name__,
                "message": str(e),
            }
            print(f"ERROR")
            self.log(f"  {type(e).__name__}: {e}")
        
        result["duration_sec"] = time.time() - start
        
        with self.lock:
            self.results.append(result)
        
        return result
    
    def test_concurrent_batch_requests(self):
        """Test 10 concurrent batch requests."""
        print("\n--- CONCURRENT BATCH REQUESTS ---")
        
        def concurrent_batches():
            url = f"{self.target}/batch-earth-observations-stream"
            
            def make_request(request_id: int):
                """Make a single batch request."""
                params = {
                    "start_date": "2026-01-01",
                    "start_time": "00:00:00",
                    "end_date": "2026-01-02",
                    "end_time": "00:00:00",
                    "frame_count": 20,
                    "latitude": float(request_id * 2) % 90,  # Vary latitude
                    "longitude": float(request_id * 3) % 180
                }
                
                try:
                    with httpx.Client(timeout=self.timeout) as client:
                        response = client.get(url, params=params)
                        
                        if response.status_code != 200:
                            raise AssertionError(
                                f"Request {request_id}: Expected 200, got {response.status_code}"
                            )
                        
                        # Verify response is complete
                        frame_count = response.text.count("event: frame")
                        if frame_count != 20:
                            raise AssertionError(
                                f"Request {request_id}: Expected 20 frames, got {frame_count}"
                            )
                        
                        return {
                            "request_id": request_id,
                            "status": response.status_code,
                            "frames": frame_count
                        }
                except Exception as e:
                    return {
                        "request_id": request_id,
                        "error": str(e)
                    }
            
            # Execute 10 requests concurrently
            results = []
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request, i) for i in range(10)]
                
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
                    if "error" in result:
                        raise AssertionError(result["error"])
            
            # Verify all succeeded
            successful = sum(1 for r in results if "status" in r and r["status"] == 200)
            assert successful == 10, f"Expected 10 successful, got {successful}"
            
            return {
                "concurrent_requests": 10,
                "successful": successful,
                "all_complete": len(results) == 10
            }
        
        self.test("Concurrent Batch Requests (10 parallel)", "concurrency", concurrent_batches)
    
    def test_mixed_load(self):
        """Test mixed request types under load: 70% valid, 20% batch, 10% invalid."""
        print("\n--- MIXED REQUEST LOAD ---")
        
        def mixed_load():
            batch_url = f"{self.target}/batch-earth-observations-stream"
            
            request_count = 0
            success_count = 0
            error_count = 0
            
            def make_mixed_request(request_num: int):
                """Make a request based on probability distribution."""
                rand = random.random()
                
                if rand < 0.7:
                    # 70% valid batch requests
                    params = {
                        "start_date": "2026-01-01",
                        "start_time": "00:00:00",
                        "end_date": "2026-01-02",
                        "end_time": "00:00:00",
                        "frame_count": 5,
                        "latitude": random.uniform(-85, 85),
                        "longitude": random.uniform(-170, 170)
                    }
                    expected_frames = 5
                elif rand < 0.9:
                    # 20% larger batch requests
                    params = {
                        "start_date": "2026-01-01",
                        "start_time": "00:00:00",
                        "end_date": "2026-01-03",
                        "end_time": "00:00:00",
                        "frame_count": 50,
                        "latitude": random.uniform(-85, 85),
                        "longitude": random.uniform(-170, 170)
                    }
                    expected_frames = 50
                else:
                    # 10% intentionally invalid (bad latitude)
                    params = {
                        "start_date": "2026-01-01",
                        "start_time": "00:00:00",
                        "end_date": "2026-01-02",
                        "end_time": "00:00:00",
                        "frame_count": 5,
                        "latitude": 95.0,  # Invalid
                        "longitude": 0.0
                    }
                    expected_frames = None
                
                try:
                    with httpx.Client(timeout=self.timeout) as client:
                        response = client.get(batch_url, params=params)
                        
                        if expected_frames is None:
                            # Expect error
                            if response.status_code in (400, 422):
                                return {"status": "expected_error"}
                            else:
                                raise AssertionError(
                                    f"Expected error for invalid request, got {response.status_code}"
                                )
                        else:
                            # Expect success
                            if response.status_code != 200:
                                raise AssertionError(
                                    f"Expected 200, got {response.status_code}"
                                )
                            
                            frame_count = response.text.count("event: frame")
                            if frame_count != expected_frames:
                                raise AssertionError(
                                    f"Expected {expected_frames} frames, got {frame_count}"
                                )
                            
                            return {"status": "success", "frames": frame_count}
                except Exception as e:
                    return {"status": "error", "error": str(e)}
            
            # Execute 30 mixed requests
            results = []
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_mixed_request, i) for i in range(30)]
                
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
                    request_count += 1
                    
                    if result["status"] == "success":
                        success_count += 1
                    elif result["status"] == "expected_error":
                        success_count += 1  # Count expected errors as success
                    elif result["status"] == "error":
                        error_count += 1
            
            # Should have mostly successes
            assert error_count == 0, f"Unexpected errors: {error_count}"
            assert request_count == 30, f"Expected 30 requests, got {request_count}"
            
            return {
                "total_requests": request_count,
                "successes": success_count,
                "errors": error_count
            }
        
        self.test("Mixed Request Load (30 diverse)", "concurrency", mixed_load)
    
    def test_idempotency(self):
        """Test that same request returns consistent results."""
        print("\n--- IDEMPOTENCY CHECK ---")
        
        def idempotency():
            url = f"{self.target}/batch-earth-observations-stream"
            params = {
                "start_date": "2026-06-15",
                "start_time": "12:00:00",
                "end_date": "2026-06-16",
                "end_time": "12:00:00",
                "frame_count": 10,
                "latitude": 40.7128,
                "longitude": -74.0060
            }
            
            results = []
            
            def make_request():
                """Make identical request."""
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(url, params=params)
                    if response.status_code != 200:
                        raise AssertionError(f"Status {response.status_code}")
                    
                    frame_count = response.text.count("event: frame")
                    return frame_count
            
            # Make 5 identical requests concurrently
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_request) for _ in range(5)]
                
                for future in as_completed(futures):
                    results.append(future.result())
            
            # All should return same frame count
            first_result = results[0]
            for result in results:
                assert result == first_result, \
                    f"Inconsistent results: {first_result} vs {result}"
            
            return {
                "identical_requests": 5,
                "consistent_results": all(r == first_result for r in results),
                "frame_count": first_result
            }
        
        self.test("Idempotency (same request 5x)", "concurrency", idempotency)
    
    def test_api_stability_after_errors(self):
        """Test API stability after receiving invalid requests."""
        print("\n--- STABILITY AFTER ERRORS ---")
        
        def stability_after_errors():
            url = f"{self.target}/batch-earth-observations-stream"
            
            # First, send some invalid requests
            invalid_params = {
                "start_date": "invalid",
                "start_time": "00:00:00",
                "end_date": "2026-01-02",
                "end_time": "00:00:00",
                "frame_count": 5,
                "latitude": 0.0,
                "longitude": 0.0
            }
            
            with httpx.Client(timeout=self.timeout) as client:
                for i in range(5):
                    response = client.get(url, params=invalid_params)
                    assert response.status_code in (400, 422), \
                        f"Expected 400/422 for invalid request, got {response.status_code}"
            
            # Now send valid requests to verify API still works
            valid_params = {
                "start_date": "2026-01-15",
                "start_time": "12:00:00",
                "end_date": "2026-01-16",
                "end_time": "12:00:00",
                "frame_count": 10,
                "latitude": 0.0,
                "longitude": 0.0
            }
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, params=valid_params)
                assert response.status_code == 200, \
                    f"API unstable after errors: got {response.status_code}"
                
                frames = response.text.count("event: frame")
                assert frames == 10, f"Expected 10 frames, got {frames}"
            
            return {
                "invalid_requests_sent": 5,
                "api_recovered": True,
                "valid_request_status": 200
            }
        
        self.test("API Stability After Errors", "concurrency", stability_after_errors)
    
    def run_all(self):
        """Run all concurrency tests."""
        self.test_concurrent_batch_requests()
        self.test_mixed_load()
        self.test_idempotency()
        self.test_api_stability_after_errors()
    
    def summary(self) -> Dict[str, Any]:
        """Generate test summary."""
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        errors = sum(1 for r in self.results if r["status"] == "ERROR")
        
        return {
            "total": len(self.results),
            "passed": passed,
            "failed": failed,
            "errors": errors
        }


def main():
    parser = argparse.ArgumentParser(
        description="Test API concurrency (concurrent requests, race conditions)"
    )
    parser.add_argument("--target", default="http://localhost:8000/api/v1",
                        help="API target URL (default: http://localhost:8000/api/v1)")
    parser.add_argument("--timeout", type=int, default=300,
                        help="Request timeout in seconds (default: 300)")
    parser.add_argument("--verbose", action="store_true",
                        help="Show detailed output")
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON")
    args = parser.parse_args()
    
    # Sanitize target for output (avoid exposing production URLs)
    def sanitize_target(url):
        """Replace sensitive parts of URL for logging."""
        import re
        return re.sub(r'https?://[^/]+', 'https://[API]', url)
    
    # Sanitize results for output (avoid exposing sensitive test data)
    def sanitize_results(results):
        """Remove sensitive details from test results before logging."""
        import re
        sanitized = []
        for result in results:
            safe_result = result.copy()
            # Redact location coordinates from test names
            if safe_result.get("test"):
                safe_result["test"] = re.sub(
                    r'\(.*?(?:latitude|longitude|coord|°).*?\)',
                    '(coordinates redacted)',
                    safe_result["test"]
                )
            # Remove full error details - only keep type
            if safe_result.get("error"):
                safe_result["error"] = {
                    "type": safe_result["error"].get("type", "Unknown"),
                    "message": "Error occurred (details redacted)"
                }
            # Remove detailed test output which may contain sensitive response data
            if safe_result.get("details"):
                safe_result["details"] = "(details redacted)"
            # Redact message if it contains URLs or sensitive info
            if safe_result.get("message"):
                safe_result["message"] = re.sub(
                    r'https?://[^\s]+',
                    'https://[API]',
                    safe_result["message"]
                )
            # Remove timing data (may reveal performance patterns)
            safe_result.pop("duration_sec", None)
            sanitized.append(safe_result)
        return sanitized
    
    def sanitize_critical_issues(issues):
        """Redact URLs and sensitive info from critical issues."""
        import re
        return [
            re.sub(r'https?://[^\s]+', 'https://[API]', issue)
            for issue in issues
        ]
    
    audit = ConcurrencyAudit(
        target=args.target,
        timeout=args.timeout,
        verbose=args.verbose
    )
    
    try:
        audit.run_all()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 130
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        if args.verbose:
            traceback.print_exc()
        return 1
    
    # Output results
    summary = audit.summary()
    
    if args.json:
        # Reconstruct output from sanitized data only (breaks taint flow)
        sanitized_results = sanitize_results(audit.results)
        safe_target = sanitize_target(args.target)
        output = {
            "timestamp": datetime.now().isoformat(),
            "target": safe_target,
            "tests": sanitized_results,
            "summary": summary
        }
        print(json.dumps(output, indent=2))
    else:
        print("\n" + "="*70)
        print("  CONCURRENCY AUDIT")
        print("="*70)
        print(f"\nTotal:     {summary['total']}")
        print(f"Passed:    {summary['passed']}")
        print(f"Failed:    {summary['failed']}")
        print(f"Errors:    {summary['errors']}")
        print()
    
    return 0 if (summary["failed"] == 0 and summary["errors"] == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
