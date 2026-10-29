import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest
from fastapi import HTTPException

from app.security import validate_init_data


def signed_data(*, token="test-max-token", auth_date=None, user=None, **extra):
    params = {
        "auth_date": str(int(time.time()) if auth_date is None else auth_date),
        "user": json.dumps(user or {"id": 700001, "first_name": "Тест"}, ensure_ascii=False),
        **extra,
    }
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    check = "\n".join(f"{key}={value}" for key, value in sorted(params.items()))
    params["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(params)


def test_valid_init_data_with_start_param():
    assert validate_init_data(signed_data(start_param="invite-token"), "test-max-token") == {
        "user": {"id": 700001, "first_name": "Тест"}, "start_param": "invite-token",
    }


@pytest.mark.parametrize("raw", [
    lambda: signed_data(token="wrong-token"),
    lambda: signed_data(auth_date=int(time.time()) - 3601),
    lambda: signed_data(auth_date=int(time.time()) + 60),
    lambda: signed_data() + "&auth_date=123",
    lambda: signed_data(user={"id": -1}),
    lambda: "not-valid-query",
])
def test_rejects_invalid_init_data(raw):
    with pytest.raises(HTTPException) as error:
        validate_init_data(raw(), "test-max-token")
    assert error.value.status_code == 401


async def test_max_login_uses_signed_profile(arena):
    response = await arena.client.post("/api/auth/max", json={"init_data": signed_data()})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["user"]["max_id"] == 700001
    assert data["user"]["role"] == "PENDING"
    me = await arena.client.get("/api/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert me.status_code == 200
    assert me.json()["display_name"] == "Тест"


async def test_signed_start_param_creates_join_request(arena, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "bot_username", "arena_test_bot")
    invitation = await arena.client.post("/api/organizations/1/invites", headers=arena.auth(900004),
                                         json={"role": "STUDENT", "group_id": 1})
    assert invitation.status_code == 200, invitation.text
    link = invitation.json()
    assert link["url"] == f"https://max.ru/arena_test_bot?startapp={link['token']}"
    response = await arena.client.post("/api/auth/max", json={"init_data": signed_data(start_param=link["token"])})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    me = await arena.client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["role"] == "PENDING"
    assert me.json()["join_request"]["group_id"] == 1


async def test_dev_auth_is_unavailable_when_disabled(arena, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "dev_auth", False)
    assert (await arena.client.post("/api/auth/dev", json={"persona": "admin"})).status_code == 404


async def test_websocket_ticket_is_not_an_api_token(arena):
    response = await arena.client.post("/api/ws-ticket", headers=arena.auth(900001))
    assert response.status_code == 200
    denied = await arena.client.get("/api/me", headers={"Authorization": f"Bearer {response.json()['ticket']}"})
    assert denied.status_code == 401
