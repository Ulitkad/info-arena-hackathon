"""Notification query primitives."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Notification


class NotificationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def page(self, user_id: int, before: int | None = None, limit: int = 100):
        query = select(Notification).where(Notification.user_id == user_id)
        if before:
            query = query.where(Notification.id < before)
        return (await self.db.scalars(query.order_by(Notification.id.desc()).limit(limit))).all()

    async def unread_count(self, user_id: int):
        return await self.db.scalar(select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id, Notification.read.is_(False),
        ))
