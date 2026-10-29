import hashlib
import secrets
from datetime import timedelta
from urllib.parse import quote

from dateutil.relativedelta import relativedelta
from sqlalchemy import func, or_, select

from .config import get_settings
from .models import (
    Duel, Event, EventGroup, EventParticipant, Group, GroupSubject, Inventory, Invite, JoinRequest, Notification, PointLedger, Progress, Reward, Subject,
    TeacherLoad, Upload, User, now,
)
from .security import fail, require


def row(obj, *excluded):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns if c.name not in excluded}


def public_user(user):
    return row(user, "phone")


async def notify(db, user_id, title, body="", link="/"):
    db.add(Notification(user_id=user_id, title=title, body=body, link=link))


async def init_progress(db, user):
    scopes = ["general"]
    if user.group_id:
        ids = (await db.scalars(select(GroupSubject.subject_id).where(GroupSubject.group_id == user.group_id))).all()
        scopes += [f"subject:{sid}" for sid in ids]
    existing = set((await db.scalars(select(Progress.scope).where(Progress.user_id == user.id))).all())
    for value in scopes:
        if value not in existing:
            db.add(Progress(user_id=user.id, scope=value, points=0))
    await db.flush()


async def seed_rewards(db, organization_id, subject_id=None):
    definitions = [
        ("Первый шаг", "BADGE", 1, "sparkles"),
        ("На старте", "TITLE", 5, "star"),
        ("Небесная рамка", "FRAME", 10, "shield"),
        ("В потоке", "BADGE", 20, "flame"),
        ("Исследователь", "TITLE", 35, "award"),
        ("Облачная рамка", "FRAME", 50, "sparkles"),
        ("Выше облаков", "BADGE", 75, "crown"),
        ("Легенда арены", "TITLE", 100, "crown"),
    ]
    for name, kind, threshold, icon in definitions:
        db.add(Reward(organization_id=organization_id, subject_id=subject_id, name=name, kind=kind, threshold=threshold, icon=icon))
    if subject_id is None:
        db.add(Reward(organization_id=organization_id, name="Дуэлянт", kind="BADGE", threshold=0, icon="swords", special=True))
    await db.flush()


async def unlock_rewards(db, user, subject_id=None):
    progress_scope = "general" if subject_id is None else f"subject:{subject_id}"
    points = await db.scalar(select(Progress.points).where(Progress.user_id == user.id, Progress.scope == progress_scope)) or 0
    rewards = (await db.scalars(select(Reward).where(
        Reward.organization_id == user.organization_id, Reward.subject_id == subject_id,
        Reward.special.is_(False), Reward.threshold <= points,
    ))).all()
    for reward in rewards:
        if not await db.get(Inventory, (user.id, reward.id)):
            db.add(Inventory(user_id=user.id, reward_id=reward.id))
            await notify(db, user.id, "Новый уровень!", f"Открыта награда «{reward.name}»", f"/battlepass/{subject_id or 'general'}")
    await db.flush()


async def award(db, user: User, points: int, source_kind: str, source_id: int, label: str, subject_id=None):
    if await db.scalar(select(PointLedger.id).where(
        PointLedger.user_id == user.id, PointLedger.source_kind == source_kind, PointLedger.source_id == source_id,
    )):
        return False
    if not user.organization_id:
        fail("Ученик не состоит в учреждении", 409)
    await init_progress(db, user)
    db.add(PointLedger(user_id=user.id, organization_id=user.organization_id, subject_id=subject_id,
                       points=points, source_kind=source_kind, source_id=source_id, label=label))
    scopes = ["general"] + ([f"subject:{subject_id}"] if subject_id else [])
    for value in scopes:
        progress = await db.scalar(select(Progress).where(Progress.user_id == user.id, Progress.scope == value))
        if progress is None:
            progress = Progress(user_id=user.id, scope=value, points=0)
            db.add(progress)
        progress.points += points
    await db.flush()
    await unlock_rewards(db, user)
    if subject_id:
        await unlock_rewards(db, user, subject_id)
    return True


async def validate_files(db, user, files):
    for url in set(files):
        upload = await db.scalar(select(Upload).where(Upload.url == url, Upload.owner_id == user.id))
        if not upload:
            fail("Можно прикреплять только собственные загруженные файлы", 403)


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
    if invite.role != "STUDENT" and invite.used_by and invite.used_by != user.id:
        fail("Приглашение уже использовано", 409)
    if invite.used_by == user.id and invite.role != "STUDENT":
        return {"status": "APPROVED"}
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


async def academic_total(db, user_id, subject_id=None, until=None, since=None, organization_id=None):
    query = select(func.coalesce(func.sum(PointLedger.points), 0)).where(
        PointLedger.user_id == user_id, PointLedger.source_kind.in_(["HOMEWORK", "EVENT"]),
    )
    if organization_id is not None:
        query = query.where(PointLedger.organization_id == organization_id)
    if subject_id is not None:
        query = query.where(PointLedger.subject_id == subject_id)
    if until:
        query = query.where(PointLedger.created_at <= until)
    if since:
        query = query.where(PointLedger.created_at >= since)
    return await db.scalar(query) or 0


async def duel_scores(db, duel):
    if not duel.starts_at:
        return 0, 0
    if duel.status == "COMPLETED":
        return duel.challenger_score, duel.opponent_score
    # Count the immutable academic ledger inside the actual competition window.
    # Progress includes PvP bonuses and must never be used as the duel scoreboard.
    end = min(now(), duel.ends_at)
    return tuple([await academic_total(db, uid, duel.subject_id, end, duel.starts_at, duel.organization_id)
                  for uid in (duel.challenger_id, duel.opponent_id)])


