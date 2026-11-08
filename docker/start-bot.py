"""Start exactly one polling bot once the local API is ready."""

import os
import sys
import time
import urllib.error
import urllib.request


def main():
    # The bot itself logs that it is disabled and waits when no token is set.
    if os.environ.get("BOT_TOKEN"):
        print("Waiting for the API before starting the bot...", flush=True)
        while True:
            try:
                with urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=3) as response:
                    if response.status == 200:
                        break
            except (urllib.error.URLError, TimeoutError, OSError):
                pass
            time.sleep(1)
    os.execv(sys.executable, [sys.executable, "-m", "app.bot"])


if __name__ == "__main__":
    main()
