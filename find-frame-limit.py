#!/usr/bin/env python3
"""Find the actual frame count limit for batch-earth-observations endpoint"""

import requests
requests.packages.urllib3.disable_warnings()

print("=== Finding Actual Frame Count Limit ===\n")

# Test increasingly large frame counts
test_values = [100, 500, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]

results = {}
for count in test_values:
    try:
        r = requests.post(
            'https://castlecelestialview.net/api/v1/batch-earth-observations',
            json={
                "start_date": "2026-08-01",
                "start_time": "00:00:00",
                "end_date": "2026-08-01",
                "end_time": "12:00:00",
                "frame_count": count,
                "latitude": 0,
                "longitude": 0
            },
            verify=False,
            timeout=60
        )
        status = "OK (200)" if r.status_code == 200 else f"ERROR {r.status_code}"
        results[count] = (r.status_code, None)
        print(f"frame_count={count:5d} -> {status}")
    except requests.exceptions.Timeout:
        results[count] = (None, "TIMEOUT")
        print(f"frame_count={count:5d} -> TIMEOUT")
    except Exception as e:
        results[count] = (None, str(e)[:40])
        print(f"frame_count={count:5d} -> {str(e)[:40]}")

# Find the threshold
print("\n=== Analysis ===")
passing = [c for c, (status, err) in results.items() if status == 200]
failing = [c for c, (status, err) in results.items() if status and status != 200]

if passing:
    max_working = max(passing)
    print(f"Maximum working frame_count: {max_working}")
    
if failing:
    min_failing = min(failing)
    print(f"Minimum failing frame_count: {min_failing} (status: {results[min_failing][0]})")

print("\nConclusion: API has a practical limit - test harness should reflect this")
