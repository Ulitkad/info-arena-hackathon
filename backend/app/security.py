import hashlib
import hmac
import json
import time
from datetime import timedelta
from urllib.parse import parse_qsl

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .db import session_dep
from .models import User, now

settings = get_settings()


def fail(message: str, status: int = 400):
    raise HTTPException(status_code=status, detail=message)


def validate_init_data(raw: str, token: str, max_age: int = 3600) -> dict:
    try:
        pairs = parse_qsl(raw, keep_blank_values=True, strict_parsing=True, max_num_fields=30)
        params = dict(pairs)
        if len(params) != len(pairs) or "hash" not in params:
            raise ValueError("duplicate or missing parameters")
        signature = params.pop("hash")
        age = time.time() - int(params["auth_date"])
        if age < -30 or age > max_age or not token:
            raise ValueError("expired or unconfigured")
        secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
        data = "\n".join(f"{key}={value}" for key, value in sorted(params.items()))
        expected = hmac.new(secret, data.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid signature")
        user = json.loads(params["user"])
        if not isinstance(user, dict) or not isinstance(user.get("id"), int) or user["id"] <= 0:
            raise ValueError("invalid user")
        return {"user": user, "start_param": params.get("start_param")}
    except (ValueError, KeyError, TypeError):
        fail("Не удалось проверить данные MAX. Откройте приложение заново.", 401)


def create_token(user_id: int, *, audience="arena", minutes=60 * 24):
    return jwt.encode(
        {"sub": str(user_id), "aud": audience, "iat": now(), "exp": now() + timedelta(minutes=minutes)},
        settings.secret_key, algorithm="HS256",
    )


def decode_token(token: str, audience="arena") -> int:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"], audience=audience)
        return int(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        fail("Сессия истекла. Откройте приложение заново.", 401)


async def current_user(request: Request, session: AsyncSession = Depends(session_dep)) -> User:
    header = request.headers.get("authorization", "")
    if not header.startswith("Bearer "):
        fail("Требуется вход через MAX", 401)
    user = await session.get(User, decode_token(header[7:]))
    if not user:
        fail("Пользователь не найден", 401)
    return user


def require(user: User, *roles):
    if user.role not in roles:
        fail("Недостаточно прав", 403)


def scope(user: User, organization_id: int):
    if user.role != "ADMIN" and user.organization_id != organization_id:
        fail("Нет доступа к этому учреждению", 403)
