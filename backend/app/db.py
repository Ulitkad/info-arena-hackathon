from pathlib import Path

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .config import get_settings

settings = get_settings()
if settings.database_url.startswith("sqlite") and ":memory:" not in settings.database_url:
    Path(settings.database_url.split("///", 1)[1]).parent.mkdir(parents=True, exist_ok=True)
engine = create_async_engine(settings.database_url, connect_args={"timeout": 30})
Session = async_sessionmaker(engine, expire_on_commit=False)


@event.listens_for(engine.sync_engine, "connect")
def configure_sqlite(connection, _):
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()


async def session_dep():
    async with Session() as session:
        # SQLite has no SELECT FOR UPDATE. Serialize transactional business operations,
        # including checks + awards, across API requests and the scheduler.
        await session.execute(text("BEGIN IMMEDIATE"))
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise
