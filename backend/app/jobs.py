import logging
from datetime import timedelta

from sqlalchemy import select, text

from .db import Session
from .models import Duel, Event, Homework, HomeworkGroup, Submission, User, now
from .services import finish_duel, notify

logger = logging.getLogger(__name__)


async def run_jobs():
    async with Session() as db:
        await db.execute(text("BEGIN IMMEDIATE"))
        try:
            moment = now()
            expired = (await db.scalars(select(Duel).where(Duel.status == "PENDING", Duel.created_at <= moment - timedelta(hours=24)))).all()
            for duel in expired:
                duel.status = "EXPIRED"
                await notify(db, duel.challenger_id, "Время вызова истекло", "Друг не ответил в течение 24 часов", "/friends")
            duels = (await db.scalars(select(Duel).where(Duel.status == "ACTIVE", Duel.ends_at <= moment))).all()
            for duel in duels:
                await finish_duel(db, duel)
            events = (await db.scalars(select(Event).where(Event.status == "OPEN", Event.closes_at <= moment))).all()
            for event in events:
                event.status = "CLOSED"
                await notify(db, event.teacher_id, "Набор завершен", event.title, "/teach?tab=events")
            tasks = (await db.scalars(select(Homework).where(Homework.deadline <= moment + timedelta(hours=6), Homework.deadline_notified.is_(False)))).all()
            for task in tasks:
                task.deadline_notified = True
                if task.deadline <= moment:
                    continue
                gids = (await db.scalars(select(HomeworkGroup.group_id).where(HomeworkGroup.homework_id == task.id))).all()
                students = (await db.scalars(select(User).where(User.group_id.in_(gids), User.role == "STUDENT"))).all()
                for student in students:
                    submitted = await db.scalar(select(Submission.id).where(Submission.homework_id == task.id, Submission.student_id == student.id, Submission.status.in_(["SUBMITTED", "APPROVED"])))
                    if not submitted:
                        await notify(db, student.id, "Дедлайн уже близко", f"До сдачи «{task.title}» осталось меньше 6 часов", f"/arena?homework={task.id}")
            await db.commit()
        except BaseException:
            await db.rollback()
            logger.exception("Scheduled transaction failed")
            raise
