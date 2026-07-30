"""Quick benchmark for batch earth observations API."""
import os
import requests
import time

# Use environment variable or default to localhost:8000
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_URL = f"{API_BASE_URL}/api/v1/batch-earth-observations"

def benchmark(name, frame_count, start_date, end_date):
    """Run a single benchmark test."""
    payload = {
        "start_date": start_date,
        "start_time": "00:00:00",
        "end_date": end_date,
        "end_time": "23:59:59",
        "frame_count": frame_count,
        "latitude": 52.0,
        "longitude": 0.0,
        "elevation": 0.0
    }
    
    start = time.perf_counter()
    response = requests.post(API_URL, json=payload, timeout=30)
    elapsed = time.perf_counter() - start
    
    if response.status_code == 200:
        data = response.json()
        frames = len(data["frames"])
        return {
            "name": name,
            "frames": frames,
            "elapsed": elapsed,
            "ms_per_frame": (elapsed / frames) * 1000,
            "fps": frames / elapsed
        }
    else:
        return None

# Check server
try:
    requests.get(f"{API_BASE_URL}/", timeout=5)
except Exception as e:
    print(f"ERROR: Server not running at {API_BASE_URL}")
    print(f"Please start the server with: uvicorn api.main:app --reload")
    print(f"Or set API_BASE_URL environment variable to point to your server")
    exit(1)

print("=" * 80)
print("BATCH API BENCHMARK - Optimized Version")
print("=" * 80)
print()

# Note: These dates are hardcoded for consistent benchmark results.
# The API handles any date (past, present, or future) for astronomical calculations,
# so these dates will remain valid test data regardless of when tests are run.
tests = [
    ("24 frames (1 day hourly)", 24, "2026-02-01", "2026-02-01"),
    ("48 frames (2 days hourly)", 48, "2026-02-01", "2026-02-02"),
    ("72 frames (3 days hourly)", 72, "2026-02-01", "2026-02-03"),
    ("168 frames (1 week hourly)", 169, "2026-02-01", "2026-02-08"),
]

results = []
for name, frames, start, end in tests:
    print(f"{name}...")
    result = benchmark(name, frames, start, end)
    if result:
        results.append(result)
        print(f"  {result['elapsed']:.2f}s total | {result['ms_per_frame']:.2f} ms/frame | {result['fps']:.1f} fps")
    else:
        print(f"  FAILED")
    print()

print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"{'Test':<35} {'Frames':>7} {'Total':>9} {'ms/frame':>10}")
print("-" * 80)
for r in results:
    print(f"{r['name']:<35} {r['frames']:>7} {r['elapsed']:>8.2f}s {r['ms_per_frame']:>9.2f}")

print()
print(f"Average: {sum(r['ms_per_frame'] for r in results)/len(results):.2f} ms/frame")
print(f"Best: {min(r['ms_per_frame'] for r in results):.2f} ms/frame ({max(r['fps'] for r in results):.1f} fps)")
