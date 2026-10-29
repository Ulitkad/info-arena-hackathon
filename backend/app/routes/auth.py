import hashlib
import hmac
import time

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import schemas as s
from ..config import get_settings
from ..db import session_dep
from ..models import Group, Inventory, JoinRequest, Organization, Reward, User
from ..security import create_token, current_user, fail, validate_init_data
from ..services import accept_invite, public_user, row

router = APIRouter(prefix="/api")
settings = get_settings()


@router.get("/config")
async def config():
    return {"dev_auth": settings.dev_auth, "demo": settings.seed_demo}


async def auth_result(db, user):
    await db.flush()
    return {"access_token": create_token(user.id), "user": public_user(user)}


@router.post("/auth/max")
async def login(data: s.AuthInput, db: AsyncSession = Depends(session_dep)):
    validated = validate_init_data(data.init_data, settings.bot_token)
    profile = validated["user"]
    user = await db.scalar(select(User).where(User.max_id == profile["id"]))
    name = profile.get("name") or " ".join(filter(None, [profile.get("first_name"), profile.get("last_name")])) or "Участник MAX"
    if not user:
        user = User(max_id=profile["id"], display_name=name[:160])
        db.add(user)
        await db.flush()
    user.display_name = name[:160]
    user.username = (profile.get("username") or "")[:100] or None
    avatar = profile.get("photo_url") or profile.get("avatar_url")
    user.avatar_url = avatar if isinstance(avatar, str) and avatar.startswith("https://") else None
    if settings.admin_max_id and user.max_id == settings.admin_max_id:
        user.role = "ADMIN"
    token = data.invite_token or validated.get("start_param")
    if token:
        await accept_invite(db, user, token)
    if user.role == "STUDENT" and user.group_id:
        from ..services import init_progress
        await init_progress(db, user)
    return await auth_result(db, user)


@router.post("/auth/dev")
async def dev_login(data: s.DevAuth, db: AsyncSession = Depends(session_dep)):
    if not settings.dev_auth or not settings.seed_demo:
        fail("Демонстрационный вход отключен", 404)
    ids = {"student": 900001, "friend": 900002, "teacher": 900003, "manager": 900004, "admin": 900005}
    user = await db.scalar(select(User).where(User.max_id == ids[data.persona]))
    if not user:
        fail("Демонстрационные данные не созданы", 409)
    return await auth_result(db, user)


@router.get("/me")
async def me(user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    organization = await db.get(Organization, user.organization_id) if user.organization_id else None
    group = await db.get(Group, user.group_id) if user.group_id else None
    pending = await db.scalar(select(JoinRequest).where(JoinRequest.student_id == user.id).order_by(JoinRequest.id.desc()))
    return {**public_user(user), "organization": row(organization) if organization else None,
            "group": row(group) if group else None, "join_request": row(pending) if pending else None}


@router.post("/invites/accept")
async def join(data: s.TokenInput, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    return await accept_invite(db, user, data.token)


@router.put("/me/profile")
async def customize(data: s.ProfileInput, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    async def owned(reward_id, kind):
        if reward_id is None:
            return
        reward = await db.get(Reward, reward_id)
        if not reward or reward.kind != kind or not await db.get(Inventory, (user.id, reward_id)):
            fail("Награда еще не открыта или имеет другой тип", 403)
    await owned(data.active_title_id, "TITLE")
    await owned(data.active_frame_id, "FRAME")
    if len(set(data.showcase)) != len(data.showcase):
        fail("Выберите разные достижения")
    for rid in data.showcase:
        await owned(rid, "BADGE")
    user.active_title_id, user.active_frame_id, user.showcase = data.active_title_id, data.active_frame_id, data.showcase
    return {"ok": True}


@router.post("/me/phone")
async def save_phone(data: s.PhoneInput, user: User = Depends(current_user)):
    age = time.time() - data.auth_date
    phone = data.phone.lstrip("+")
    check = f"authDate={data.auth_date}\nphone={phone}\nuserId={user.max_id}"
    expected = hmac.new(settings.bot_token.encode(), check.encode(), hashlib.sha256).hexdigest()
    if not settings.bot_token or age < -30 or age > 3600 or not hmac.compare_digest(expected, data.hash.lower()):
        fail("Не удалось подтвердить номер телефона", 401)
    user.phone = phone
    return {"ok": True}
