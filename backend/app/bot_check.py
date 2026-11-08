"""Read-only MAX diagnostics: never polls updates, sends messages or removes webhooks.

Run in the deployed container: docker compose exec app python -m app.bot_check
"""

import asyncio
import os
import socket
import ssl
from urllib.parse import urlsplit

import httpx

from .bot import PollingConflictError, api_client, ca_bundle, check_polling, request_failure, tls_context
from .config import get_settings


async def diagnose() -> int:
    settings = get_settings()
    if not settings.bot_token:
        print("FAIL: BOT_TOKEN is empty; bot is disabled")
        return 1
    url = urlsplit(settings.bot_api_url)
    host = url.hostname
    port = url.port or 443
    if url.scheme != "https" or not host:
        print("FAIL: BOT_API_URL must be an HTTPS URL")
        return 1
    print(f"MAX endpoint: {host}:{port}; token is set (not displayed)")
    proxy_names = [name for name in ("HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy", "NO_PROXY", "no_proxy")
                   if os.environ.get(name)]
    print("Proxy environment variables: " + (", ".join(proxy_names) or "none"))
    try:
        context = tls_context(settings)
    except (OSError, ssl.SSLError, ValueError) as exc:
        print(f"FAIL: custom CA cannot be loaded ({type(exc).__name__}); check MAX_CA_BUNDLE and its mount")
        return 1
    source = "custom" if settings.max_ca_bundle else "bundled" if ca_bundle(settings) else "none"
    print(f"CA: system trust + additional bundle={source}; verification enabled")

    # Direct probes isolate DNS, TCP and TLS. HTTP below still uses the bot's
    # normal proxy settings, so a direct probe failure alone is not definitive.
    try:
        addresses = await asyncio.wait_for(
            asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM), timeout=10,
        )
        print("DNS: " + ", ".join(dict.fromkeys(item[4][0] for item in addresses)))
    except (OSError, TimeoutError) as exc:
        print(f"Direct DNS FAIL: {type(exc).__name__}")
    else:
        for label, options in (("TCP", {}), ("TLS", {"ssl": context, "server_hostname": host})):
            try:
                _, writer = await asyncio.wait_for(asyncio.open_connection(host, port, **options), timeout=10)
                writer.close()
                try:
                    await asyncio.wait_for(writer.wait_closed(), timeout=2)
                except (OSError, TimeoutError):
                    pass
                print(f"Direct {label}: OK")
            except ssl.SSLCertVerificationError:
                print("Direct TLS FAIL: certificate verification failed; check trusted root CA")
            except (OSError, TimeoutError) as exc:
                print(f"Direct {label} FAIL: {type(exc).__name__}")

    print("Checking /me and /subscriptions using the bot's HTTP client (no /updates request)...")
    try:
        async with api_client(settings) as client:
            identity = await check_polling(client)
        print(f"OK: token accepted; bot_id={identity.get('user_id')}; username={identity.get('username')}")
        print("OK: no webhook subscriptions. Polling is allowed.")
        print("If Start still receives no reply, check bot logs and stop any other polling instance with this token.")
        return 0
    except PollingConflictError:
        print("FAIL: token accepted, but a webhook subscription is active; it conflicts with polling.")
        print("No subscriptions were removed. Decide which deployment should receive this bot's events.")
    except httpx.HTTPStatusError as exc:
        print(f"FAIL: {exc.request.url.path} returned HTTP {exc.response.status_code}")
        if exc.response.status_code == 401:
            print("Check/rotate BOT_TOKEN and recreate the container; restarting does not reload .env.")
    except httpx.RequestError as exc:
        print(f"FAIL: {exc.request.url.path}: {request_failure(exc)}")
    except ValueError:
        print("FAIL: MAX returned an invalid JSON response")
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(diagnose()))
