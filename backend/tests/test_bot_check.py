import ssl
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from app import bot_check
from app.config import Settings


def settings():
    return Settings(_env_file=None, secret_key="test-secret-key-for-arena-only-000000000000",
                    bot_token="private-test-token")


async def test_diagnostics_exits_if_bot_is_disabled(monkeypatch, capsys):
    config = settings()
    config.bot_token = ""
    monkeypatch.setattr(bot_check, "get_settings", lambda: config)
    assert await bot_check.diagnose() == 1
    assert "BOT_TOKEN is empty" in capsys.readouterr().out


async def test_diagnostics_reports_bad_ca_without_exposing_exception(monkeypatch, capsys):
    monkeypatch.setattr(bot_check, "get_settings", settings)
    monkeypatch.setattr(bot_check, "tls_context", Mock(side_effect=ssl.SSLError("private details")))
    assert await bot_check.diagnose() == 1
    output = capsys.readouterr().out
    assert "custom CA cannot be loaded" in output
    assert "private details" not in output
    assert "private-test-token" not in output


@pytest.mark.parametrize(("failure", "expected"), [
    (bot_check.PollingConflictError("private webhook"), "webhook subscription is active"),
    (httpx.ConnectTimeout("private proxy", request=httpx.Request("GET", "https://max.test/me")),
     "connection/TLS handshake timed out"),
    (httpx.HTTPStatusError("private details", request=httpx.Request("GET", "https://max.test/me"),
                           response=httpx.Response(401)), "returned HTTP 401"),
])
async def test_diagnostics_reports_api_failure_without_exposing_secrets(monkeypatch, capsys, failure, expected):
    monkeypatch.setattr(bot_check, "get_settings", settings)
    monkeypatch.setattr(bot_check.asyncio.get_running_loop(), "getaddrinfo", AsyncMock(side_effect=OSError))
    monkeypatch.setattr(bot_check, "check_polling", AsyncMock(side_effect=failure))
    monkeypatch.setattr(bot_check, "api_client", lambda _: httpx.AsyncClient())
    assert await bot_check.diagnose() == 1
    output = capsys.readouterr().out
    assert expected in output
    assert "private" not in output


async def test_diagnostics_uses_only_read_only_endpoints(monkeypatch, capsys):
    config = settings()
    monkeypatch.setattr(bot_check, "get_settings", lambda: config)
    # Direct DNS can fail even when an HTTP proxy provides connectivity.
    monkeypatch.setattr(bot_check.asyncio.get_running_loop(), "getaddrinfo", AsyncMock(side_effect=OSError))
    paths = []

    def handler(request):
        assert request.method == "GET"
        paths.append(request.url.path)
        assert request.headers["Authorization"] == config.bot_token
        if request.url.path == "/me":
            return httpx.Response(200, json={"user_id": 99, "username": "test_bot"})
        assert request.url.path == "/subscriptions"
        return httpx.Response(200, json={"subscriptions": []})

    monkeypatch.setattr(bot_check, "api_client", lambda _: httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url=config.bot_api_url,
        headers={"Authorization": config.bot_token},
    ))
    assert await bot_check.diagnose() == 0
    assert paths == ["/me", "/subscriptions"]
    output = capsys.readouterr().out
    assert "token accepted" in output
    assert "private-test-token" not in output
