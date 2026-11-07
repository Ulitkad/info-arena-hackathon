"""Duel scoring and lifecycle use-cases."""

from datetime import timedelta

from dateutil.relativedelta import relativedelta
from sqlalchemy import func, or_, select

from ..models import Duel, GroupSubject, PointLedger, User, now
from ..security import fail
from .notifications import notify
from .progress import award


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
