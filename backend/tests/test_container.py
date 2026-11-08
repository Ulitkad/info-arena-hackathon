"""Exercise container helpers without Docker or network/MAX access."""

import io
import runpy
import urllib.error
from pathlib import Path
from unittest.mock import Mock

import pytest

DOCKER_DIR = Path(__file__).resolve().parents[2] / "docker"


class Response(io.BytesIO):
    status = 200


def test_container_healthchecks_frontend_and_api(monkeypatch):
    open_url = Mock(side_effect=[Response(b'<div id="app"></div>'), Response(b'{"status":"ok"}')])
    monkeypatch.setattr("urllib.request.urlopen", open_url)
    runpy.run_path(str(DOCKER_DIR / "healthcheck.py"))["main"]()
    assert [call.args[0] for call in open_url.call_args_list] == [
        "http://127.0.0.1:8080/", "http://127.0.0.1:8080/api/health",
    ]


@pytest.mark.parametrize("body", [b"", b"upstream error"])
def test_container_healthcheck_rejects_missing_frontend(monkeypatch, body):
    monkeypatch.setattr("urllib.request.urlopen", Mock(return_value=Response(body)))
    with pytest.raises(SystemExit, match="Frontend is not ready"):
        runpy.run_path(str(DOCKER_DIR / "healthcheck.py"))["main"]()


def test_container_healthcheck_rejects_unhealthy_api(monkeypatch):
    monkeypatch.setattr("urllib.request.urlopen", Mock(side_effect=[
        Response(b'<div id="app"></div>'), Response(b'{"status":"error"}'),
    ]))
    with pytest.raises(SystemExit, match="API is not ready"):
        runpy.run_path(str(DOCKER_DIR / "healthcheck.py"))["main"]()


def test_disabled_bot_does_not_wait_for_api(monkeypatch):
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    open_url = Mock()
    execute = Mock()
    monkeypatch.setattr("urllib.request.urlopen", open_url)
    monkeypatch.setattr("os.execv", execute)
    runpy.run_path(str(DOCKER_DIR / "start-bot.py"))["main"]()
    open_url.assert_not_called()
    assert execute.call_args.args[1][1:] == ["-m", "app.bot"]


def test_bot_waits_for_ready_api_before_exec(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "container-test-token")
    open_url = Mock(side_effect=[urllib.error.URLError("starting"), Response(b'{"status":"ok"}')])
    execute = Mock()
    sleep = Mock()
    monkeypatch.setattr("urllib.request.urlopen", open_url)
    monkeypatch.setattr("os.execv", execute)
    monkeypatch.setattr("time.sleep", sleep)
    runpy.run_path(str(DOCKER_DIR / "start-bot.py"))["main"]()
    assert open_url.call_count == 2
    sleep.assert_called_once_with(1)
    execute.assert_called_once()
