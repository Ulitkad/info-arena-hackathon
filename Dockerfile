# syntax=docker/dockerfile:1

FROM node:24-alpine AS frontend-build
WORKDIR /frontend
COPY --link frontend/package.json frontend/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm,sharing=locked npm ci
COPY --link frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    DATABASE_URL=sqlite+aiosqlite:////data/arena.db \
    UPLOAD_DIR=/uploads
WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates nginx supervisor \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /uvx /bin/
COPY --link backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    uv sync --frozen --no-dev --no-install-project

RUN useradd --uid 10001 --create-home --no-log-init arena \
    && mkdir --parents /data /uploads \
    && chown arena:arena /data /uploads
COPY --link backend/app/ ./app/
COPY --link backend/migrations/ ./migrations/
COPY --link backend/alembic.ini ./
COPY --from=frontend-build /frontend/dist/ /usr/share/nginx/html/
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/supervisord.conf /etc/supervisor/arena.conf
COPY docker/entrypoint.sh docker/start-bot.py docker/healthcheck.py /opt/arena/

USER arena
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
    CMD ["python", "/opt/arena/healthcheck.py"]
ENTRYPOINT ["/bin/sh", "/opt/arena/entrypoint.sh"]
