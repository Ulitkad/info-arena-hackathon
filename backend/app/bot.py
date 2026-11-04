"""MAX long-polling bot. One instance; TLS is verified using system/custom CA trust."""
import asyncio
import logging
import ssl
from pathlib import Path

import httpx

from .config import Settings, get_settings

log = logging.getLogger("arena.bot")


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
    await asyncio.sleep(0.5)


async def poll_once(client: httpx.AsyncClient, settings: Settings, marker: int | None, marker_file: Path):
    params = {"timeout": 30, "limit": 100}
    if marker is not None:
        params["marker"] = marker
    response = await client.get("/updates", params=params)
    response.raise_for_status()
    data = response.json()
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
    tls = ssl.create_default_context()
    if settings.max_ca_bundle:
        tls.load_verify_locations(settings.max_ca_bundle)
    marker_file = Path("/data/bot-marker") if Path("/data").exists() else Path("data/bot-marker")
    marker_file.parent.mkdir(parents=True, exist_ok=True)
    marker = int(marker_file.read_text()) if marker_file.exists() else None
    async with httpx.AsyncClient(base_url=settings.bot_api_url, headers={"Authorization": settings.bot_token},
                                  verify=tls, timeout=45) as client:
        while True:
            try:
                marker = await poll_once(client, settings, marker, marker_file)
                await asyncio.sleep(0.3)
            except httpx.HTTPStatusError as exc:
                log.error("MAX %s %s failed: HTTP %s %s; retry in 5 seconds",
                          exc.request.method, exc.request.url.path, exc.response.status_code, api_error(exc.response))
                await asyncio.sleep(5)
            except httpx.ConnectTimeout:
                log.warning("MAX connection/TLS handshake timed out; check server egress/proxy/network; retry in 5 seconds")
                await asyncio.sleep(5)
            except (httpx.RequestError, ValueError, OSError):
                log.exception("MAX update cycle failed; retry in 5 seconds")
                await asyncio.sleep(5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
