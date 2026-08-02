#!/usr/bin/env python3
"""
Boundary Condition Testing - Stability Audit
==============================================
Tests coordinate, date, and frame count boundaries to ensure graceful handling.
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


class BoundaryAudit:
    """Test API boundary conditions."""
    
    def __init__(self, target: str = "http://localhost:8000", timeout: int = 300, verbose: bool = False):
        self.target = target
        self.timeout = timeout
        self.verbose = verbose
        # Increase individual request timeout for batch operations
        self.client = httpx.Client(timeout=httpx.Timeout(timeout, read=timeout*2))
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
            
            if "502" in str(e) or "timeout" in str(e).lower():
                self.critical_issues.append(f"{name}: {result['error']['message']}")
        
        result["duration_sec"] = time.time() - start
        self.results.append(result)
        return result
    
    def batch_request(self, 
                     start_date: str, start_time: str,
                     end_date: str, end_time: str,
                     frame_count: int,
                     latitude: float = 40.7128,
                     longitude: float = -74.0060,
                     elevation: float = 0.0) -> Dict[str, Any]:
        """Make batch observation request."""
        params = {
            "start_date": start_date,
            "start_time": start_time,
            "end_date": end_date,
            "end_time": end_time,
            "frame_count": frame_count,
            "latitude": latitude,
            "longitude": longitude,
            "elevation": elevation
        }
        
        url = f"{self.target}/batch-earth-observations-stream"
        response = self.client.get(url, params=params)
        
        # Check for error responses
        if response.status_code not in (200, 422):
            raise RuntimeError(f"HTTP {response.status_code}: {response.text[:200]}")
        
        # Count SSE frames received
        frames = 0
        if response.status_code == 200:
            for line in response.iter_lines():
                if line.startswith("event: frame"):
                    frames += 1
        
        return {
            "frames_received": frames,
            "status_code": response.status_code,
        }
    
    # ========================================================================
    # COORDINATE BOUNDARIES
    # ========================================================================
    
    def test_coordinates(self):
        """Run all coordinate boundary tests."""
        print("\n--- COORDINATE BOUNDARIES ---")
        
        def north_pole():
            result = self.batch_request(
                "2026-01-01", "00:00:00",
                "2026-01-02", "00:00:00",
                frame_count=10,
                latitude=90.0, longitude=0.0
            )
            assert result["status_code"] == 200, f"Expected 200, got {result['status_code']}"
            assert result["frames_received"] == 10, f"Expected 10 frames, got {result['frames_received']}"
            return {"latitude": 90.0, "frames": result["frames_received"]}
        
        def south_pole():
            result = self.batch_request(
                "2026-01-01", "00:00:00",
                "2026-01-02", "00:00:00",
                frame_count=10,
                latitude=-90.0, longitude=0.0
            )
            assert result["status_code"] == 200
            assert result["frames_received"] == 10
            return {"latitude": -90.0, "frames": result["frames_received"]}
        
        def date_line_plus():
            result = self.batch_request(
                "2026-01-01", "00:00:00",
                "2026-01-02", "00:00:00",
                frame_count=10,
                latitude=0.0, longitude=180.0
            )
            assert result["status_code"] == 200
            assert result["frames_received"] == 10
            return {"longitude": 180.0, "frames": result["frames_received"]}
        
        def date_line_minus():
            result = self.batch_request(
                "2026-01-01", "00:00:00",
                "2026-01-02", "00:00:00",
                frame_count=10,
                latitude=0.0, longitude=-180.0
            )
            assert result["status_code"] == 200
            assert result["frames_received"] == 10
            return {"longitude": -180.0, "frames": result["frames_received"]}
        
        def high_elevation():
            result = self.batch_request(
                "2026-01-01", "00:00:00",
                "2026-01-02", "00:00:00",
                frame_count=10,
                elevation=10000.0  # 10 km
            )
            assert result["status_code"] == 200
            assert result["frames_received"] == 10
            return {"elevation": 10000, "frames": result["frames_received"]}
        
        def low_elevation():
            result = self.batch_request(
                "2026-01-01", "00:00:00",
                "2026-01-02", "00:00:00",
                frame_count=10,
                elevation=-1000.0  # Below sea level
            )
            assert result["status_code"] == 200
            assert result["frames_received"] == 10
            return {"elevation": -1000, "frames": result["frames_received"]}
        
        self.test("North Pole (latitude=90.0)", "coordinates", north_pole)
        self.test("South Pole (latitude=-90.0)", "coordinates", south_pole)
        self.test("Date Line (+180°)", "coordinates", date_line_plus)
        self.test("Date Line (-180°)", "coordinates", date_line_minus)
        self.test("High Elevation (10 km)", "coordinates", high_elevation)
        self.test("Low Elevation (-1 km)", "coordinates", low_elevation)
    
    # ========================================================================
    # DATE RANGE BOUNDARIES
    # ========================================================================
    
    def test_dates(self):
        """Run all date boundary tests."""
        print("\n--- DATE BOUNDARIES ---")
        
        def ancient_date():
            result = self.batch_request(
                "1900-01-01", "00:00:00",
                "1900-01-02", "00:00:00",
                frame_count=10
            )
            assert result["status_code"] in (200, 422), f"Unexpected status {result['status_code']}"
            return {"year": 1900, "status": result["status_code"]}
        
        def y2k():
            result = self.batch_request(
                "2000-01-01", "00:00:00",
                "2000-01-02", "00:00:00",
                frame_count=10
            )
            assert result["status_code"] == 200
            assert result["frames_received"] == 10
            return {"year": 2000, "frames": result["frames_received"]}
        
        def far_future():
            result = self.batch_request(
                "2100-01-01", "00:00:00",
                "2100-01-02", "00:00:00",
                frame_count=10
            )
            assert result["status_code"] in (200, 422), f"Unexpected status {result['status_code']}"
            return {"year": 2100, "status": result["status_code"]}
        
        self.test("Ancient Date (1900-01-01)", "dates", ancient_date)
        self.test("Y2K Transition (2000-01-01)", "dates", y2k)
        self.test("Far Future (2100-01-01)", "dates", far_future)
    
    # ========================================================================
    # FRAME COUNT BOUNDARIES
    # ========================================================================
    
    def test_frame_counts(self):
        """Run frame count boundary and performance tests."""
        print("\n--- FRAME COUNT BOUNDARIES ---")
        
        test_values = [2, 10, 50, 100]  # Practical range for stability testing
        
        for fc in test_values:
            def frame_test(frame_count=fc):
                result = self.batch_request(
                    "2026-01-01", "00:00:00",
                    "2026-01-31", "23:59:59",  # 1 month
                    frame_count=frame_count
                )
                assert result["status_code"] in (200, 422), f"Unexpected status {result['status_code']}"
                if result["status_code"] == 200:
                    assert result["frames_received"] == frame_count, \
                        f"Expected {frame_count} frames, got {result['frames_received']}"
                return {
                    "frame_count": frame_count,
                    "frames_received": result["frames_received"],
                    "status": result["status_code"]
                }
            
            self.test(f"Frame Count = {fc:5d}", "framecount", frame_test)
    
    # ========================================================================
    # TIME SPAN EDGE CASES
    # ========================================================================
    
    def test_time_spans(self):
        """Run time span edge case tests."""
        print("\n--- TIME SPAN EDGE CASES ---")
        
        def extreme_density():
            # 50 frames in 10 seconds = 5 frames/sec
            result = self.batch_request(
                "2026-01-01", "00:00:00",
                "2026-01-01", "00:00:10",
                frame_count=50
            )
            assert result["status_code"] in (200, 422)
            return {
                "time_span": "10 seconds",
                "frame_count": 50,
                "frames_received": result["frames_received"]
            }
        
        def sparse_coverage():
            # 10 frames over 50 years
            result = self.batch_request(
                "2000-01-01", "00:00:00",
                "2050-01-01", "00:00:00",
                frame_count=10
            )
            assert result["status_code"] == 200
            assert result["frames_received"] == 10
            return {
                "time_span": "50 years",
                "frame_count": 10,
                "frames_received": result["frames_received"]
            }
        
        self.test("Extreme Density (1000 in 10 sec)", "timespan", extreme_density)
        self.test("Sparse Coverage (10 over 50 yrs)", "timespan", sparse_coverage)
    
    # ========================================================================
    # VALIDATION ERRORS
    # ========================================================================
    
    def test_validation_errors(self):
        """Test that invalid inputs are rejected gracefully."""
        print("\n--- VALIDATION ERROR HANDLING ---")
        
        def invalid_latitude():
            result = self.batch_request(
                "2026-01-01", "00:00:00",
                "2026-01-02", "00:00:00",
                frame_count=10,
                latitude=90.1  # Beyond boundary
            )
            assert result["status_code"] == 422, f"Expected 422, got {result['status_code']}"
            return {"latitude": 90.1, "status": result["status_code"]}
        
        def invalid_frame_count():
            result = self.batch_request(
                "2026-01-01", "00:00:00",
                "2026-01-02", "00:00:00",
                frame_count=1  # Below minimum of 2
            )
            assert result["status_code"] == 422, f"Expected 422, got {result['status_code']}"
            return {"frame_count": 1, "status": result["status_code"]}
        
        self.test("Invalid Latitude (90.1)", "validation", invalid_latitude)
        self.test("Invalid Frame Count (1)", "validation", invalid_frame_count)
    
    def run_all(self):
        """Run all boundary tests."""
        self.test_coordinates()
        self.test_dates()
        self.test_frame_counts()
        self.test_time_spans()
        self.test_validation_errors()
    
    def print_summary(self):
        """Print test summary."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        errors = sum(1 for r in self.results if r["status"] == "ERROR")
        
        print(f"\n{'='*70}")
        print("TEST SUMMARY - BOUNDARY CONDITIONS")
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
        description="Test API boundary conditions"
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
        print("  BOUNDARY CONDITION AUDIT")
        print(f"  Target: {sanitize_target(args.target)}")
        print(f"{'='*70}")
    
    audit = BoundaryAudit(
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
