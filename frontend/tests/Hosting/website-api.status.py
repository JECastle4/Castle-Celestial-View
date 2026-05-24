import requests

FRONTEND_URL = "http://castlecelestialview.net/en/index.html"
API_URL = (
    "http://castlecelestialview.net/api/v1/batch-earth-observations-stream?"
    "start_date=2026-05-24&start_time=00:00:00&end_date=2026-05-24&end_time=23:59:59&"
    "frame_count=48&latitude=51.5&longitude=-0.1&elevation=0&lang=en"
)

def check_frontend():
    try:
        resp = requests.get(FRONTEND_URL, timeout=10)
        print(f"Frontend status: {resp.status_code}")
        if resp.status_code == 200:
            print("Frontend is up.")
        else:
            print("Frontend returned non-200 status.")
    except Exception as e:
        print(f"Frontend check failed: {e}")

def check_api():
    try:
        resp = requests.get(API_URL, stream=True, timeout=10)
        print(f"API status: {resp.status_code}")
        if resp.status_code == 200:
            print("API is up.")
            # Print first event chunk (if streaming)
            for line in resp.iter_lines():
                if line:
                    print(f"API response sample: {line.decode()}")
                    break
        else:
            print("API returned non-200 status.")
    except Exception as e:
        print(f"API check failed: {e}")

if __name__ == "__main__":
    print("--- Checking Frontend ---")
    check_frontend()
    print("\n--- Checking API ---")
    check_api()
