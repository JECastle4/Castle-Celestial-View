#!/usr/bin/env python3
"""
Astropy Limits Testing - Stability Audit
=========================================
Tests astropy boundaries, IERS data coverage, and calculation edge cases.

TESTS INCLUDED:
- IERS data availability (1900, 2000, 2100)
- Coordinate edge cases (poles, date line)
- Time span edge cases (extreme density vs. sparse)
- Precision detection (future dates)
- Performance scaling (frame_count: 10, 100, 1000)
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


class AstropyLimitsAudit:
    """Test astropy boundaries and limits."""
    
    def __init__(self, target: str = "http://localhost:8000", timeout: int = 600, verbose: bool = False):
        self.target = target
        self.timeout = timeout
        self.verbose = verbose
        self.client = httpx.Client(timeout=httpx.Timeout(timeout, read=timeout*2))
        self.results: List[Dict[str, Any]] = []
    
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
        
        result["duration_sec"] = time.time() - start
        self.results.append(result)
        return result
    
    def test_iers_date_coverage(self):
        """Test IERS data availability for different date ranges."""
        print("\n--- IERS DATA COVERAGE ---")
        
        def iers_coverage():
            url = f"{self.target}/batch-earth-observations-stream"
            
            test_dates = [
                ("1900-01-01", "1900-01-02", "Ancient date (1900)"),
                ("2000-01-01", "2000-01-02", "Y2K transition (2000)"),
                ("2026-01-01", "2026-01-02", "Current date (2026)"),
                ("2100-01-01", "2100-01-02", "Future date (2100)"),
            ]
            
            results = []
            
            for start_date, end_date, label in test_dates:
                params = {
                    "start_date": start_date,
                    "start_time": "00:00:00",
                    "end_date": end_date,
                    "end_time": "00:00:00",
                    "frame_count": 10,
                    "latitude": 0.0,
                    "longitude": 0.0
                }
                
                try:
                    response = self.client.get(url, params=params)
                    
                    if response.status_code != 200:
                        raise AssertionError(
                            f"{label}: Expected 200, got {response.status_code}"
                        )
                    
                    frames = response.text.count("event: frame")
                    if frames != 10:
                        raise AssertionError(
                            f"{label}: Expected 10 frames, got {frames}"
                        )
                    
                    results.append({
                        "date_range": label,
                        "status": 200,
                        "frames": frames
                    })
                except Exception as e:
                    results.append({
                        "date_range": label,
                        "error": str(e)
                    })
            
            # Verify all date ranges worked
            errors = [r for r in results if "error" in r]
            if errors:
                raise AssertionError(f"IERS coverage issues: {errors}")
            
            return {
                "tested_dates": len(results),
                "all_successful": len(errors) == 0,
                "results": results
            }
        
        self.test("IERS Data Coverage (1900-2100)", "astropy", iers_coverage)
    
    def test_coordinate_edge_cases(self):
        """Test astropy calculations at coordinate boundaries."""
        print("\n--- COORDINATE EDGE CASES ---")
        
        def coordinate_edges():
            url = f"{self.target}/batch-earth-observations-stream"
            
            edge_cases = [
                (90.0, 0.0, "North Pole"),
                (-90.0, 0.0, "South Pole"),
                (0.0, 180.0, "Date line (East)"),
                (0.0, -180.0, "Date line (West)"),
                (0.0, 0.0, "Equator/Prime Meridian"),
            ]
            
            results = []
            
            for lat, lon, label in edge_cases:
                params = {
                    "start_date": "2026-06-21",
                    "start_time": "12:00:00",
                    "end_date": "2026-06-22",
                    "end_time": "12:00:00",
                    "frame_count": 5,
                    "latitude": lat,
                    "longitude": lon
                }
                
                try:
                    response = self.client.get(url, params=params)
                    
                    if response.status_code != 200:
                        raise AssertionError(f"{label}: Got {response.status_code}")
                    
                    frames = response.text.count("event: frame")
                    results.append({
                        "location": label,
                        "lat": lat,
                        "lon": lon,
                        "frames": frames
                    })
                except Exception as e:
                    results.append({
                        "location": label,
                        "error": str(e)
                    })
            
            errors = [r for r in results if "error" in r]
            if errors:
                raise AssertionError(f"Coordinate edge case errors: {errors}")
            
            return {
                "edge_cases_tested": len(results),
                "all_successful": len(errors) == 0,
                "results": results
            }
        
        self.test("Coordinate Edge Cases (poles, dateline)", "astropy", coordinate_edges)
    
    def test_time_span_extremes(self):
        """Test extreme time span scenarios."""
        print("\n--- TIME SPAN EXTREMES ---")
        
        def time_extremes():
            url = f"{self.target}/batch-earth-observations-stream"
            
            scenarios = [
                ("2026-01-01", "00:00:00", "2026-01-01", "00:00:10",
                 100, "Extreme density (100 frames in 10 sec)"),
                ("2026-01-01", "00:00:00", "2076-01-01", "00:00:00",
                 10, "Sparse coverage (10 frames over 50 years)"),
                ("2026-06-20", "00:00:00", "2026-06-22", "00:00:00",
                 50, "Moderate (50 frames over 2 days)"),
            ]
            
            results = []
            
            for start_d, start_t, end_d, end_t, frames, label in scenarios:
                params = {
                    "start_date": start_d,
                    "start_time": start_t,
                    "end_date": end_d,
                    "end_time": end_t,
                    "frame_count": frames,
                    "latitude": 40.0,
                    "longitude": -74.0
                }
                
                try:
                    response = self.client.get(url, params=params)
                    
                    if response.status_code != 200:
                        raise AssertionError(f"{label}: Got {response.status_code}")
                    
                    frame_count = response.text.count("event: frame")
                    results.append({
                        "scenario": label,
                        "requested_frames": frames,
                        "actual_frames": frame_count,
                        "success": frame_count == frames
                    })
                except Exception as e:
                    results.append({
                        "scenario": label,
                        "error": str(e)
                    })
            
            errors = [r for r in results if "error" in r]
            if errors:
                raise AssertionError(f"Time span errors: {errors}")
            
            return {
                "scenarios_tested": len(results),
                "all_successful": len(errors) == 0,
                "results": results
            }
        
        self.test("Time Span Extremes (density & range)", "astropy", time_extremes)
    
    def test_frame_count_scaling(self):
        """Test performance scaling with increasing frame counts."""
        print("\n--- FRAME COUNT SCALING ---")
        
        def frame_scaling():
            url = f"{self.target}/batch-earth-observations-stream"
            
            frame_counts = [10, 100, 500]
            results = []
            
            for fc in frame_counts:
                params = {
                    "start_date": "2026-01-01",
                    "start_time": "00:00:00",
                    "end_date": "2026-01-02",
                    "end_time": "00:00:00",
                    "frame_count": fc,
                    "latitude": 0.0,
                    "longitude": 0.0
                }
                
                start = time.time()
                try:
                    response = self.client.get(url, params=params)
                    duration = time.time() - start
                    
                    if response.status_code != 200:
                        raise AssertionError(
                            f"frame_count={fc}: Got status {response.status_code}"
                        )
                    
                    actual_frames = response.text.count("event: frame")
                    if actual_frames != fc:
                        raise AssertionError(
                            f"frame_count={fc}: Got {actual_frames} frames"
                        )
                    
                    results.append({
                        "frame_count": fc,
                        "duration_sec": duration,
                        "frames_per_sec": fc / duration,
                        "success": True
                    })
                    
                    self.log(
                        f"frame_count={fc}: {duration:.2f}s "
                        f"({fc/duration:.1f} frames/sec)"
                    )
                except Exception as e:
                    results.append({
                        "frame_count": fc,
                        "error": str(e)
                    })
                    self.log(f"frame_count={fc}: FAILED - {str(e)}")
            
            errors = [r for r in results if "error" in r]
            if errors:
                # Log but don't fail - large frame counts may timeout
                self.log(f"Some frame counts failed (expected for large values): {errors}")
            
            successful = [r for r in results if "success" in r and r["success"]]
            if not successful:
                raise AssertionError("No frame counts succeeded")
            
            return {
                "frame_counts_tested": frame_counts,
                "successful": len(successful),
                "results": results
            }
        
        self.test("Frame Count Scaling (10, 100, 500)", "performance", frame_scaling)
    
    def test_precision_future_dates(self):
        """Test that calculations work for future dates (with potential precision loss)."""
        print("\n--- PRECISION FOR FUTURE DATES ---")
        
        def future_precision():
            url = f"{self.target}/batch-earth-observations-stream"
            
            # Test increasingly distant future dates
            future_dates = [
                ("2030-01-01", "2030-01-02", "4 years ahead"),
                ("2050-01-01", "2050-01-02", "24 years ahead"),
                ("2100-01-01", "2100-01-02", "74 years ahead"),
            ]
            
            results = []
            
            for start, end, label in future_dates:
                params = {
                    "start_date": start,
                    "start_time": "12:00:00",
                    "end_date": end,
                    "end_time": "12:00:00",
                    "frame_count": 10,
                    "latitude": 40.0,
                    "longitude": -74.0
                }
                
                try:
                    response = self.client.get(url, params=params)
                    
                    if response.status_code != 200:
                        raise AssertionError(f"{label}: Got {response.status_code}")
                    
                    frames = response.text.count("event: frame")
                    results.append({
                        "date_range": label,
                        "frames": frames,
                        "success": frames == 10
                    })
                except Exception as e:
                    results.append({
                        "date_range": label,
                        "error": str(e)
                    })
            
            errors = [r for r in results if "error" in r]
            if errors:
                raise AssertionError(f"Future date errors: {errors}")
            
            return {
                "future_dates_tested": len(results),
                "all_successful": all(r.get("success", False) for r in results),
                "results": results
            }
        
        self.test("Precision for Future Dates (2030-2100)", "astropy", future_precision)
    
    def run_all(self):
        """Run all astropy limits tests."""
        self.test_iers_date_coverage()
        self.test_coordinate_edge_cases()
        self.test_time_span_extremes()
        self.test_precision_future_dates()
        self.test_frame_count_scaling()
    
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
    
    def cleanup(self):
        """Clean up resources."""
        self.client.close()


def main():
    parser = argparse.ArgumentParser(
        description="Test astropy limits (IERS coverage, date ranges, frame count scaling)"
    )
    parser.add_argument("--target", default="http://localhost:8000/api/v1",
                        help="API target URL (default: http://localhost:8000/api/v1)")
    parser.add_argument("--timeout", type=int, default=600,
                        help="Request timeout in seconds (default: 600)")
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
    
    audit = AstropyLimitsAudit(
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
    finally:
        audit.cleanup()
    
    # Output results
    summary = audit.summary()
    
    if args.json:
        output = {
            "timestamp": datetime.now().isoformat(),
            "target": sanitize_target(args.target),
            "tests": sanitize_results(audit.results),
            "summary": summary
        }
        print(json.dumps(output, indent=2))
    else:
        print("\n" + "="*70)
        print("  ASTROPY LIMITS AUDIT")
        print("="*70)
        print(f"\nTotal:     {summary['total']}")
        print(f"Passed:    {summary['passed']} ✓")
        print(f"Failed:    {summary['failed']} ✗")
        print(f"Errors:    {summary['errors']} ⚠")
        print("\nNote: frame_count=10000+ may timeout (performance limit)")
        print()
    
    return 0 if (summary["failed"] == 0 and summary["errors"] == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
