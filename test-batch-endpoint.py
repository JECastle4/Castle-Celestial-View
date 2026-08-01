#!/usr/bin/env python3
"""Test the batch-earth-observations endpoint with different frame counts"""

import requests
requests.packages.urllib3.disable_warnings()
session = requests.Session()

# Test frame_count=2 to confirm it works
print("Testing frame_count=2 (expected to work):")
try:
    r = session.post(
        'https://castlecelestialview.net/api/v1/batch-earth-observations',
        json={
            "start_date": "2026-08-01",
            "start_time": "00:00:00",
            "end_date": "2026-08-01",
            "end_time": "12:00:00",
            "frame_count": 2,
            "latitude": 0,
            "longitude": 0
        },
        verify=False,
        timeout=10
    )
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        print(f"✓ Request successful!")
        print(f"Response length: {len(r.text)} chars")
    else:
        print(f"✗ Failed with status {r.status_code}")
        print(f"Response: {r.text[:300]}")
except Exception as e:
    print(f"✗ Exception: {e}")

print("\nTesting frame_count=5:")
try:
    r = session.post(
        'https://castlecelestialview.net/api/v1/batch-earth-observations',
        json={
            "start_date": "2026-08-01",
            "start_time": "00:00:00",
            "end_date": "2026-08-01",
            "end_time": "12:00:00",
            "frame_count": 5,
            "latitude": 0,
            "longitude": 0
        },
        verify=False,
        timeout=10
    )
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        print(f"✓ Request successful!")
    else:
        print(f"✗ Failed with status {r.status_code}")
except Exception as e:
    print(f"✗ Exception: {str(e)[:100]}")
