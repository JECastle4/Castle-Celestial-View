#!/usr/bin/env python3
"""
Error Handling Testing - Stability Audit
=========================================
Tests that API fails gracefully without crashes or information disclosure.
"""

import json
import sys
import time
import argparse
from datetime import datetime
from typing import Dict, Any, List
import traceback

try:
    import httpx
except ImportError:
    print("Error: httpx not installed. Install with: pip install httpx")
    sys.exit(1)


class ErrorHandlingAudit:
    """Test error handling and crash resistance."""
    
    def __init__(self, target: str = "http://localhost:8000", timeout: int = 120, verbose: bool = False):
        self.target = target
        self.timeout = timeout
        self.verbose = verbose
        self.client = httpx.Client(timeout=timeout)
        self.results: List[Dict[str, Any]] = []
        self.critical_issues: List[str] = []
    
    def log(self, msg: str):
        """Print only if verbose."""
        if self.verbose:
            print(msg)
    
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
            self.critical_issues.append(f"{name}: {result['error']['message']}")
        
        result["duration_sec"] = time.time() - start
        self.results.append(result)
        return result
    
    # ========================================================================
    # MALFORMED REQUEST TESTS
    # ========================================================================
    
    def test_invalid_requests(self):
        """Test handling of malformed/invalid requests."""
        print("\n--- MALFORMED REQUEST HANDLING ---")
        
        def missing_required_field():
            # Missing start_date parameter
            url = f"{self.target}/batch-earth-observations-stream"
            params = {
                "start_time": "00:00:00",
                "end_date": "2026-01-02",
                "end_time": "00:00:00",
                "frame_count": 10,
                "latitude": 0.0,
                "longitude": 0.0
            }
            response = self.client.get(url, params=params)
            assert response.status_code == 422, \
                f"Expected 422 for missing field, got {response.status_code}"
            assert "application/json" in response.headers.get("content-type", ""), \
                "Expected JSON response"
            return {"status": response.status_code, "content_type": response.headers.get("content-type")}
        
        def invalid_date_format():
            # Invalid date format
            url = f"{self.target}/batch-earth-observations-stream"
            params = {
                "start_date": "01-01-2026",  # Wrong format
                "start_time": "00:00:00",
                "end_date": "2026-01-02",
                "end_time": "00:00:00",
                "frame_count": 10,
                "latitude": 0.0,
                "longitude": 0.0
            }
            response = self.client.get(url, params=params)
            assert response.status_code == 422, \
                f"Expected 422 for invalid date, got {response.status_code}"
            assert response.text, "Expected error message in response"
            return {"status": response.status_code}
        
        def invalid_time_format():
            # Invalid time format
            url = f"{self.target}/batch-earth-observations-stream"
            params = {
                "start_date": "2026-01-01",
                "start_time": "25:99:99",  # Invalid time
                "end_date": "2026-01-02",
                "end_time": "00:00:00",
                "frame_count": 10,
                "latitude": 0.0,
                "longitude": 0.0
            }
            response = self.client.get(url, params=params)
            assert response.status_code == 422, \
                f"Expected 422 for invalid time, got {response.status_code}"
            return {"status": response.status_code}
        
        self.test("Missing Required Field", "malformed", missing_required_field)
        self.test("Invalid Date Format", "malformed", invalid_date_format)
        self.test("Invalid Time Format", "malformed", invalid_time_format)
    
    # ========================================================================
    # OUT-OF-RANGE VALUE TESTS
    # ========================================================================
    
    def test_out_of_range_values(self):
        """Test handling of out-of-range numeric values."""
        print("\n--- OUT-OF-RANGE VALUE HANDLING ---")
        
        def latitude_too_high():
            # Latitude > 90
            url = f"{self.target}/batch-earth-observations-stream"
            params = {
                "start_date": "2026-01-01",
                "start_time": "00:00:00",
                "end_date": "2026-01-02",
                "end_time": "00:00:00",
                "frame_count": 10,
                "latitude": 91.0,
                "longitude": 0.0
            }
            response = self.client.get(url, params=params)
            assert response.status_code == 422, \
                f"Expected 422 for latitude > 90, got {response.status_code}"
            return {"status": response.status_code}
        
        def longitude_too_high():
            # Longitude > 180
            url = f"{self.target}/batch-earth-observations-stream"
            params = {
                "start_date": "2026-01-01",
                "start_time": "00:00:00",
                "end_date": "2026-01-02",
                "end_time": "00:00:00",
                "frame_count": 10,
                "latitude": 0.0,
                "longitude": 181.0
            }
            response = self.client.get(url, params=params)
            assert response.status_code == 422, \
                f"Expected 422 for longitude > 180, got {response.status_code}"
            return {"status": response.status_code}
        
        def frame_count_too_low():
            # frame_count < 2
            url = f"{self.target}/batch-earth-observations-stream"
            params = {
                "start_date": "2026-01-01",
                "start_time": "00:00:00",
                "end_date": "2026-01-02",
                "end_time": "00:00:00",
                "frame_count": 1,
                "latitude": 0.0,
                "longitude": 0.0
            }
            response = self.client.get(url, params=params)
            assert response.status_code == 422, \
                f"Expected 422 for frame_count < 2, got {response.status_code}"
            return {"status": response.status_code}
        
        def frame_count_negative():
            # frame_count < 0
            url = f"{self.target}/batch-earth-observations-stream"
            params = {
                "start_date": "2026-01-01",
                "start_time": "00:00:00",
                "end_date": "2026-01-02",
                "end_time": "00:00:00",
                "frame_count": -1,
                "latitude": 0.0,
                "longitude": 0.0
            }
            response = self.client.get(url, params=params)
            assert response.status_code == 422, \
                f"Expected 422 for negative frame_count, got {response.status_code}"
            return {"status": response.status_code}
        
        self.test("Latitude Too High (91°)", "outofrange", latitude_too_high)
        self.test("Longitude Too High (181°)", "outofrange", longitude_too_high)
        self.test("Frame Count Too Low (1)", "outofrange", frame_count_too_low)
        self.test("Frame Count Negative (-1)", "outofrange", frame_count_negative)
    
    # ========================================================================
    # ERROR MESSAGE DISCLOSURE TESTS
    # ========================================================================
    
    def test_error_message_disclosure(self):
        """Test that error messages don't leak sensitive information."""
        print("\n--- ERROR MESSAGE DISCLOSURE ---")
        
        def no_stack_trace():
            # Invalid request
            url = f"{self.target}/batch-earth-observations-stream"
            params = {
                "start_date": "not-a-date",
                "start_time": "00:00:00",
                "end_date": "2026-01-02",
                "end_time": "00:00:00",
                "frame_count": 10,
                "latitude": 0.0,
                "longitude": 0.0
            }
            response = self.client.get(url, params=params)
            assert response.status_code == 422, f"Expected 422, got {response.status_code}"
            
            # Check response doesn't contain common stack trace markers
            text = response.text.lower()
            forbidden = ["traceback", "file \"", "line ", "exception", "python"]
            for marker in forbidden:
                assert marker not in text, \
                    f"Stack trace disclosure detected: '{marker}' in response"
            
            return {"status": response.status_code, "has_traceback": False}
        
        def json_response_on_error():
            # Invalid request
            url = f"{self.target}/batch-earth-observations-stream"
            params = {
                "start_date": "2026-01-01",
                "start_time": "00:00:00",
                "end_date": "2026-01-02",
                "end_time": "00:00:00",
                "frame_count": "not-a-number",  # Should be int
                "latitude": 0.0,
                "longitude": 0.0
            }
            response = self.client.get(url, params=params)
            assert response.status_code in (400, 422), \
                f"Expected 4xx error, got {response.status_code}"
            
            # Should be JSON, not HTML
            assert "application/json" in response.headers.get("content-type", ""), \
                f"Expected JSON response, got {response.headers.get('content-type')}"
            
            # Should be valid JSON
            try:
                json.loads(response.text)
            except json.JSONDecodeError:
                raise AssertionError("Response is not valid JSON")
            
            return {"status": response.status_code, "is_json": True}
        
        self.test("No Stack Trace in Error", "disclosure", no_stack_trace)
        self.test("JSON Response on Error", "disclosure", json_response_on_error)
    
    # ========================================================================
    # TIME CONSTRAINT TESTS
    # ========================================================================
    
    def test_time_constraints(self):
        """Test handling of time constraint violations."""
        print("\n--- TIME CONSTRAINT HANDLING ---")
        
        def inverted_times():
            # end_date before start_date
            url = f"{self.target}/batch-earth-observations-stream"
            params = {
                "start_date": "2026-01-02",
                "start_time": "00:00:00",
                "end_date": "2026-01-01",  # Before start
                "end_time": "00:00:00",
                "frame_count": 10,
                "latitude": 0.0,
                "longitude": 0.0
            }
            response = self.client.get(url, params=params)
            assert response.status_code == 400 or response.status_code == 422, \
                f"Expected 4xx for inverted times, got {response.status_code}"
            return {"status": response.status_code}
        
        def same_times():
            # start == end (should fail - need at least 2 frames)
            url = f"{self.target}/batch-earth-observations-stream"
            params = {
                "start_date": "2026-01-01",
                "start_time": "00:00:00",
                "end_date": "2026-01-01",
                "end_time": "00:00:00",
                "frame_count": 10,
                "latitude": 0.0,
                "longitude": 0.0
            }
            response = self.client.get(url, params=params)
            assert response.status_code == 400 or response.status_code == 422, \
                f"Expected 4xx for same times, got {response.status_code}"
            return {"status": response.status_code}
        
        self.test("Inverted Times (end before start)", "timeconstraint", inverted_times)
        self.test("Same Start and End Time", "timeconstraint", same_times)
    
    # ========================================================================
    # GRACEFUL DEGRADATION
    # ========================================================================
    
    def test_graceful_degradation(self):
        """Test server recovery after errors."""
        print("\n--- GRACEFUL DEGRADATION ---")
        
        def server_available_after_error():
            # Send bad request
            url = f"{self.target}/batch-earth-observations-stream"
            params = {
                "start_date": "not-a-date",
                "start_time": "00:00:00",
                "end_date": "2026-01-02",
                "end_time": "00:00:00",
                "frame_count": 10,
                "latitude": 0.0,
                "longitude": 0.0
            }
            bad_response = self.client.get(url, params=params)
            
            # Now send a valid request
            url = f"{self.target}/batch-earth-observations-stream"
            params = {
                "start_date": "2026-01-01",
                "start_time": "00:00:00",
                "end_date": "2026-01-02",
                "end_time": "00:00:00",
                "frame_count": 5,
                "latitude": 0.0,
                "longitude": 0.0
            }
            good_response = self.client.get(url, params=params)
            
            assert good_response.status_code == 200, \
                f"Server failed to recover after error: {good_response.status_code}"
            assert good_response.text, "Expected SSE stream in response"
            
            return {
                "error_response": bad_response.status_code,
                "recovery_response": good_response.status_code,
                "recovered": good_response.status_code == 200
            }
        
        self.test("Server Recovery After Error", "graceful", server_available_after_error)
    
    def run_all(self):
        """Run all error handling tests."""
        self.test_invalid_requests()
        self.test_out_of_range_values()
        self.test_error_message_disclosure()
        self.test_time_constraints()
        self.test_graceful_degradation()
    
    def print_summary(self):
        """Print test summary."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        errors = sum(1 for r in self.results if r["status"] == "ERROR")
        
        print(f"\n{'='*70}")
        print("TEST SUMMARY - ERROR HANDLING")
        print(f"{'='*70}")
        print(f"Total:     {total}")
        print(f"Passed:    {passed} ✓")
        print(f"Failed:    {failed} ✗")
        print(f"Errors:    {errors} ⚠")
        
        if self.critical_issues:
            print(f"\nCRITICAL ISSUES ({len(self.critical_issues)}):")
            for issue in self.critical_issues:
                print(f"  • {issue}")
        
        return 0 if errors == 0 and failed == 0 else 1


def main():
    parser = argparse.ArgumentParser(
        description="Test API error handling and crash resistance"
    )
    parser.add_argument("--target", default="http://localhost:8000",
                       help="API target URL")
    parser.add_argument("--timeout", type=int, default=120,
                       help="Request timeout in seconds")
    parser.add_argument("--verbose", action="store_true",
                       help="Verbose output")
    parser.add_argument("--json", action="store_true",
                       help="JSON output only")
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
    
    if not args.json:
        print(f"\n{'='*70}")
        print("  ERROR HANDLING AUDIT")
        print(f"  Target: {sanitize_target(args.target)}")
        print(f"{'='*70}")
    
    audit = ErrorHandlingAudit(
        target=args.target,
        timeout=args.timeout,
        verbose=args.verbose
    )
    
    try:
        audit.run_all()
    except Exception as e:
        print(f"\nFatal error: {e}")
        if args.verbose:
            traceback.print_exc()
        return 1
    
    if args.json:
        output = {
            "timestamp": datetime.now().isoformat(),
            "target": sanitize_target(args.target),
            "results": sanitize_results(audit.results),
            "critical_issues": sanitize_critical_issues(audit.critical_issues)
        }
        print(json.dumps(output, indent=2))
    else:
        return audit.print_summary()


if __name__ == "__main__":
    sys.exit(main())
