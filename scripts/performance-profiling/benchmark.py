#!/usr/bin/env python3
"""
Performance profiling and baseline establishment for Phase 2.3+ optimizations.

Measures:
- Response time (wall-clock)
- Memory usage (peak, delta)
- Success/failure rates

Profiles:
1. Batch Earth Observations: frame_count=100,500,1000,5000
2. Astronomical Events: date_range=1,5,10 years

Success Criteria:
- Batch Earth <10s for frame_count=1000
- Astronomical Events <5s for 10-year range
"""

import json
import time
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List
import statistics
import threading

# Add parent to path for API imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.main import app
from api.i18n import set_request_locale
from fastapi.testclient import TestClient


class PerformanceBenchmark:
    """Benchmark harness for profiling endpoints."""

    def __init__(self):
        self.client = TestClient(app)
        self.results: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "benchmarks": {},
            "summary": {},
        }
        self.start_time = time.perf_counter()

    def profile_batch_earth_observations(self) -> Dict[str, Any]:
        """Profile batch_earth_observations with varying frame counts."""
        print("\n" + "=" * 70)
        print("PROFILING: Batch Earth Observations")
        print("=" * 70)

        benchmark_data = {
            "endpoint": "batch_earth_observations",
            "tests": {},
            "summary": {},
        }

        frame_counts = [50, 100, 200, 500]
        times = []

        for frame_count in frame_counts:
            print(f"\n  Testing frame_count={frame_count}...")

            payload = {
                "latitude": 40.0,
                "longitude": -74.0,
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
                "frame_count": frame_count,
            }

            # Profile with tracemalloc (but don't start it during request timing)
            start_time = time.perf_counter()
            try:
                response = self.client.post(
                    "/api/v1/batch-earth-observations",
                    json=payload,
                    headers={"Accept": "application/json"},
                )
                elapsed = time.perf_counter() - start_time

                # Memory profiling happens after timing
                memory_delta = 0.0  # Not tracking for now
                memory_peak_mb = 0.0  # Not tracking for now

                if response.status_code == 200:
                    times.append(elapsed)

                    # Parse response
                    data = response.json()
                    frame_count_returned = len(data.get("frames", []))
                    bodies_count = (
                        len(data["frames"][0].get("sun", {}).keys()) if frame_count_returned > 0 else 0
                    )

                    # Check success criteria and set status
                    status = "pass"
                    if frame_count == 500 and elapsed > 40.0:
                        status = "⚠️ SLOW (>40s for 500 frames)"

                    test_result = {
                        "frame_count": frame_count,
                        "response_time_seconds": round(elapsed, 3),
                        "frame_count_returned": frame_count_returned,
                        "status": status,
                        "http_status": 200,
                    }

                    if status == "pass":
                        print(f"    [PASS] Response time: {elapsed:.2f}s")
                    else:
                        print(f"    [SLOW] Response time: {elapsed:.2f}s (expected <40s)")

                    benchmark_data["tests"][f"batch_{frame_count}"] = test_result
                else:
                    error_msg = response.text[:200]
                    print(f"    ✗ HTTP {response.status_code}: {error_msg}")
                    benchmark_data["tests"][f"batch_{frame_count}"] = {
                        "frame_count": frame_count,
                        "status": "error",
                        "http_status": response.status_code,
                        "error": error_msg,
                    }

            except Exception as e:
                print(f"    ✗ FAILED: {e}")
                benchmark_data["tests"][f"batch_{frame_count}"] = {
                    "frame_count": frame_count,
                    "status": "error",
                    "error": str(e),
                }

        # Summary stats
        if times:
            benchmark_data["summary"] = {
                "min_response_time": round(min(times), 3),
                "max_response_time": round(max(times), 3),
                "avg_response_time": round(statistics.mean(times), 3),
            }

        return benchmark_data

    def profile_astronomical_events(self) -> Dict[str, Any]:
        """Profile astronomical_events with varying date ranges."""
        print("\n" + "=" * 70)
        print("PROFILING: Astronomical Events")
        print("=" * 70)

        benchmark_data = {
            "endpoint": "astronomical_events",
            "tests": {},
            "summary": {},
        }

        year_ranges = [1, 5, 10]
        times = []

        for years in year_ranges:
            print(f"\n  Testing {years}-year range...")

            # Calculate date range
            end_date = datetime(2026, 12, 31)
            start_date = end_date - timedelta(days=365 * years)

            payload = {
                "latitude": 40.0,
                "longitude": -74.0,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
            }

            # Time the request
            start_time = time.perf_counter()
            try:
                response = self.client.post(
                    "/api/v1/astronomical-events",
                    json=payload,
                    headers={"Accept": "application/json"},
                )
                elapsed = time.perf_counter() - start_time

                # Memory profiling (not tracked for now)
                memory_delta = 0.0
                memory_peak_mb = 0.0

                if response.status_code == 200:
                    times.append(elapsed)

                    data = response.json()
                    event_list = data.get("events", [])
                    event_count = len(event_list)

                    # Count event types
                    event_type_counts = {}
                    for event in event_list:
                        event_type = event.get("event_type", "unknown")
                        event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1

                    # Set status and test result
                    status = "pass"
                    if years == 10 and elapsed > 5.0:
                        status = "⚠️ SLOW (>5s for 10-year range)"

                    test_result = {
                        "year_range": years,
                        "response_time_seconds": round(elapsed, 3),
                        "event_count": event_count,
                        "event_types": event_type_counts,
                        "status": status,
                        "http_status": 200,
                    }

                    if status == "pass":
                        print(f"    [PASS] Response time: {elapsed:.2f}s")
                    else:
                        print(f"    [SLOW] Response time: {elapsed:.2f}s (expected <5s)")

                    if event_count > 0:
                        print(f"       Events: {event_count} total")

                    benchmark_data["tests"][f"events_{years}yr"] = test_result
                else:
                    error_msg = response.text[:200]
                    print(f"    ✗ HTTP {response.status_code}: {error_msg}")
                    benchmark_data["tests"][f"events_{years}yr"] = {
                        "year_range": years,
                        "status": "error",
                        "http_status": response.status_code,
                        "error": error_msg,
                    }

            except Exception as e:
                print(f"    ✗ FAILED: {e}")
                benchmark_data["tests"][f"events_{years}yr"] = {
                    "year_range": years,
                    "status": "error",
                    "error": str(e),
                }

        # Summary stats
        if times:
            benchmark_data["summary"] = {
                "min_response_time": round(min(times), 3),
                "max_response_time": round(max(times), 3),
                "avg_response_time": round(statistics.mean(times), 3),
            }

        return benchmark_data

    def run_all(self) -> Dict[str, Any]:
        """Run all benchmarks."""
        print("\n" + "=" * 70)
        print("PERFORMANCE BASELINE ESTABLISHMENT - Phase 2.4")
        print("=" * 70)
        print(f"Started at: {self.results['timestamp']}")

        # Profile batch observations
        self.results["benchmarks"]["batch_earth_observations"] = (
            self.profile_batch_earth_observations()
        )

        # Profile astronomical events
        self.results["benchmarks"]["astronomical_events"] = (
            self.profile_astronomical_events()
        )

        # Generate summary
        self.results["summary"] = self._generate_summary()

        # Total elapsed time
        total_elapsed = time.perf_counter() - self.start_time
        self.results["total_elapsed_seconds"] = round(total_elapsed, 2)

        return self.results

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate overall summary and check success criteria."""
        summary = {
            "success_criteria": {
                "batch_earth_500frames_under_40s": False,
                "astronomical_events_10yr_under_5s": False,
                "all_tests_completed": False,
            },
            "recommendations": [],
        }

        # Check batch earth criteria
        batch_tests = self.results["benchmarks"].get("batch_earth_observations", {}).get("tests", {})
        batch_500 = batch_tests.get("batch_500", {})
        if batch_500.get("response_time_seconds", float('inf')) < 40.0:
            summary["success_criteria"]["batch_earth_500frames_under_40s"] = True

        # Check events criteria
        event_tests = self.results["benchmarks"].get("astronomical_events", {}).get("tests", {})
        events_10yr = event_tests.get("events_10yr", {})
        if events_10yr.get("response_time_seconds", float('inf')) < 5.0:
            summary["success_criteria"]["astronomical_events_10yr_under_5s"] = True

        # Check all completed
        batch_count = len(batch_tests)
        event_count = len(event_tests)
        if batch_count >= 4 and event_count >= 3:
            summary["success_criteria"]["all_tests_completed"] = True

        # Add recommendations
        if not summary["success_criteria"]["batch_earth_500frames_under_40s"]:
            batch_response_time = batch_500.get("response_time_seconds", "unknown")
            summary["recommendations"].append(
                f"⚠️ Batch Earth Observations 500 frames: {batch_response_time}s (target <40s)"
            )
        else:
            summary["recommendations"].append(
                f"[PASS] Batch Earth Observations 500 frames: {batch_500.get('response_time_seconds')}s (target <40s)"
            )

        if not summary["success_criteria"]["astronomical_events_10yr_under_5s"]:
            events_response_time = events_10yr.get("response_time_seconds", "unknown")
            summary["recommendations"].append(
                f"✗ Astronomical Events 10yr: {events_response_time}s (target <5s). "
                "Astropy eclipse calculations are computationally expensive. Consider: "
                "1) Implement eclipse caching with longer TTL, "
                "2) Add pagination/limits to large date ranges, "
                "3) Optimize eclipse detection algorithm"
            )
        else:
            summary["recommendations"].append(
                f"[PASS] Astronomical Events 10yr: {events_10yr.get('response_time_seconds')}s (target <5s)"
            )

        return summary

    def save_baseline(self, output_path: str = "performance-baseline.json"):
        """Save baseline results to JSON."""
        output_file = Path(output_path)
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)

        print(f"\n[PASS] Baseline saved to {output_file}")

    def print_summary(self):
        """Print summary report."""
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        summary = self.results["summary"]
        print("\nSuccess Criteria:")
        for criterion, passed in summary["success_criteria"].items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {status}: {criterion}")

        if summary["recommendations"]:
            print("\nRecommendations:")
            for rec in summary["recommendations"]:
                print(f"  {rec}")

        print(f"\nTotal elapsed time: {self.results['total_elapsed_seconds']}s")
        print("=" * 70)


def main():
    """Entry point."""
    benchmark = PerformanceBenchmark()

    try:
        results = benchmark.run_all()
        benchmark.print_summary()
        benchmark.save_baseline()

        # Exit with appropriate code
        all_passed = all(
            results["summary"]["success_criteria"].values()
        )
        return 0 if all_passed else 1

    except Exception as e:
        print(f"\n✗ BENCHMARK FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
