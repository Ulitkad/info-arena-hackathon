import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from .config import get_settings
from .db import Session, engine
from .jobs import run_jobs
from .routes import auth, learning, manage, notifications, social

logging.basicConfig(level=logging.INFO)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    if settings.seed_demo:
        from .seed import seed_demo
        async with Session() as db:
            await db.execute(text("BEGIN IMMEDIATE"))
            await seed_demo(db)
            await db.commit()
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(run_jobs, "interval", seconds=30, max_instances=1, coalesce=True, misfire_grace_time=60)
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        await engine.dispose()


app = FastAPI(title="Инфо Арена", version="1.0.0", lifespan=lifespan)
for router in (auth.router, manage.router, learning.router, social.router, notifications.router):
    app.include_router(router)
app.mount("/media", StaticFiles(directory=settings.upload_dir, check_dir=False), name="media")


@app.exception_handler(IntegrityError)
async def constraint_error(request, exc):
    logging.getLogger(__name__).warning("Database constraint violation on %s", request.url.path)
    return JSONResponse(status_code=409, content={"detail": "Изменение конфликтует с существующими данными. Обновите страницу и повторите."})


@app.get("/api/health")
async def health():
    async with Session() as db:
        await db.execute(text("SELECT 1"))
    return {"status": "ok"}
