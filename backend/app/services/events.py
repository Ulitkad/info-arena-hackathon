"""Learning event access and completion use-cases."""

from sqlalchemy import func, select

from ..models import Event, EventGroup, EventParticipant, Group, Subject, User, now
from ..security import fail, require
from .notifications import notify
from .progress import award


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
