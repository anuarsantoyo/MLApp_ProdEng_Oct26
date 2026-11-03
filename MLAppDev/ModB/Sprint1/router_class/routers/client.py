# Start one server first, then run:  python client.py
# Run it against app_v1 and against main: the five lines must come out identical.
import sys

import requests

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"
TIMEOUT = 10


def show(label, response):
    print(f"{label:<22} {response.status_code}  {response.text}")


show("GET /items/", requests.get(f"{BASE_URL}/items/", timeout=TIMEOUT))
show("GET /items/1", requests.get(f"{BASE_URL}/items/1", timeout=TIMEOUT))
show("GET /items/99", requests.get(f"{BASE_URL}/items/99", timeout=TIMEOUT))
show(
    "POST /items/",
    requests.post(
        f"{BASE_URL}/items/",
        json={"name": "monitor", "price": 150.0},
        timeout=TIMEOUT,
    ),
)
show("GET /health/", requests.get(f"{BASE_URL}/health/", timeout=TIMEOUT))
