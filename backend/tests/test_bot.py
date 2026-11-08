import json
import ssl

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
    {"update_type": "message_created", "message": {"body": {"text": "/identity"}}},
    {"update_type": "message_created", "message": {
        "sender": {"user_id": 42}, "recipient": {"chat_type": "dialog"}, "body": {"text": "/id"},
    }},
    {"update_type": "message_edited", "message": {"body": {"text": "/id"}}},
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


async def test_polling_preflight_checks_identity_and_subscriptions():
    paths = []

    def handler(request):
        paths.append(request.url.path)
        if request.url.path == "/me":
            return httpx.Response(200, json={"user_id": 99, "username": "arena_test_bot"})
        return httpx.Response(200, json={"subscriptions": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://max.test") as client:
        identity = await bot.check_polling(client)
    assert identity["user_id"] == 99
    assert paths == ["/me", "/subscriptions"]


async def test_polling_preflight_detects_webhook_without_deleting_it():
    def handler(request):
        assert request.method == "GET"
        if request.url.path == "/me":
            return httpx.Response(200, json={"user_id": 99})
        assert request.url.path == "/subscriptions"
        return httpx.Response(200, json={"subscriptions": [{"url": "https://private.example/webhook"}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://max.test") as client:
        with pytest.raises(bot.PollingConflictError, match="webhook subscription is active") as exc:
            await bot.check_polling(client)
    assert "private.example" not in str(exc.value)


async def test_polling_preflight_stops_on_invalid_token():
    def handler(request):
        assert request.url.path == "/me"
        return httpx.Response(401, json={"code": "unauthorized"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://max.test") as client:
        with pytest.raises(httpx.HTTPStatusError):
            await bot.check_polling(client)


@pytest.mark.parametrize(("error", "summary"), [
    (httpx.ConnectTimeout("private proxy details"), "connection/TLS handshake timed out"),
    (httpx.ReadTimeout("private proxy details"), "response timed out after connecting"),
    (httpx.ConnectError("private proxy details"), "ConnectError"),
])
def test_network_failure_summary_does_not_expose_exception_details(error, summary):
    assert summary in bot.request_failure(error)
    assert "private proxy details" not in bot.request_failure(error)


def test_certificate_failure_is_not_reported_as_network_timeout():
    error = httpx.ConnectError("private proxy details")
    error.__cause__ = ssl.SSLCertVerificationError(1, "certificate verify failed")
    assert "TLS certificate verification failed" in bot.request_failure(error)


def test_api_client_keeps_tls_verification_and_separate_connect_timeout(bot_settings):
    client = bot.api_client(bot_settings)
    assert client.timeout.connect == 10
    assert client.timeout.read == 45
    context = bot.tls_context(bot_settings)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname


def test_bundled_ca_is_used_when_no_explicit_bundle(bot_settings, monkeypatch):
    from pathlib import Path
    bundle = Path(__file__).resolve().parents[2] / "docker/certs/russian-trusted-root-ca.crt"
    monkeypatch.setattr(bot, "BUNDLED_CA", bundle)
    bot_settings.max_ca_bundle = ""
    assert bot.ca_bundle(bot_settings) == str(bundle)
    context = bot.tls_context(bot_settings)
    import hashlib
    expected = "d26d2d0231b7c39f92cc738512ba54103519e4405d68b5bd703e9788ca8ecf31"
    assert hashlib.sha256(ssl.PEM_cert_to_DER_cert(bundle.read_text())).hexdigest() == expected
    assert any(hashlib.sha256(cert).hexdigest() == expected for cert in context.get_ca_certs(binary_form=True))
    assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname


def test_explicit_ca_takes_precedence(bot_settings, monkeypatch, tmp_path):
    bundle = tmp_path / "bundled.pem"
    bundle.touch()
    monkeypatch.setattr(bot, "BUNDLED_CA", bundle)
    bot_settings.max_ca_bundle = "/certs/custom.pem"
    assert bot.ca_bundle(bot_settings) == "/certs/custom.pem"


def test_host_install_uses_system_trust_without_bundled_ca(bot_settings, monkeypatch, tmp_path):
    monkeypatch.setattr(bot, "BUNDLED_CA", tmp_path / "missing.pem")
    bot_settings.max_ca_bundle = ""
    assert bot.ca_bundle(bot_settings) == ""
    assert bot.tls_context(bot_settings).verify_mode == ssl.CERT_REQUIRED


async def test_start_command_gets_greeting(bot_settings, caplog):
    def handler(request):
        assert request.url.path == "/messages"
        assert request.url.params["user_id"] == "42"
        return httpx.Response(200, json={})

    with caplog.at_level("INFO", logger="arena.bot"):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://max.test") as client:
            await bot.handle_update(client, bot_settings, {
                "update_type": "message_created", "message": {
                    "sender": {"user_id": 42}, "recipient": {"chat_type": "dialog"},
                    "body": {"text": "/start"},
                },
            })
    assert "MAX greeting sent successfully for message_created" in caplog.text
