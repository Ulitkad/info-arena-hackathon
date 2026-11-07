"""Condition-based achievements, independent from Battlepass rewards."""

from collections.abc import Iterable

from sqlalchemy import func, select

from ..models import Achievement, Duel, Friendship, GroupSubject, Homework, PointLedger, Submission, User, UserAchievement
from .notifications import notify


GENERAL_DEFINITIONS = [
    ("HOMEWORK_COUNT", 1, "Первый шаг", "Выполнить первое домашнее задание", "sparkles"),
    ("HOMEWORK_COUNT", 5, "В ритме", "Выполнить 5 домашних заданий", "star"),
    ("HOMEWORK_COUNT", 10, "Уверенный старт", "Выполнить 10 домашних заданий", "award"),
    ("HOMEWORK_COUNT", 25, "Серьёзный ученик", "Выполнить 25 домашних заданий", "flame"),
    ("HOMEWORK_COUNT", 50, "Профи домашки", "Выполнить 50 домашних заданий", "shield"),
    ("HOMEWORK_COUNT", 100, "Марафонец", "Выполнить 100 домашних заданий", "crown"),
    ("HOMEWORK_COUNT", 500, "Легенда домашки", "Выполнить 500 домашних заданий", "crown"),
    ("HOMEWORK_ON_TIME_COUNT", 3, "На шаг впереди", "Сдать 3 задания до дедлайна", "sparkles"),
    ("HOMEWORK_ON_TIME_COUNT", 10, "Пунктуальность", "Сдать 10 заданий до дедлайна", "star"),
    ("HOMEWORK_FIRST_TRY_COUNT", 5, "С первой попытки", "Получить 5 зачётов без доработки", "shield"),
    ("HOMEWORK_FIRST_TRY_COUNT", 10, "Без ошибок", "Получить 10 зачётов без доработки", "crown"),
    ("HOMEWORK_REVISION_COUNT", 1, "Работа над ошибками", "Исправить работу после доработки", "sparkles"),
    ("HOMEWORK_REVISION_COUNT", 3, "Камбек", "Успешно исправить 3 работы", "flame"),
    ("EVENT_COUNT", 1, "Вне класса", "Принять участие в первом мероприятии", "star"),
    ("EVENT_COUNT", 3, "Активист", "Участвовать в 3 мероприятиях", "award"),
    ("EVENT_COUNT", 5, "Человек дела", "Завершить 5 мероприятий", "shield"),
    ("EVENT_COUNT", 10, "Мастер событий", "Получить баллы за 10 мероприятий", "crown"),
    ("FRIENDS_COUNT", 1, "Не один на арене", "Добавить первого друга", "sparkles"),
    ("FRIENDS_COUNT", 3, "Своя команда", "Добавить 3 друзей", "star"),
    ("FRIENDS_COUNT", 10, "Душа компании", "Иметь 10 друзей", "crown"),
    ("DUEL_WINS", 1, "Первый бой", "Победить в первой дуэли", "swords"),
    ("DUEL_WINS", 3, "Серия побед", "Победить в 3 дуэлях", "swords"),
    ("DUEL_WINS", 10, "Гроза арены", "Победить в 10 дуэлях", "crown"),
    ("DUEL_WIN_STREAK", 3, "Непобедимый", "Победить в 3 дуэлях подряд", "flame"),
    ("DUEL_WIN_STREAK", 5, "Чемпионская серия", "Победить в 5 дуэлях подряд", "crown"),
    ("SUBJECT_COVERAGE", 3, "Многогранная личность", "Получить баллы по 3 предметам", "sparkles"),
    ("ALL_SUBJECTS", 1, "Круг знаний", "Получить баллы по каждому предмету группы", "shield"),
]

SUBJECT_DEFINITIONS = [
    ("SUBJECT_HOMEWORK_COUNT", 1, "Первый предмет", "Выполнить первое задание по предмету", "sparkles"),
    ("SUBJECT_HOMEWORK_COUNT", 10, "Знаток предмета", "Выполнить 10 заданий по предмету", "award"),
    ("SUBJECT_HOMEWORK_COUNT", 25, "Предметный марафонец", "Выполнить 25 заданий по предмету", "crown"),
]


async def seed_achievements(db, organization_id, subject_id=None):
    definitions = SUBJECT_DEFINITIONS if subject_id is not None else GENERAL_DEFINITIONS
    for code, threshold, name, description, icon in definitions:
        exists = await db.scalar(select(Achievement.id).where(
            Achievement.organization_id == organization_id, Achievement.subject_id == subject_id,
            Achievement.code == code, Achievement.threshold == threshold,
        ))
        if not exists:
            db.add(Achievement(organization_id=organization_id, subject_id=subject_id, code=code,
                               threshold=threshold, name=name, description=description, icon=icon))
    await db.flush()


