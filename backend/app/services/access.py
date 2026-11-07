"""Membership, invitation and authorization-related use-cases."""

import hashlib
import secrets
from urllib.parse import quote

from sqlalchemy import select

from ..config import get_settings
from ..models import Group, GroupSubject, Invite, JoinRequest, Subject, TeacherLoad, User
from ..repositories import UserRepository
from ..security import fail, require
from .notifications import notify
from .progress import init_progress


async def validate_load(db, teacher, subject_id, group_ids):
    require(teacher, "TEACHER")
    if not group_ids or len(group_ids) != len(set(group_ids)):
        fail("Выберите уникальные группы")
    for gid in group_ids:
        if not await db.get(TeacherLoad, (teacher.id, subject_id, gid)):
            fail("Предмет или группа не входят в вашу нагрузку", 403)
        group = await db.get(Group, gid)
        if not group or group.organization_id != teacher.organization_id:
            fail("Группа недоступна", 403)


async def validate_assignments(db, organization_id, loads):
    if not loads:
        fail("Добавьте хотя бы одну пару предмет — группа")
    unique = {(item.subject_id, item.group_id) for item in loads}
    if len(unique) != len(loads):
        fail("Нагрузка содержит дубли")
    for sid, gid in unique:
        subject, group = await db.get(Subject, sid), await db.get(Group, gid)
        if not subject or not group or subject.organization_id != organization_id or group.organization_id != organization_id:
            fail("Предмет и группа должны принадлежать учреждению", 403)
        if not await db.get(GroupSubject, (gid, sid)):
            fail("Сначала привяжите предмет к группе")


async def create_invite(db, organization_id, role, group_id=None, loads=None):
    if role == "STUDENT":
        group = await db.get(Group, group_id)
        if not group or group.organization_id != organization_id:
            fail("Группа не найдена", 404)
        previous = (await db.scalars(select(Invite).where(
            Invite.group_id == group_id, Invite.role == "STUDENT", Invite.revoked.is_(False), Invite.used_by.is_(None),
        ))).all()
        for old in previous:
            old.revoked = True
    if role == "TEACHER":
        await validate_assignments(db, organization_id, loads or [])
    token = secrets.token_urlsafe(32)
    invite = Invite(token_hash=hashlib.sha256(token.encode()).hexdigest(), role=role,
                    organization_id=organization_id, group_id=group_id,
                    loads=[item.model_dump() for item in loads or []])
    db.add(invite)
    await db.flush()
    settings = get_settings()
    param = "group_token" if role == "STUDENT" else "invite_token"
    web_url = f"{settings.base_app_url.rstrip('/')}?role={role.lower()}&{param}={quote(token)}"
    max_url = f"https://max.ru/{settings.bot_username}?startapp={quote(token)}" if settings.bot_username else None
    return {"id": invite.id, "token": token, "url": max_url or web_url, "web_url": web_url, "max_url": max_url}


async def accept_invite(db, user, token):
    invite = await db.scalar(select(Invite).where(Invite.token_hash == hashlib.sha256(token.encode()).hexdigest()))
    if not invite or invite.revoked:
        fail("Ссылка недействительна или отозвана", 404)
    if invite.role != "STUDENT" and invite.used_by is not None:
        fail("Приглашение уже использовано", 409)
    if user.role not in ("PENDING", "STUDENT"):
        fail("Для текущей роли нельзя принять это приглашение", 409)
    if user.group_id:
        if invite.role == "STUDENT" and user.group_id == invite.group_id:
            return {"status": "APPROVED"}
        fail("Вы уже состоите в группе. Обратитесь к управляющему.", 409)
    if user.organization_id and user.organization_id != invite.organization_id:
        fail("Вы уже состоите в другом учреждении", 409)
    pending = await db.scalar(select(JoinRequest).where(JoinRequest.student_id == user.id, JoinRequest.status == "PENDING"))
    if pending:
        if invite.role == "STUDENT" and pending.group_id == invite.group_id:
            return {"status": "PENDING"}
        fail("У вас уже есть заявка на рассмотрении", 409)
    if invite.role == "STUDENT":
        db.add(JoinRequest(student_id=user.id, group_id=invite.group_id))
        managers = (await db.scalars(select(User).where(User.role == "MANAGER", User.organization_id == invite.organization_id))).all()
        for manager in managers:
            await notify(db, manager.id, "Новая заявка", user.display_name, "/manage/requests")
        return {"status": "PENDING"}
    user.role, user.organization_id = invite.role, invite.organization_id
    invite.used_by = user.id
    if invite.role == "TEACHER":
        for item in invite.loads:
            if not await db.get(GroupSubject, (item["group_id"], item["subject_id"])):
                fail("Нагрузка приглашения устарела. Запросите новую ссылку.", 409)
            db.add(TeacherLoad(teacher_id=user.id, **item))
    await notify(db, user.id, "Добро пожаловать!", "Доступ к учреждению открыт")
    await db.flush()
    return {"status": "APPROVED"}


async def activate_student(db, user, group):
    if user.group_id and user.group_id != group.id:
        fail("Ученик уже состоит в другой группе", 409)
    if user.organization_id and user.organization_id != group.organization_id:
        fail("Пользователь состоит в другом учреждении", 409)
    if user.role not in ("PENDING", "STUDENT"):
        fail("Нельзя изменить служебную роль на ученика", 409)
    user.role, user.organization_id, user.group_id = "STUDENT", group.organization_id, group.id
    await init_progress(db, user)
    await notify(db, user.id, "Заявка одобрена", f"Вы приняты в группу {group.name}. Добро пожаловать на арену!")


async def find_user(db, query):
    users = await UserRepository(db).by_lookup(query)
    if len(users) != 1:
        fail("Пользователь не найден однозначно. Он должен сначала открыть приложение.", 404)
    return users[0]
