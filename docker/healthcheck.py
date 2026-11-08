"""Check both the frontend and API through the public Nginx listener."""

import json
import urllib.request


def main():
    with urllib.request.urlopen("http://127.0.0.1:8080/", timeout=2) as response:
        if response.status != 200 or b'<div id="app">' not in response.read():
            raise SystemExit("Frontend is not ready")
    with urllib.request.urlopen("http://127.0.0.1:8080/api/health", timeout=2) as response:
        if response.status != 200 or json.load(response).get("status") != "ok":
            raise SystemExit("API is not ready")


if __name__ == "__main__":
    main()