async def seed_all_achievements(db, organization_id, subject_ids: Iterable[int] = ()):
    await seed_achievements(db, organization_id)
    for subject_id in subject_ids:
        await seed_achievements(db, organization_id, subject_id)


async def _count(db, query):
    return await db.scalar(query) or 0


async def _duel_win_streak(db, user_id):
    duels = (await db.scalars(select(Duel).where(
        Duel.status == "COMPLETED", Duel.winner_id.is_not(None),
        (Duel.challenger_id == user_id) | (Duel.opponent_id == user_id),
    ).order_by(Duel.ends_at.desc(), Duel.id.desc()))).all()
    streak = 0
    for duel in duels:
        if duel.winner_id != user_id:
            break
        streak += 1
    return streak


async def achievement_progress(db, user: User, achievement: Achievement):
    code = achievement.code
    homework = select(func.count()).select_from(PointLedger).where(
        PointLedger.user_id == user.id, PointLedger.organization_id == user.organization_id,
        PointLedger.source_kind == "HOMEWORK",
    )
    if code == "HOMEWORK_COUNT":
        return await _count(db, homework)
    if code == "SUBJECT_HOMEWORK_COUNT":
        return await _count(db, homework.where(PointLedger.subject_id == achievement.subject_id))
    if code in ("HOMEWORK_ON_TIME_COUNT", "HOMEWORK_FIRST_TRY_COUNT", "HOMEWORK_REVISION_COUNT"):
        query = select(func.count()).select_from(Submission).join(Homework, Homework.id == Submission.homework_id).where(
            Submission.student_id == user.id, Submission.status == "APPROVED",
        )
        if code == "HOMEWORK_ON_TIME_COUNT":
            query = query.where(Submission.submitted_at <= Homework.deadline)
        elif code == "HOMEWORK_FIRST_TRY_COUNT":
            query = query.where(Submission.revision_count == 0)
        else:
            query = query.where(Submission.revision_count > 0)
        return await _count(db, query)
    if code == "EVENT_COUNT":
        return await _count(db, select(func.count()).select_from(PointLedger).where(
            PointLedger.user_id == user.id, PointLedger.organization_id == user.organization_id,
            PointLedger.source_kind == "EVENT",
        ))
    if code == "FRIENDS_COUNT":
        return await _count(db, select(func.count()).select_from(Friendship).where(
            Friendship.status == "ACCEPTED", (Friendship.low_id == user.id) | (Friendship.high_id == user.id),
        ))
    if code == "DUEL_WINS":
        return user.duel_wins
    if code == "DUEL_WIN_STREAK":
        return await _duel_win_streak(db, user.id)
    if code == "SUBJECT_COVERAGE":
        return await _count(db, select(func.count(func.distinct(PointLedger.subject_id))).where(
            PointLedger.user_id == user.id, PointLedger.organization_id == user.organization_id,
            PointLedger.subject_id.is_not(None), PointLedger.source_kind.in_(["HOMEWORK", "EVENT"]),
        ))
    if code == "ALL_SUBJECTS":
        required = await _count(db, select(func.count()).select_from(GroupSubject).where(GroupSubject.group_id == user.group_id))
        covered = await _count(db, select(func.count(func.distinct(PointLedger.subject_id))).where(
            PointLedger.user_id == user.id, PointLedger.organization_id == user.organization_id,
            PointLedger.subject_id.is_not(None), PointLedger.source_kind.in_(["HOMEWORK", "EVENT"]),
        ))
        return 1 if required and covered >= required else 0
    return 0


async def evaluate_achievements(db, user: User):
    if user.role != "STUDENT" or not user.organization_id:
        return []
    subject_ids = select(GroupSubject.subject_id).where(GroupSubject.group_id == user.group_id)
    achievements = (await db.scalars(select(Achievement).where(
        Achievement.organization_id == user.organization_id,
        (Achievement.subject_id.is_(None) | Achievement.subject_id.in_(subject_ids)),
    ))).all()
    unlocked = []
    for achievement in achievements:
        if await db.get(UserAchievement, (user.id, achievement.id)):
            continue
        if await achievement_progress(db, user, achievement) < achievement.threshold:
            continue
        db.add(UserAchievement(user_id=user.id, achievement_id=achievement.id))
        unlocked.append(achievement)
        await notify(db, user.id, "Новое достижение!", f"Открыто «{achievement.name}»", "/achievements")
    if unlocked:
        await db.flush()
    return unlocked
