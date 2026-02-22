"""
Traffic generator. Sends a mix of requests:
  70% /fast — normal traffic
  10% /slow — heavy queries
  20% /flaky — the one that causes problems

Run it. Open Grafana. Watch the SLOs change.
"""
import httpx
import random
import time
import sys

BASE_URL = "http://localhost:8000"

# Weighted endpoint distribution. Adjust these to simulate different scenarios.
# Want to see your SLO recover? Drop /flaky to 0.
# Want to see it burn? Crank /flaky to 0.5.
ENDPOINTS = [
    ("/fast",  0.70),
    ("/slow",  0.10),
    ("/flaky", 0.20),
]


def pick_endpoint():
    r = random.random()
    cumulative = 0
    for endpoint, weight in ENDPOINTS:
        cumulative += weight
        if r <= cumulative:
            return endpoint
    return ENDPOINTS[0][0]


def main():
    rps = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
    print(f"~{rps} req/s. Ctrl+C to stop.")

    with httpx.Client(timeout=10) as client:
        count = 0
        while True:
            endpoint = pick_endpoint()
            try:
                resp = client.get(f"{BASE_URL}{endpoint}")
                status = "✓" if resp.status_code == 200 else f"✗ {resp.status_code}"
            except Exception as e:
                status = f"✗ {e}"

            count += 1
            if count % 20 == 0:
                print(f"  {count} sent")

            time.sleep(1.0 / rps)


if __name__ == "__main__":
    main()