"""MAX long-polling bot. One instance; TLS is verified using system/custom CA trust."""
import asyncio
import logging
import ssl
from pathlib import Path

import httpx

from .config import get_settings

log = logging.getLogger("arena.bot")


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
                params = {"timeout": 30, "limit": 100}
                if marker is not None:
                    params["marker"] = marker
                response = await client.get("/updates", params=params)
                response.raise_for_status()
                data = response.json()
                for update in data.get("updates", []):
                    kind = update.get("update_type")
                    message = update.get("message", {})
                    text = message.get("body", {}).get("text", "") or ""
                    if kind != "bot_started" and not (kind == "message_created" and text.strip().split(" ")[0] in ("/start", "/help")):
                        continue
                    user_id = update.get("user", {}).get("user_id") or message.get("sender", {}).get("user_id")
                    chat_id = update.get("chat_id") or message.get("recipient", {}).get("chat_id")
                    target = {"chat_id": chat_id} if chat_id else {"user_id": user_id}
                    if not chat_id and not user_id:
                        continue
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
                    await asyncio.sleep(0.05)
                marker = data.get("marker", marker)
                if marker is not None:
                    temp = marker_file.with_suffix(".tmp")
                    temp.write_text(str(marker))
                    temp.replace(marker_file)
            except (httpx.HTTPError, ValueError, OSError):
                log.exception("MAX polling failed; retry in 5 seconds (check token, CA and subscriptions)")
                await asyncio.sleep(5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
