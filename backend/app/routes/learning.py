import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import schemas as s
from ..config import get_settings
from ..db import session_dep
from ..models import (
    Event, EventGroup, EventParticipant, GroupSubject, Homework, HomeworkGroup,
    Inventory, Progress, Reward, Subject, Submission, Upload, User, now,
)
from ..security import current_user, fail, require
from ..services import (
    award, complete_event, event_join, event_owner, notify, public_user, row,
    student_access, validate_files, validate_load,
)

router = APIRouter(prefix="/api")


@router.post("/uploads", status_code=201)
async def upload(file: UploadFile, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    require(user, "STUDENT", "TEACHER", "MANAGER", "ADMIN")
    suffix = Path(file.filename or "file").suffix.lower()
    allowed = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf", ".txt", ".docx", ".xlsx", ".pptx", ".zip"}
    if suffix not in allowed:
        fail("Разрешены изображения, PDF, TXT, Office и ZIP")
    name = f"{secrets.token_hex(24)}{suffix}"
    directory = get_settings().upload_dir
    directory.mkdir(parents=True, exist_ok=True)
    path, size = directory / name, 0
    try:
        with path.open("wb") as target:
            while chunk := await file.read(1024 * 256):
                size += len(chunk)
                if size > 20 * 1024 * 1024:
                    fail("Файл должен быть не больше 20 МБ", 413)
                target.write(chunk)
        if not size:
            fail("Файл пуст")
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    await file.close()
    item = Upload(owner_id=user.id, url=f"/media/{name}", name=(file.filename or "Файл")[:200], size=size)
    db.add(item)
    await db.flush()
    return row(item)


@router.get("/battlepasses")
async def battlepasses(user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    require(user, "STUDENT")
    subject_ids = (await db.scalars(select(GroupSubject.subject_id).where(GroupSubject.group_id == user.group_id))).all()
    subjects = (await db.scalars(select(Subject).where(Subject.id.in_(subject_ids)))).all()
    inventory = (await db.scalars(select(Inventory.reward_id).where(Inventory.user_id == user.id))).all()
    rewards = (await db.scalars(select(Reward).where(Reward.organization_id == user.organization_id, Reward.special.is_(False)).order_by(Reward.threshold))).all()
    progresses = (await db.scalars(select(Progress).where(Progress.user_id == user.id))).all()
    points = {p.scope: p.points for p in progresses}
    passes = [{"id": "general", "name": "Общий пропуск", "subtitle": "Все твои победы — в одном месте", "color": "#0284c7", "subject_id": None}]
    passes += [{"id": str(item.id), "name": item.name, "subtitle": "Предметный пропуск", "color": item.color, "subject_id": item.id} for item in subjects]
    for item in passes:
        item["points"] = points.get("general" if item["subject_id"] is None else f"subject:{item['subject_id']}", 0)
        item["rewards"] = [{**row(r), "unlocked": r.id in inventory} for r in rewards if r.subject_id == item["subject_id"]]
        item["level"] = sum(r["threshold"] <= item["points"] for r in item["rewards"])
        item["next_threshold"] = next((r["threshold"] for r in item["rewards"] if r["threshold"] > item["points"]), item["points"])
    return passes


@router.get("/inventory")
async def inventory(user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    items = (await db.execute(select(Reward, Inventory).join(Inventory).where(Inventory.user_id == user.id).order_by(Inventory.unlocked_at.desc()))).all()
    return [{**row(reward), "unlocked_at": item.unlocked_at} for reward, item in items]


@router.get("/homework")
async def homework(user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    require(user, "TEACHER", "STUDENT")
    query = select(Homework)
    if user.role == "TEACHER":
        query = query.where(Homework.teacher_id == user.id)
    else:
        query = query.join(HomeworkGroup).where(HomeworkGroup.group_id == user.group_id)
    items = (await db.scalars(query.order_by(Homework.deadline.desc()).limit(200))).all()
    result = []
    for item in items:
        subject = await db.get(Subject, item.subject_id)
        gids = (await db.scalars(select(HomeworkGroup.group_id).where(HomeworkGroup.homework_id == item.id))).all()
        submission = await db.scalar(select(Submission).where(Submission.homework_id == item.id, Submission.student_id == user.id))
        pending = await db.scalar(select(func.count()).select_from(Submission).where(Submission.homework_id == item.id, Submission.status == "SUBMITTED"))
        result.append({**row(item), "subject": row(subject), "group_ids": gids, "reward": 1,
                       "submission": row(submission) if submission else None, "pending_count": pending})
    return result


@router.post("/homework", status_code=201)
async def create_homework(data: s.HomeworkInput, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    await validate_load(db, user, data.subject_id, data.group_ids)
    await validate_files(db, user, data.files)
    if data.deadline <= now():
        fail("Дедлайн должен быть в будущем")
    item = Homework(teacher_id=user.id, **data.model_dump(exclude={"group_ids"}))
    db.add(item)
    await db.flush()
    for gid in data.group_ids:
        db.add(HomeworkGroup(homework_id=item.id, group_id=gid))
    students = (await db.scalars(select(User).where(User.group_id.in_(data.group_ids), User.role == "STUDENT"))).all()
    for student in students:
        await notify(db, student.id, "Новое задание", item.title, f"/arena?homework={item.id}")
    return row(item)


@router.post("/homework/{hid}/submit")
async def submit_homework(hid: int, data: s.ContentInput, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    item = await db.get(Homework, hid)
    if not item:
        fail("Задание не найдено", 404)
    await student_access(db, user, item, HomeworkGroup, HomeworkGroup.homework_id)
    if now() >= item.deadline:
        fail("Срок сдачи уже истек", 409)
    await validate_files(db, user, data.files)
    submission = await db.scalar(select(Submission).where(Submission.homework_id == hid, Submission.student_id == user.id))
    if submission and submission.status == "APPROVED":
        fail("Работа уже зачтена", 409)
    if not submission:
        submission = Submission(homework_id=hid, student_id=user.id)
        db.add(submission)
    submission.text, submission.files = data.text, data.files
    submission.status, submission.submitted_at = "SUBMITTED", now()
    await notify(db, item.teacher_id, "Работа на проверку", f"{user.display_name}: {item.title}", f"/teach?homework={hid}")
    await db.flush()
    return row(submission)


@router.get("/homework/{hid}/submissions")
async def submissions(hid: int, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    require(user, "TEACHER")
    item = await db.get(Homework, hid)
    if not item or item.teacher_id != user.id:
        fail("Задание не найдено", 404)
    items = (await db.execute(select(Submission, User).join(User).where(Submission.homework_id == hid).order_by(Submission.submitted_at))).all()
    return [{**row(submission), "student": public_user(student)} for submission, student in items]


@router.post("/submissions/{sid}/review")
async def review(sid: int, data: s.ReviewInput, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    require(user, "TEACHER")
    submission = await db.get(Submission, sid)
    if not submission:
        fail("Работа не найдена", 404)
    homework = await db.get(Homework, submission.homework_id)
    if homework.teacher_id != user.id:
        fail("Нет доступа к работе", 403)
    if submission.status == "APPROVED":
        if data.approve:
            return {"ok": True}
        fail("Зачтенную работу нельзя вернуть на доработку", 409)
    if submission.status != "SUBMITTED":
        fail("Дождитесь повторной отправки работы", 409)
    student = await db.get(User, submission.student_id)
    if student.organization_id != user.organization_id or student.role != "STUDENT":
        fail("Ученик больше не состоит в учреждении", 409)
    submission.status = "APPROVED" if data.approve else "REVISION"
    submission.feedback = data.feedback
    if data.approve:
        await award(db, student, 1, "HOMEWORK", homework.id, homework.title, homework.subject_id)
    await notify(db, student.id, "Работа зачтена!" if data.approve else "Задание на доработку",
                 f"{homework.title}. {'+1 балл' if data.approve else data.feedback}", f"/arena?homework={homework.id}")
    return {"ok": True}


@router.get("/events")
async def events(user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    require(user, "TEACHER", "STUDENT")
    query = select(Event)
    query = query.where(Event.teacher_id == user.id) if user.role == "TEACHER" else query.join(EventGroup).where(EventGroup.group_id == user.group_id)
    items = (await db.scalars(query.order_by(Event.created_at.desc()).limit(200))).all()
    result = []
    for item in items:
        count = await db.scalar(select(func.count()).select_from(EventParticipant).where(EventParticipant.event_id == item.id, EventParticipant.status == "JOINED"))
        participant = await db.get(EventParticipant, (item.id, user.id))
        subject = await db.get(Subject, item.subject_id)
        gids = (await db.scalars(select(EventGroup.group_id).where(EventGroup.event_id == item.id))).all()
        result.append({**row(item), "subject": row(subject), "count": count, "group_ids": gids,
                       "participant": row(participant) if participant else None})
    return result


@router.post("/events", status_code=201)
async def create_event(data: s.EventInput, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    await validate_load(db, user, data.subject_id, data.group_ids)
    if data.closes_at <= now():
        fail("Дата закрытия набора должна быть в будущем")
    event = Event(teacher_id=user.id, **data.model_dump(exclude={"group_ids"}))
    db.add(event)
    await db.flush()
    for gid in data.group_ids:
        db.add(EventGroup(event_id=event.id, group_id=gid))
    students = (await db.scalars(select(User).where(User.group_id.in_(data.group_ids), User.role == "STUDENT"))).all()
    for student in students:
        await notify(db, student.id, "Новое мероприятие", f"{event.title} · +{event.points} баллов", "/arena?tab=events")
    return row(event)


@router.post("/events/{eid}/join")
async def join_event(eid: int, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    event = await db.get(Event, eid)
    if not event:
        fail("Мероприятие не найдено", 404)
    await event_join(db, event, user)
    return {"ok": True}


@router.post("/events/{eid}/leave")
async def leave_event(eid: int, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    event = await db.get(Event, eid)
    if not event:
        fail("Мероприятие не найдено", 404)
    await student_access(db, user, event, EventGroup, EventGroup.event_id)
    if event.status != "OPEN" or event.closes_at <= now():
        fail("Изменение состава уже закрыто", 409)
    participant = await db.get(EventParticipant, (eid, user.id))
    if participant and not participant.blacklisted:
        participant.status = "LEFT"
    return {"ok": True}


@router.get("/events/{eid}/participants")
async def participants(eid: int, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    await event_owner(db, user, eid)
    results = (await db.execute(select(EventParticipant, User).join(User).where(EventParticipant.event_id == eid))).all()
    return [{**row(participant), "user": public_user(student)} for participant, student in results]


@router.post("/events/{eid}/participants")
async def force_add(eid: int, data: s.ParticipantInput, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    event = await event_owner(db, user, eid)
    student = await db.get(User, data.user_id)
    if not student:
        fail("Ученик не найден", 404)
    await event_join(db, event, student, force=True)
    await notify(db, student.id, "Вы добавлены в мероприятие", event.title, "/arena?tab=events")
    return {"ok": True}


@router.delete("/events/{eid}/participants/{uid}")
async def kick(eid: int, uid: int, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    event = await event_owner(db, user, eid)
    if event.status == "COMPLETED":
        fail("Мероприятие уже завершено", 409)
    participant = await db.get(EventParticipant, (eid, uid))
    if not participant:
        fail("Участник не найден", 404)
    participant.status = "KICKED"
    if event.status == "OPEN" and event.closes_at > now():
        participant.blacklisted = True
    await notify(db, uid, "Состав мероприятия изменен", f"Вы исключены: {event.title}", "/arena?tab=events")
    return {"ok": True}


@router.post("/events/{eid}/close")
async def close_event(eid: int, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    event = await event_owner(db, user, eid)
    if event.status == "OPEN":
        event.status = "CLOSED"
    return {"ok": True}


@router.post("/events/{eid}/complete")
async def finish_event(eid: int, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    event = await event_owner(db, user, eid)
    await complete_event(db, event)
    return {"ok": True}
