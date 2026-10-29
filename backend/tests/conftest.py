import os
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import event, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Tests never use the application database or real MAX credentials.
os.environ.update(
    SECRET_KEY="test-secret-key-for-arena-only-000000000000",
    BOT_TOKEN="test-max-token",
    DEV_AUTH="true",
    SEED_DEMO="true",
    DATABASE_URL="sqlite+aiosqlite:///:memory:",
)

from app.db import session_dep  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base, User  # noqa: E402
from app.security import create_token  # noqa: E402
from app.seed import seed_demo  # noqa: E402


@pytest.fixture
async def arena(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}")

    @event.listens_for(engine.sync_engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as db:
        await seed_demo(db)
        await db.commit()
        users = {u.max_id: u for u in (await db.scalars(select(User))).all()}

    async def dependency():
        async with sessions() as db:
            await db.execute(text("BEGIN IMMEDIATE"))
            try:
                yield db
                await db.commit()
            except BaseException:
                await db.rollback()
                raise

    app.dependency_overrides[session_dep] = dependency
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield SimpleNamespace(
            client=client, sessions=sessions, users=users,
            auth=lambda max_id: {"Authorization": f"Bearer {create_token(users[max_id].id)}"},
        )
    app.dependency_overrides.clear()
    await engine.dispose()
