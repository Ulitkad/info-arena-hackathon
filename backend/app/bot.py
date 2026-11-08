"""MAX long-polling bot. One instance; TLS is verified using system/custom CA trust."""
import asyncio
import logging
import ssl
from pathlib import Path

import httpx

from .config import Settings, get_settings

log = logging.getLogger("arena.bot")
BUNDLED_CA = Path("/opt/arena/russian-trusted-root-ca.crt")


class PollingConflictError(RuntimeError):
    """A webhook is configured; never silently remove someone else's subscription."""


def ca_bundle(settings: Settings) -> str:
    return settings.max_ca_bundle or (str(BUNDLED_CA) if BUNDLED_CA.is_file() else "")


def tls_context(settings: Settings) -> ssl.SSLContext:
    context = ssl.create_default_context()
    bundle = ca_bundle(settings)
    if bundle:
        context.load_verify_locations(bundle)
    return context


def api_client(settings: Settings) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.bot_api_url,
        headers={"Authorization": settings.bot_token},
        verify=tls_context(settings),
        # A long poll can wait 30 seconds, but connection setup should fail faster.
        timeout=httpx.Timeout(45, connect=10),
    )


async def check_polling(client: httpx.AsyncClient) -> dict:
    response = await client.get("/me")
    response.raise_for_status()
    identity = response.json()
    response = await client.get("/subscriptions")
    response.raise_for_status()
    if response.json().get("subscriptions"):
        raise PollingConflictError(
            "MAX webhook subscription is active: long polling cannot receive updates. "
            "Remove the subscription only if this bot should use polling; nothing was changed automatically."
        )
    return identity


def request_failure(exc: httpx.RequestError) -> str:
    """Explain errors without printing headers, proxy credentials or event payloads."""
    cause = exc
    while cause is not None:
        if isinstance(cause, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(cause):
            return "TLS certificate verification failed; check MAX_CA_BUNDLE and the trusted root CA"
        cause = cause.__cause__
    if isinstance(exc, httpx.ConnectTimeout):
        return "connection/TLS handshake timed out; check outbound TCP/443, routing, DNS and proxy settings"
    if isinstance(exc, httpx.ReadTimeout):
        return "response timed out after connecting; check MAX availability and network/proxy timeouts"
    return f"{type(exc).__name__}; check DNS, outbound connectivity and proxy settings"


def reply_target(update: dict) -> dict:
    message = update.get("message") or {}
    recipient = message.get("recipient") or {}
    user_id = (update.get("user") or {}).get("user_id") or (message.get("sender") or {}).get("user_id")
    # A dialog's recipient.user_id is the bot, not the user we are replying to.
    if update.get("update_type") == "bot_started" or recipient.get("chat_type") == "dialog":
        return {"user_id": user_id} if user_id else {}
    chat_id = update.get("chat_id") or recipient.get("chat_id")
    if chat_id:
        return {"chat_id": chat_id}
    return {"user_id": user_id} if user_id else {}


def api_error(response: httpx.Response) -> str:
    try:
        error = response.json()
    except ValueError:
        return "non-JSON error response"
    if not isinstance(error, dict):
        return "unexpected error response"
    return f"code={error.get('code', '?')} message={error.get('message', '?')}"[:1000]


async def handle_update(client: httpx.AsyncClient, settings: Settings, update: dict):
    kind = update.get("update_type")
    message = update.get("message") or {}
    text = (message.get("body") or {}).get("text") or ""
    if kind != "bot_started" and not (kind == "message_created" and text.strip().split(" ")[0] in ("/start", "/help")):
        return
    target = reply_target(update)
    if not target:
        return
    button = {"type": "open_app", "text": "Открыть арену", "web_app": settings.bot_username}
    if not settings.bot_username:
        button = {"type": "link", "text": "Открыть арену", "url": settings.base_app_url}
    payload = update.get("payload")
    if payload and button["type"] == "open_app":
        button["payload"] = str(payload)[:512]
    reply = await client.post("/messages", params=target, json={
        "text": "Добро пожаловать в Инфо Арену! ☁️\n\nВыполняй задания, открывай награды и соревнуйся с друзьями. Твой следующий уровень начинается здесь.",
        "attachments": [{"type": "inline_keyboard", "payload": {"buttons": [[button]]}}],
    })
    reply.raise_for_status()
    log.info("MAX greeting sent successfully for %s", kind)
    await asyncio.sleep(0.5)


async def poll_once(client: httpx.AsyncClient, settings: Settings, marker: int | None, marker_file: Path):
    params = {"timeout": 30, "limit": 100}
    if marker is not None:
        params["marker"] = marker
    response = await client.get("/updates", params=params)
    response.raise_for_status()
    data = response.json()
    if data.get("updates"):
        log.info("MAX received %d updates", len(data["updates"]))
    for update in data.get("updates", []):
        try:
            await handle_update(client, settings, update)
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            # Retrying an invalid/unavailable recipient must not block all later updates.
            # Auth, rate limits and transient failures still retry without advancing the marker.
            if not (400 <= status < 500) or status in (401, 408, 429):
                raise
            log.error("MAX send failed for %s target=%s: HTTP %s %s; skipping update",
                      update.get("update_type"), reply_target(update), status, api_error(exc.response))
    marker = data.get("marker", marker)
    if marker is not None:
        temp = marker_file.with_suffix(".tmp")
        temp.write_text(str(marker))
        temp.replace(marker_file)
    return marker


async def run():
    settings = get_settings()
    if not settings.bot_token:
        log.warning("BOT_TOKEN is empty; bot is disabled")
        await asyncio.Event().wait()
        return
    marker_file = Path("/data/bot-marker") if Path("/data").exists() else Path("data/bot-marker")
    marker_file.parent.mkdir(parents=True, exist_ok=True)
    marker = int(marker_file.read_text()) if marker_file.exists() else None
    log.info("MAX bot starting; additional_ca=%s; checking token and webhook subscriptions", bool(ca_bundle(settings)))
    async with api_client(settings) as client:
        checked = False
        connected = False
        while True:
            try:
                if not checked:
                    identity = await check_polling(client)
                    log.info("MAX token accepted for bot_id=%s; no webhooks; starting long polling", identity.get("user_id"))
                    checked = True
                marker = await poll_once(client, settings, marker, marker_file)
                if not connected:
                    log.info("MAX long polling connected successfully; waiting for Start or /start")
                    connected = True
                await asyncio.sleep(0.3)
            except PollingConflictError as exc:
                log.error("%s Retrying checks in 60 seconds.", exc)
                await asyncio.sleep(60)
            except httpx.HTTPStatusError as exc:
                connected = False
                checked = False
                log.error("MAX %s %s failed: HTTP %s %s; retry in 5 seconds",
                          exc.request.method, exc.request.url.path, exc.response.status_code, api_error(exc.response))
                await asyncio.sleep(5)
            except httpx.RequestError as exc:
                connected = False
                log.warning("MAX %s %s: %s; retry in 5 seconds",
                            exc.request.method, exc.request.url.path, request_failure(exc))
                await asyncio.sleep(5)
            except (ValueError, OSError):
                log.exception("MAX update cycle failed; retry in 5 seconds")
                await asyncio.sleep(5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