async def duel_slots(db, user_id):
    return await db.scalar(select(func.count()).select_from(Duel).where(
        Duel.status == "ACTIVE", or_(Duel.challenger_id == user_id, Duel.opponent_id == user_id),
    ))


async def finish_duel(db, duel):
    if duel.status != "ACTIVE" or not duel.ends_at or duel.ends_at > now():
        return
    a, b = await duel_scores(db, duel)
    duel.challenger_score, duel.opponent_score = a, b
    players = [await db.get(User, uid) for uid in (duel.challenger_id, duel.opponent_id)]
    if any(not p or p.organization_id != duel.organization_id or p.role != "STUDENT" for p in players):
        duel.status = "CANCELLED"
        return
    duel.status = "COMPLETED"
    if a == b:
        for player in players:
            await award(db, player, 3, "DUEL", duel.id, "Ничья в дуэли")
            await notify(db, player.id, "Дружеская ничья", f"Счет {a}:{b}. +3 балла в общий БП", "/friends")
    else:
        winner = players[0] if a > b else players[1]
        duel.winner_id = winner.id
        winner.duel_wins += 1
        await award(db, winner, 10, "DUEL", duel.id, "Победа в дуэли")
        badge = await db.scalar(select(Reward).where(Reward.organization_id == winner.organization_id, Reward.special.is_(True)))
        if badge and not await db.get(Inventory, (winner.id, badge.id)):
            db.add(Inventory(user_id=winner.id, reward_id=badge.id))
        for player in players:
            await notify(db, player.id, "Дуэль завершена", f"{winner.display_name} побеждает {a}:{b}. Победителю +10 баллов", "/friends")
    await db.flush()


async def start_duel(db, duel, user):
    if user.id != duel.opponent_id or duel.status != "PENDING":
        fail("Нельзя принять этот вызов", 409)
    if duel.created_at + timedelta(hours=24) <= now():
        fail("Время ответа на вызов истекло", 409)
    challenger = await db.get(User, duel.challenger_id)
    if challenger.organization_id != user.organization_id or challenger.role != "STUDENT":
        fail("Соперник больше не доступен для дуэли", 409)
    if duel.subject_id:
        for player in (user, challenger):
            if not await db.get(GroupSubject, (player.group_id, duel.subject_id)):
                fail("Оба участника должны изучать выбранный предмет", 409)
    for uid in (duel.challenger_id, duel.opponent_id):
        if await duel_slots(db, uid) >= 3:
            fail("У одного из участников уже три активные дуэли", 409)
    duel.starts_at = now()
    duel.ends_at = duel.starts_at + (relativedelta(months=1) if duel.duration == "1m" else timedelta(days=int(duel.duration[0])))
    duel.initial_challenger = await academic_total(db, duel.challenger_id, duel.subject_id, organization_id=duel.organization_id)
    duel.initial_opponent = await academic_total(db, duel.opponent_id, duel.subject_id, organization_id=duel.organization_id)
    duel.status = "ACTIVE"
    for uid in (duel.challenger_id, duel.opponent_id):
        await notify(db, uid, "Дуэль началась!", "Пусть победит самый любознательный", "/friends")


async def student_access(db, student, entity, link_model, id_column):
    require(student, "STUDENT")
    if not student.group_id or not await db.scalar(select(link_model).where(
        id_column == entity.id, link_model.group_id == student.group_id,
    )):
        fail("Нет доступа к этой группе", 403)


async def event_owner(db, user, event_id):
    require(user, "TEACHER")
    event = await db.get(Event, event_id)
    if not event or event.teacher_id != user.id:
        fail("Мероприятие не найдено", 404)
    return event


async def event_join(db, event, student, force=False):
    await student_access(db, student, event, EventGroup, EventGroup.event_id)
    if event.status != "OPEN" or event.closes_at <= now():
        fail("Набор закрыт", 409)
    participant = await db.get(EventParticipant, (event.id, student.id))
    if participant and participant.blacklisted:
        fail("Вы исключены из этого мероприятия", 403)
    if participant and participant.status == "JOINED":
        return
    count = await db.scalar(select(func.count()).select_from(EventParticipant).where(
        EventParticipant.event_id == event.id, EventParticipant.status == "JOINED",
    ))
    if count >= event.max_participants:
        fail("Все места уже заняты", 409)
    if participant:
        participant.status = "JOINED"
    else:
        db.add(EventParticipant(event_id=event.id, user_id=student.id))


async def complete_event(db, event):
    if event.status == "COMPLETED":
        return
    participants = (await db.scalars(select(EventParticipant).where(
        EventParticipant.event_id == event.id, EventParticipant.status == "JOINED",
    ))).all()
    if len(participants) < event.min_participants:
        fail("Не набран минимальный состав участников", 409)
    event.status = "COMPLETED"
    for participant in participants:
        student = await db.get(User, participant.user_id)
        if student.role != "STUDENT":
            continue
        group = await db.get(Group, student.group_id)
        subject = await db.get(Subject, event.subject_id)
        if not group or group.organization_id != subject.organization_id:
            continue
        await award(db, student, event.points, "EVENT", event.id, event.title, event.subject_id)
        await notify(db, student.id, "Мероприятие завершено", f"{event.title}: +{event.points} баллов", "/arena")


async def find_user(db, query):
    query = query.strip()
    conditions = [func.lower(User.username) == query.lstrip("@").lower()]
    if query.lstrip("+").isdigit():
        conditions.append(User.max_id == int(query.lstrip("+")))
        conditions.append(User.phone == query.lstrip("+"))
    users = (await db.scalars(select(User).where(or_(*conditions)).limit(2))).all()
    if len(users) != 1:
        fail("Пользователь не найден однозначно. Он должен сначала открыть приложение.", 404)
    return users[0]
