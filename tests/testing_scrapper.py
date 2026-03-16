import json
import sys
from typing import Any

import requests


TEST_URL = "https://nk-scraper.grayriver-ffcf7337.westus.azurecontainerapps.io/api/company/tracxn"
TEST_PAYLOAD = {"companyDomain": "namekart.com"}
TIMEOUT_SECONDS = 100


def pretty_print_response(resp: requests.Response) -> None:
    """Print the response status and JSON (if available)."""
    print(f"Status: {resp.status_code}")
    print("Headers:")
    for key, value in resp.headers.items():
        print(f"  {key}: {value}")

    print("\nBody:")
    try:
        parsed: Any = resp.json()
        print(json.dumps(parsed, indent=2)) 
    except requests.JSONDecodeError:
        print(resp.text)


def main() -> int:
    try:
        response = requests.post(TEST_URL, json=TEST_PAYLOAD, timeout=TIMEOUT_SECONDS)
        pretty_print_response(response)
        return 0
    except requests.RequestException as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())