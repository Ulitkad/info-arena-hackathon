import json

import httpx
import pytest

from app import bot
from app.config import Settings


@pytest.fixture
def bot_settings(monkeypatch):
    async def no_sleep(_):
        pass

    monkeypatch.setattr(bot.asyncio, "sleep", no_sleep)
    return Settings(_env_file=None, secret_key="test-secret-key-for-arena-only-000000000000",
                    bot_username="arena_test_bot", base_app_url="https://arena.example.com")


@pytest.mark.parametrize(("update", "target"), [
    ({"update_type": "bot_started", "chat_id": 234503008, "user": {"user_id": 42}}, {"user_id": 42}),
    ({"update_type": "message_created", "message": {
        "sender": {"user_id": 42},
        "recipient": {"chat_type": "dialog", "chat_id": 234503008, "user_id": 99},
    }}, {"user_id": 42}),
    ({"update_type": "message_created", "message": {
        "sender": {"user_id": 42}, "recipient": {"chat_type": "chat", "chat_id": -123},
    }}, {"chat_id": -123}),
    ({"update_type": "bot_started", "chat_id": 234503008, "user": None}, {}),
    ({"update_type": "message_created", "message": {"sender": None, "recipient": None}}, {}),
])
def test_reply_target(update, target):
    assert bot.reply_target(update) == target


async def test_reply_preserves_app_button_and_payload(bot_settings):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://max.test") as client:
        await bot.handle_update(client, bot_settings, {
            "update_type": "bot_started", "chat_id": 234503008,
            "user": {"user_id": 42}, "payload": "invite-token",
        })
    assert dict(requests[0].url.params) == {"user_id": "42"}
    button = json.loads(requests[0].content)["attachments"][0]["payload"]["buttons"][0][0]
    assert button == {"type": "open_app", "text": "Открыть арену",
                      "web_app": "arena_test_bot", "payload": "invite-token"}


async def test_reply_without_username_uses_link(bot_settings):
    bot_settings.bot_username = ""

    def handler(request):
        button = json.loads(request.content)["attachments"][0]["payload"]["buttons"][0][0]
        assert button == {"type": "link", "text": "Открыть арену", "url": bot_settings.base_app_url}
        return httpx.Response(200, json={})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://max.test") as client:
        await bot.handle_update(client, bot_settings, {
            "update_type": "message_created", "message": {
                "sender": {"user_id": 42}, "recipient": {"chat_type": "dialog"},
                "body": {"text": "/help"},
            },
        })


async def test_permanent_send_error_does_not_block_marker_or_later_updates(bot_settings, tmp_path, caplog):
    marker_file = tmp_path / "bot-marker"
    marker_file.write_text("121199")
    sent = []
    polls = []

    def handler(request):
        if request.url.path == "/updates":
            polls.append(dict(request.url.params))
            if len(polls) > 1:
                return httpx.Response(200, json={"updates": [], "marker": 121201})
            return httpx.Response(200, json={"marker": 121200, "updates": [
                {"update_type": "bot_started", "user": {"user_id": 42}},
                {"update_type": "bot_started", "user": {"user_id": 43}},
            ]})
        sent.append(request.url.params["user_id"])
        if len(sent) == 1:
            return httpx.Response(404, json={"code": "test.not.found", "message": "Test recipient not found"})
        return httpx.Response(200, json={})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://max.test") as client:
        marker = await bot.poll_once(client, bot_settings, 121199, marker_file)
        assert marker == 121200
        assert marker_file.read_text() == "121200"
        await bot.poll_once(client, bot_settings, marker, marker_file)
    assert sent == ["42", "43"]
    assert polls[1]["marker"] == "121200"
    assert "HTTP 404 code=test.not.found message=Test recipient not found" in caplog.text


@pytest.mark.parametrize("status", [401, 408, 429, 500, 503])
async def test_retryable_send_error_preserves_marker(bot_settings, tmp_path, status):
    marker_file = tmp_path / "bot-marker"
    marker_file.write_text("100")

    def handler(request):
        if request.url.path == "/updates":
            return httpx.Response(200, json={"marker": 101, "updates": [
                {"update_type": "bot_started", "user": {"user_id": 42}},
            ]})
        return httpx.Response(status, json={"code": "test.error", "message": "Test error"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://max.test") as client:
        with pytest.raises(httpx.HTTPStatusError):
            await bot.poll_once(client, bot_settings, 100, marker_file)
    assert marker_file.read_text() == "100"


async def test_connection_timeout_preserves_marker(bot_settings, tmp_path):
    marker_file = tmp_path / "bot-marker"
    marker_file.write_text("100")

    def handler(request):
        raise httpx.ConnectTimeout("TLS handshake timed out", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://max.test") as client:
        with pytest.raises(httpx.ConnectTimeout):
            await bot.poll_once(client, bot_settings, 100, marker_file)
    assert marker_file.read_text() == "100"


@pytest.mark.parametrize("update", [
    {"update_type": "message_created", "message": {"body": None}},
    {"update_type": "message_created", "message": {"body": {"text": "hello"}}},
    {"update_type": "message_callback", "message": None},
])
async def test_unhandled_updates_are_ignored(bot_settings, update):
    def handler(request):
        pytest.fail("No message should be sent")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://max.test") as client:
        await bot.handle_update(client, bot_settings, update)


def test_error_summary_handles_non_json():
    assert bot.api_error(httpx.Response(502, text="<html>Bad gateway</html>")) == "non-JSON error response"
    assert bot.api_error(httpx.Response(502, json=[])) == "unexpected error response"
