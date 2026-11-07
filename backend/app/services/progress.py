"""Points, progress tracks and reward unlocking use-cases."""

from sqlalchemy import select

from ..models import GroupSubject, Inventory, PointLedger, Progress, Reward, User
from ..frame_styles import DEFAULT_FRAME_STYLE
from ..security import fail
from .achievements import evaluate_achievements
from .notifications import notify


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
        ("На старте", "TITLE", 5, "star", None),
        ("Небесная рамка", "FRAME", 10, "shield", "skyline"),
        ("Исследователь", "TITLE", 35, "award", None),
        ("Облачная рамка", "FRAME", 50, "sparkles", "aurora"),
        ("Легенда арены", "TITLE", 100, "crown", None),
    ]
    for name, kind, threshold, icon, frame_style in definitions:
        db.add(Reward(organization_id=organization_id, subject_id=subject_id, name=name, kind=kind,
                      threshold=threshold, icon=icon, frame_style=frame_style or (DEFAULT_FRAME_STYLE if kind == "FRAME" else None)))
    await db.flush()


async def unlock_rewards(db, user, subject_id=None):
    progress_scope = "general" if subject_id is None else f"subject:{subject_id}"
    points = await db.scalar(select(Progress.points).where(
        Progress.user_id == user.id, Progress.scope == progress_scope)) or 0
    rewards = (await db.scalars(select(Reward).where(
        Reward.organization_id == user.organization_id, Reward.subject_id == subject_id,
        Reward.special.is_(False), Reward.threshold <= points,
    ))).all()
    for reward in rewards:
        if not await db.get(Inventory, (user.id, reward.id)):
            db.add(Inventory(user_id=user.id, reward_id=reward.id))
            await notify(db, user.id, "Новый уровень!", f"Открыта награда «{reward.name}»",
                         f"/battlepass/{subject_id or 'general'}")
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
    await evaluate_achievements(db, user)
    return True
