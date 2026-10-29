from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import schemas as s
from ..db import session_dep
from ..models import Duel, Friendship, GroupSubject, PointLedger, Reward, User, now
from ..security import current_user, fail, require
from ..services import duel_scores, duel_slots, finish_duel, notify, public_user, row, start_duel

router = APIRouter(prefix="/api")


@router.get("/users/search")
async def search_users(q: str = "", user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    require(user, "STUDENT")
    if len(q.strip()) < 2:
        return []
    escaped = q.strip().lstrip("@")[:100].replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    users = (await db.scalars(select(User).where(
        User.organization_id == user.organization_id, User.role == "STUDENT", User.id != user.id,
        or_(User.display_name.ilike(f"%{escaped}%", escape="\\"), User.username.ilike(f"%{escaped}%", escape="\\")),
    ).limit(30))).all()
    # SQLite's built-in lower() is ASCII-only. Casefold in Python for Cyrillic search.
    if not users:
        candidates = (await db.scalars(select(User).where(User.organization_id == user.organization_id, User.role == "STUDENT", User.id != user.id))).all()
        needle = q.strip().lstrip("@").casefold()
        users = [u for u in candidates if needle in u.display_name.casefold() or needle in (u.username or "").casefold()][:30]
    return [public_user(item) for item in users]


@router.get("/users/{uid}")
async def user_profile(uid: int, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    require(user, "STUDENT")
    target = await db.get(User, uid)
    if not target or target.organization_id != user.organization_id or target.role != "STUDENT":
        fail("Профиль не найден", 404)
    reward_ids = [rid for rid in [target.active_title_id, target.active_frame_id, *target.showcase] if rid]
    rewards = (await db.scalars(select(Reward).where(Reward.id.in_(reward_ids)))).all()
    low, high = sorted([user.id, uid])
    friendship = await db.scalar(select(Friendship).where(Friendship.low_id == low, Friendship.high_id == high))
    my_subjects = (await db.scalars(select(GroupSubject.subject_id).where(GroupSubject.group_id == user.group_id))).all()
    their_subjects = (await db.scalars(select(GroupSubject.subject_id).where(GroupSubject.group_id == target.group_id))).all()
    return {**public_user(target), "rewards": [row(item) for item in rewards],
            "friendship": row(friendship) if friendship else None, "common_subject_ids": sorted(set(my_subjects) & set(their_subjects))}


@router.get("/friends")
async def friends(user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    require(user, "STUDENT")
    results = (await db.scalars(select(Friendship).where(or_(Friendship.low_id == user.id, Friendship.high_id == user.id)))).all()
    items = []
    for item in results:
        other = await db.get(User, item.high_id if item.low_id == user.id else item.low_id)
        if other.role != "STUDENT" or other.organization_id != user.organization_id:
            continue
        items.append({**row(item), "user": public_user(other), "incoming": item.requester_id != user.id})
    for duel in (await db.scalars(select(Duel).where(Duel.status == "PENDING", Duel.opponent_id == user.id))).all():
        if duel.created_at + timedelta(hours=24) <= now():
            duel.status = "EXPIRED"
            await notify(db, duel.challenger_id, "Время вызова истекло", "Друг не ответил в течение 24 часов", "/friends")
    return items


@router.post("/friends/{uid}")
async def request_friend(uid: int, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    require(user, "STUDENT")
    other = await db.get(User, uid)
    if uid == user.id or not other or other.role != "STUDENT" or other.organization_id != user.organization_id:
        fail("Нельзя отправить заявку этому пользователю", 403)
    low, high = sorted([user.id, uid])
    item = await db.scalar(select(Friendship).where(Friendship.low_id == low, Friendship.high_id == high))
    if item:
        if item.status == "PENDING" and item.requester_id != user.id:
            item.status = "ACCEPTED"
            await notify(db, uid, "Теперь вы друзья", user.display_name, f"/users/{user.id}")
        elif item.status == "REJECTED":
            item.status, item.requester_id = "PENDING", user.id
            await notify(db, uid, "Заявка в друзья", user.display_name, "/friends?tab=requests")
    else:
        item = Friendship(low_id=low, high_id=high, requester_id=user.id)
        db.add(item)
        await notify(db, uid, "Заявка в друзья", user.display_name, "/friends?tab=requests")
    await db.flush()
    return row(item)


@router.post("/friendships/{fid}/respond")
async def respond_friend(fid: int, data: s.Moderation, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    require(user, "STUDENT")
    item = await db.get(Friendship, fid)
    if not item or user.id not in (item.low_id, item.high_id) or item.requester_id == user.id:
        fail("Заявка не найдена", 404)
    if item.status != "PENDING":
        fail("Заявка уже обработана", 409)
    other = await db.get(User, item.requester_id)
    if other.organization_id != user.organization_id or other.role != "STUDENT":
        fail("Пользователь больше недоступен", 409)
    item.status = "ACCEPTED" if data.approve else "REJECTED"
    if data.approve:
        await notify(db, item.requester_id, "Теперь вы друзья", user.display_name, f"/users/{user.id}")
    return {"ok": True}


@router.delete("/friendships/{fid}")
async def remove_friend(fid: int, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    item = await db.get(Friendship, fid)
    if not item or user.id not in (item.low_id, item.high_id):
        fail("Связь не найдена", 404)
    await db.delete(item)
    return {"ok": True}


@router.get("/duels")
async def duels(user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    require(user, "STUDENT")
    items = (await db.scalars(select(Duel).where(or_(Duel.challenger_id == user.id, Duel.opponent_id == user.id)).order_by(Duel.id.desc()).limit(100))).all()
    result = []
    for item in items:
        if item.status == "PENDING" and item.created_at + timedelta(hours=24) <= now():
            item.status = "EXPIRED"
        await finish_duel(db, item)
        a, b = await duel_scores(db, item)
        challenger, opponent = await db.get(User, item.challenger_id), await db.get(User, item.opponent_id)
        result.append({**row(item), "challenger_score": a, "opponent_score": b,
                       "challenger": public_user(challenger), "opponent": public_user(opponent)})
    return result


@router.post("/duels", status_code=201)
async def challenge(data: s.DuelInput, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    require(user, "STUDENT")
    opponent = await db.get(User, data.opponent_id)
    if not opponent or opponent.role != "STUDENT" or opponent.organization_id != user.organization_id or opponent.id == user.id:
        fail("Соперник недоступен", 403)
    low, high = sorted([user.id, opponent.id])
    friendship = await db.scalar(select(Friendship).where(Friendship.low_id == low, Friendship.high_id == high, Friendship.status == "ACCEPTED"))
    if not friendship:
        fail("Вызывать на дуэль можно только друзей", 403)
    existing = await db.scalar(select(Duel).where(Duel.low_id == low, Duel.high_id == high, Duel.status.in_(["PENDING", "ACTIVE"])))
    if existing:
        if existing.status == "PENDING" and existing.created_at + timedelta(hours=24) <= now():
            existing.status = "EXPIRED"
            await db.flush()
        else:
            fail("Между вами уже есть дуэль или ожидающий вызов", 409)
    for uid in (user.id, opponent.id):
        if await duel_slots(db, uid) >= 3:
            fail("У одного из участников уже три активные дуэли", 409)
    if data.subject_id:
        for player in (user, opponent):
            if not player.group_id or not await db.get(GroupSubject, (player.group_id, data.subject_id)):
                fail("Оба участника должны изучать выбранный предмет", 403)
    duel = Duel(challenger_id=user.id, opponent_id=opponent.id, low_id=low, high_id=high,
                organization_id=user.organization_id, subject_id=data.subject_id, duration=data.duration)
    db.add(duel)
    await db.flush()
    await notify(db, opponent.id, "Тебя вызывают на дуэль!", user.display_name, "/friends")
    return row(duel)


@router.post("/duels/{did}/accept")
async def accept(did: int, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    require(user, "STUDENT")
    duel = await db.get(Duel, did)
    if not duel or duel.opponent_id != user.id:
        fail("Вызов не найден", 404)
    challenger = await db.get(User, duel.challenger_id)
    low, high = sorted([user.id, challenger.id])
    friendship = await db.scalar(select(Friendship).where(Friendship.low_id == low, Friendship.high_id == high))
    if not friendship or friendship.status != "ACCEPTED":
        fail("Для начала дуэли нужно оставаться друзьями", 409)
    await start_duel(db, duel, user)
    return row(duel)


@router.post("/duels/{did}/cancel")
async def cancel(did: int, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    duel = await db.get(Duel, did)
    if not duel or user.id not in (duel.challenger_id, duel.opponent_id):
        fail("Вызов не найден", 404)
    if duel.status != "PENDING":
        fail("Можно отменить только непринятый вызов", 409)
    duel.status = "CANCELLED" if user.id == duel.challenger_id else "DECLINED"
    other = duel.opponent_id if user.id == duel.challenger_id else duel.challenger_id
    await notify(db, other, "Вызов отменен" if duel.status == "CANCELLED" else "Вызов отклонен", user.display_name, "/friends")
    return {"ok": True}


@router.get("/duels/{did}/ledger")
async def duel_ledger(did: int, user: User = Depends(current_user), db: AsyncSession = Depends(session_dep)):
    duel = await db.get(Duel, did)
    if not duel or user.id not in (duel.challenger_id, duel.opponent_id):
        fail("Дуэль не найдена", 404)
    if not duel.starts_at:
        return []
    query = select(PointLedger).where(
        PointLedger.user_id.in_([duel.challenger_id, duel.opponent_id]),
        PointLedger.organization_id == duel.organization_id,
        PointLedger.source_kind.in_(["HOMEWORK", "EVENT"]),
        PointLedger.created_at >= duel.starts_at, PointLedger.created_at <= min(now(), duel.ends_at),
    )
    if duel.subject_id:
        query = query.where(PointLedger.subject_id == duel.subject_id)
    return [row(item) for item in (await db.scalars(query.order_by(PointLedger.created_at.desc()).limit(30))).all()]
