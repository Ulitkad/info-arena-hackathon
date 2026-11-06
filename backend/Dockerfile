# syntax=docker/dockerfile:1

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

COPY --link requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    python -m pip install -r requirements.txt

RUN useradd --uid 10001 --create-home --no-log-init arena \
    && mkdir --parents /data /uploads \
    && chown arena:arena /data /uploads

COPY --link --chown=10001:10001 . ./
USER arena
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"]
