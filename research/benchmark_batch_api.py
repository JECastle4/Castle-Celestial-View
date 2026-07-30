"""
Benchmark script for the batch earth observations API.
Tests performance with various time spans and frame counts.
"""
import os
import requests
import time

# Use environment variable or default to localhost:8000
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_URL = f"{API_BASE_URL}/api/v1/batch-earth-observations"

def benchmark_batch_request(start_date, start_time, end_date, end_time, frame_count, latitude, longitude, elevation=0.0):
    """
    Send a batch request and measure response time.
    
    Returns:
        tuple: (response_time_seconds, response_data, success)
    """
    payload = {
        "start_date": start_date,
        "start_time": start_time,
        "end_date": end_date,
        "end_time": end_time,
        "frame_count": frame_count,
        "latitude": latitude,
        "longitude": longitude,
        "elevation": elevation
    }
    
    start = time.perf_counter()
    try:
        response = requests.post(API_URL, json=payload, timeout=30)
        elapsed = time.perf_counter() - start
        
        if response.status_code == 200:
            return elapsed, response.json(), True
        else:
            return elapsed, response.text, False
    except Exception as e:
        elapsed = time.perf_counter() - start
        return elapsed, str(e), False


def run_benchmarks():
    """Run various benchmark scenarios."""
    
    print("=" * 80)
    print("BATCH EARTH OBSERVATIONS API BENCHMARK")
    print("=" * 80)
    print()
    
    # Test location: London
    lat, lon = 52.0, 0.0
    
    # Note: These dates are hardcoded for consistent benchmark results.
    # The API handles any date (past, present, or future) for astronomical calculations,
    # so these dates will remain valid test data regardless of when tests are run.
    test_cases = [
        {
            "name": "1 day, hourly (24 frames)",
            "start_date": "2026-02-01",
            "start_time": "00:00:00",
            "end_date": "2026-02-01",
            "end_time": "23:59:59",
            "frame_count": 24
        },
        {
            "name": "1 week, hourly (168 frames)",
            "start_date": "2026-02-01",
            "start_time": "00:00:00",
            "end_date": "2026-02-08",
            "end_time": "00:00:00",
            "frame_count": 169
        },
        {
            "name": "1 week, every 30 minutes (336 frames)",
            "start_date": "2026-02-01",
            "start_time": "00:00:00",
            "end_date": "2026-02-08",
            "end_time": "00:00:00",
            "frame_count": 337
        },
        {
            "name": "1 month, daily (31 frames)",
            "start_date": "2026-02-01",
            "start_time": "12:00:00",
            "end_date": "2026-03-03",
            "end_time": "12:00:00",
            "frame_count": 31
        },
        {
            "name": "1 hour, every minute (60 frames)",
            "start_date": "2026-02-01",
            "start_time": "12:00:00",
            "end_date": "2026-02-01",
            "end_time": "13:00:00",
            "frame_count": 61
        },
        {
            "name": "1 day, every 5 minutes (288 frames)",
            "start_date": "2026-02-01",
            "start_time": "00:00:00",
            "end_date": "2026-02-01",
            "end_time": "23:59:59",
            "frame_count": 289
        },
    ]
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}/{len(test_cases)}: {test['name']}")
        print("-" * 80)
        
        elapsed, data, success = benchmark_batch_request(
            test["start_date"],
            test["start_time"],
            test["end_date"],
            test["end_time"],
            test["frame_count"],
            lat,
            lon
        )
        
        if success:
            frames = len(data.get("frames", []))
            time_span_hours = data["metadata"]["time_span_hours"]
            
            print(f"  [SUCCESS]")
            print(f"  Response time: {elapsed:.3f} seconds")
            print(f"  Frames received: {frames}")
            print(f"  Time span: {time_span_hours:.2f} hours")
            print(f"  Time per frame: {elapsed/frames*1000:.2f} ms")
            print(f"  Frames per second: {frames/elapsed:.2f}")
            
            results.append({
                "name": test["name"],
                "frame_count": frames,
                "elapsed": elapsed,
                "time_per_frame": elapsed/frames,
                "frames_per_second": frames/elapsed,
                "success": True
            })
        else:
            print(f"  [FAILED]: {data}")
            results.append({
                "name": test["name"],
                "frame_count": test["frame_count"],
                "elapsed": elapsed,
                "error": data,
                "success": False
            })
        
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    
    successful = [r for r in results if r["success"]]
    if successful:
        print(f"{'Test Name':<40} {'Frames':>8} {'Time':>10} {'ms/frame':>10}")
        print("-" * 80)
        for r in successful:
            print(f"{r['name']:<40} {r['frame_count']:>8} {r['elapsed']:>9.3f}s {r['time_per_frame']*1000:>9.2f}")
        
        print()
        print(f"Average time per frame: {sum(r['time_per_frame'] for r in successful)/len(successful)*1000:.2f} ms")
        print(f"Fastest: {min(r['time_per_frame'] for r in successful)*1000:.2f} ms/frame")
        print(f"Slowest: {max(r['time_per_frame'] for r in successful)*1000:.2f} ms/frame")
    else:
        print("No successful tests!")
    
    failed = [r for r in results if not r["success"]]
    if failed:
        print()
        print(f"Failed tests: {len(failed)}")
        for r in failed:
            print(f"  - {r['name']}: {r.get('error', 'Unknown error')}")


if __name__ == "__main__":
    # Check if server is running
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        print(f"Server is running at {API_BASE_URL}: {response.json()}")
        print()
    except Exception as e:
        print(f"ERROR: Server not running at {API_BASE_URL}")
        print(f"Please start the server with: uvicorn api.main:app --reload")
        print(f"Or set API_BASE_URL environment variable to point to your server")
        exit(1)
    
    run_benchmarks()
