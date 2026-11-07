"""User queries shared by authentication and social endpoints."""

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def by_max_id(self, max_id: int):
        return await self.db.scalar(select(User).where(User.max_id == max_id))

    async def by_lookup(self, value: str):
        value = value.strip()
        conditions = [func.lower(User.username) == value.lstrip("@").lower()]
        if value.lstrip("+").isdigit():
            conditions.extend([User.max_id == int(value.lstrip("+")), User.phone == value.lstrip("+")])
        return (await self.db.scalars(select(User).where(or_(*conditions)).limit(2))).all()
