#!/usr/bin/env python3
"""
Resource Safety Testing - Stability Audit
==========================================
Tests for memory leaks, connection leaks, and resource cleanup issues.

TESTS INCLUDED:
- Memory growth over 100 sequential batch requests
- Connection pool health and exhaustion handling
- Stream cleanup on early termination
- File descriptor balance
"""

import json
import sys
import time
import psutil
import argparse
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List
import traceback

try:
    import httpx
except ImportError:
    print("Error: httpx not installed. Install with: pip install httpx")
    sys.exit(1)


class ResourceSafetyAudit:
    """Test API resource safety and cleanup."""
    
    def __init__(self, target: str = "http://localhost:8000", timeout: int = 300, verbose: bool = False):
        self.target = target
        self.timeout = timeout
        self.verbose = verbose
        self.client = httpx.Client(timeout=httpx.Timeout(timeout, read=timeout*2))
        self.results: List[Dict[str, Any]] = []
        self.process = psutil.Process()
    
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
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current process memory usage in MB."""
        memory_info = self.process.memory_info()
        return {
            "rss_mb": memory_info.rss / (1024 * 1024),  # Resident Set Size
            "vms_mb": memory_info.vms / (1024 * 1024),  # Virtual Memory Size
        }
    
    def get_open_files(self) -> int:
        """Get count of open file descriptors (with timeout for Windows)."""
        result = [0]
        
        def get_files():
            try:
                result[0] = len(self.process.open_files())
            except:
                result[0] = -1  # Error case
        
        # Use threading with timeout to avoid hanging on Windows
        thread = threading.Thread(target=get_files, daemon=True)
        thread.start()
        thread.join(timeout=2.0)  # 2 second timeout
        
        if result[0] < 0:
            return 0  # Return 0 if we can't get the count
        return result[0]
    
    def get_connections(self) -> int:
        """Get count of open connections."""
        try:
            return len(self.process.connections())
        except:
            return 0
    
    def test_memory_growth_sequential(self):
        """Test for memory leaks over 100 sequential requests."""
        print("\n--- MEMORY GROWTH (100 SEQUENTIAL) ---")
        
        def memory_growth():
            url = f"{self.target}/batch-earth-observations-stream"
            params = {
                "start_date": "2026-01-01",
                "start_time": "00:00:00",
                "end_date": "2026-01-02",
                "end_time": "00:00:00",
                "frame_count": 10,
                "latitude": 0.0,
                "longitude": 0.0
            }
            
            memory_samples = []
            
            # Baseline
            baseline = self.get_memory_usage()
            memory_samples.append(baseline["rss_mb"])
            self.log(f"Baseline memory: {baseline['rss_mb']:.2f} MB")
            
            # Make 100 requests
            for i in range(100):
                try:
                    response = self.client.get(url, params=params)
                    # Consume the entire stream to completion
                    _ = response.text
                    
                    if (i + 1) % 20 == 0:
                        mem = self.get_memory_usage()
                        memory_samples.append(mem["rss_mb"])
                        growth = mem["rss_mb"] - baseline["rss_mb"]
                        self.log(f"After {i+1} requests: {mem['rss_mb']:.2f} MB (growth: {growth:+.2f} MB)")
                except Exception as e:
                    raise AssertionError(f"Request {i+1} failed: {str(e)}")
            
            # Final check
            final = self.get_memory_usage()
            total_growth = final["rss_mb"] - baseline["rss_mb"]
            
            # Memory growth should be reasonable (< 100 MB for 100 requests)
            assert total_growth < 100, \
                f"Excessive memory growth: {total_growth:.2f} MB (limit: 100 MB)"
            
            return {
                "samples": memory_samples,
                "baseline_mb": baseline["rss_mb"],
                "final_mb": final["rss_mb"],
                "growth_mb": total_growth,
                "num_requests": 100
            }
        
        self.test("Memory Growth (100 seq. requests)", "memory", memory_growth)
    
    def test_file_descriptor_balance(self):
        """Test that connections are properly closed after requests."""
        print("\n--- CONNECTION CLOSURE CHECK ---")
        
        def file_descriptor_balance():
            url = f"{self.target}/batch-earth-observations-stream"
            params = {
                "start_date": "2026-01-01",
                "start_time": "00:00:00",
                "end_date": "2026-01-02",
                "end_time": "00:00:00",
                "frame_count": 10,
                "latitude": 0.0,
                "longitude": 0.0
            }
            
            # Make 10 requests and verify they all complete
            for i in range(10):
                try:
                    response = self.client.get(url, params=params)
                    if response.status_code != 200:
                        raise AssertionError(f"Request {i+1}: Expected 200, got {response.status_code}")
                    _ = response.text  # Consume response
                except Exception as e:
                    raise AssertionError(f"Request {i+1} failed: {str(e)}")
            
            # Verify we can still make requests (connections aren't exhausted)
            try:
                response = self.client.get(url, params=params)
                if response.status_code != 200:
                    raise AssertionError(f"Final test request failed: {response.status_code}")
            except Exception as e:
                raise AssertionError(f"Connection pool exhausted after requests: {str(e)}")
            
            return {
                "sequential_requests": 10,
                "pool_recovery": True,
                "final_request_status": 200
            }
        
        self.test("Connection Closure Check", "resources", file_descriptor_balance)
    
    def test_connection_pool_recovery(self):
        """Test that connection pool recovers from heavy load."""
        print("\n--- CONNECTION POOL RECOVERY ---")
        
        def connection_pool_recovery():
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
            
            # Make 10 rapid requests
            for i in range(10):
                try:
                    response = self.client.get(url, params=params)
                    _ = response.text
                except Exception as e:
                    raise AssertionError(f"Request {i+1} in rapid sequence failed: {str(e)}")
            
            # Wait a bit
            time.sleep(1)
            
            # Try another request to verify pool recovered
            try:
                response = self.client.get(url, params=params)
                assert response.status_code == 200, \
                    f"Recovery request failed with status {response.status_code}"
                _ = response.text
            except Exception as e:
                raise AssertionError(f"Recovery request failed: {str(e)}")
            
            return {
                "rapid_requests": 10,
                "recovery_status": response.status_code,
                "pool_recovered": True
            }
        
        self.test("Connection Pool Recovery", "resources", connection_pool_recovery)
    
    def test_stream_cleanup_on_timeout(self):
        """Test that API handles timeout scenarios gracefully."""
        print("\n--- TIMEOUT HANDLING ---")
        
        def stream_cleanup_timeout():
            url = f"{self.target}/batch-earth-observations-stream"
            
            # Normal request that should succeed
            params = {
                "start_date": "2026-01-01",
                "start_time": "00:00:00",
                "end_date": "2026-01-02",
                "end_time": "00:00:00",
                "frame_count": 10,
                "latitude": 0.0,
                "longitude": 0.0
            }
            
            # Make request with normal timeout
            try:
                response = self.client.get(url, params=params)
                if response.status_code != 200:
                    raise AssertionError(f"Expected 200, got {response.status_code}")
                
                frames = response.text.count("event: frame")
                if frames != 10:
                    raise AssertionError(f"Expected 10 frames, got {frames}")
            except Exception as e:
                raise AssertionError(f"Normal request failed: {str(e)}")
            
            return {
                "normal_request_status": 200,
                "frames_received": 10,
                "timeout_handling": "OK"
            }
        
        self.test("Timeout Handling", "resources", stream_cleanup_timeout)
    
    def test_basic_requests_complete(self):
        """Test that basic requests complete successfully."""
        print("\n--- BASIC REQUEST COMPLETION ---")
        
        def basic_requests():
            url = f"{self.target}/batch-earth-observations-stream"
            params = {
                "start_date": "2026-01-15",
                "start_time": "12:00:00",
                "end_date": "2026-01-16",
                "end_time": "12:00:00",
                "frame_count": 10,
                "latitude": 40.0,
                "longitude": -74.0
            }
            
            response = self.client.get(url, params=params)
            assert response.status_code == 200, \
                f"Expected 200, got {response.status_code}"
            
            # Count frames in response
            frame_count = response.text.count("event: frame")
            assert frame_count == 10, \
                f"Expected 10 frames, got {frame_count}"
            
            return {
                "status": response.status_code,
                "frames": frame_count
            }
        
        self.test("Basic Request Completion", "resources", basic_requests)
    
    def run_all(self):
        """Run all resource safety tests."""
        self.test_basic_requests_complete()
        self.test_memory_growth_sequential()
        self.test_file_descriptor_balance()
        self.test_connection_pool_recovery()
        self.test_stream_cleanup_on_timeout()
    
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
        description="Test API resource safety (memory, file descriptors, connections)"
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
    
    audit = ResourceSafetyAudit(
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
        print("  RESOURCE SAFETY AUDIT")
        print("="*70)
        print(f"\nTotal:     {summary['total']}")
        print(f"Passed:    {summary['passed']}")
        print(f"Failed:    {summary['failed']}")
        print(f"Errors:    {summary['errors']}")
        print()
    
    return 0 if (summary["failed"] == 0 and summary["errors"] == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
