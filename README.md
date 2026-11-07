# Info Arena

[Русская версия](README.ru.md)

Info Arena is a MAX bot and Mini App for gamified learning. It provides assignments, events, Battlepass tracks, rewards, friends, and duels.

The frontend uses Vue 3, Vite, Pinia, and Vue Router. The backend uses FastAPI, SQLAlchemy 2, SQLite, and Alembic.

## Features

- **Student:** join an institution through an invitation, submit and revise assignments, register for events, use institution and subject Battlepass tracks, collect achievements, add friends, and start duels.
- **Teacher:** create and grade assignments, manage events, and work with students within assigned subject-group workloads.
- **Manager:** manage groups, subjects, applications, teachers, workloads, invitations, and rewards for an institution.
- **Administrator:** manage institutions, assign managers, and administer a selected institution.
- In-app and WebSocket notifications. Background jobs process deadlines and finish duels every 30 seconds.

## Requirements

The commands below assume Bash on a Debian-based Linux distribution and are run from the repository root.

- Python 3.11 or newer
- uv 0.9 or newer
- Node.js 22.12 or newer, or Node.js 24 LTS
- npm
- Docker Engine and Docker Compose v2 for container deployment

On a minimal Debian or Ubuntu host, install the Python prerequisites with:

```bash
sudo apt update
sudo apt install -y python3 ca-certificates curl
```

Install a supported Node.js version using the method appropriate for your distribution. Verify the installed versions before continuing:

```bash
python3 --version
node --version
npm --version
```

## Local development without MAX

Install the backend dependencies with `uv` (it creates and manages
`backend/.venv` from `pyproject.toml` and `uv.lock`):

```bash
uv sync --directory backend
```

Create `backend/.env` with local settings. Do not use the Docker `/data` paths in this file.

```dotenv
SECRET_KEY=REPLACE_WITH_A_RANDOM_SECRET_AT_LEAST_32_CHARACTERS_LONG
DATABASE_URL=sqlite+aiosqlite:///./data/arena.db
UPLOAD_DIR=uploads
BASE_APP_URL=http://localhost:5173
DEV_AUTH=true
SEED_DEMO=true
```

Generate a suitable secret with:

```bash
uv run --directory backend python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Start the API in the first terminal:

```bash
uv run --directory backend alembic upgrade head
uv run --directory backend uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Start the frontend in a second terminal from the repository root:

```bash
cd frontend
npm ci
npm run dev -- --port 5173 --strictPort
```

Open <http://localhost:5173>. With demo authentication enabled, the login page provides demo users for the student, teacher, manager, and administrator roles. Sign out from the header to switch users.

Useful endpoints:

- API health check: <http://localhost:8000/api/health>
- Swagger UI: <http://localhost:8000/docs>
- Vite proxies `/api`, `/media`, and `/ws` to the API, so a separate CORS configuration is not required for local development.

Demo authentication is enabled only when both `DEV_AUTH=true` and `SEED_DEMO=true` are set. It exposes every demo role and must not be enabled on a public server. Use a separate database for real data. Process environment variables override values from `.env`.

## Docker Compose deployment

Install Docker Engine and the Compose v2 plugin for your Debian-based distribution. From the repository root:

```bash
cp .env.example .env
```

Set a random `SECRET_KEY` in `.env`. For a demo deployment, set both `DEV_AUTH=true` and `SEED_DEMO=true`. Start the stack:

```bash
docker compose up --build -d
docker compose logs -f api web bot
```

The application is available at <http://localhost> and the API health check is at <http://localhost/api/health>.

Set the public port with `WEB_PORT` in the root `.env` (default: `80`). For example, with `WEB_PORT=8080`, use <http://localhost:8080> and set `BASE_APP_URL` to the same URL. The port inside the container remains `80`.

Services:

| Service | Description |
| --- | --- |
| `api` | Applies migrations, runs FastAPI, and runs the scheduler in one worker. |
| `web` | Serves the built frontend through Nginx and proxies the API and WebSocket traffic on port 80. |
| `bot` | Runs one MAX long-polling instance. It remains inactive when `BOT_TOKEN` is not set. |

SQLite data and uploaded files are stored in the named `database` and `uploads` volumes. `docker compose down` keeps these volumes. Do not use `docker compose down -v` if the data is needed. Before upgrades, create a consistent backup of the SQLite database with the API stopped, or use the SQLite backup API, and back up the uploads directory.

The bundled Nginx configuration is HTTP-only. A production Mini App requires an external HTTPS reverse proxy or load balancer with a valid certificate chain. Proxy `/ws`, set the public HTTPS URL in `BASE_APP_URL`, and restrict direct access to the HTTP port.

## Environment variables

The configuration file is resolved relative to the current working directory. Local development uses `backend/.env` when the API is started from `backend`; Compose passes the root `.env` to its services.

| Variable | Description |
| --- | --- |
| `SECRET_KEY` | Required random JWT secret, at least 32 characters. Use the same value for all API instances. Changing it invalidates existing tokens. |
| `DATABASE_URL` | Local: `sqlite+aiosqlite:///./data/arena.db`. Docker: `sqlite+aiosqlite:////data/arena.db`. |
| `UPLOAD_DIR` | Local: `uploads`. Compose overrides it to `/uploads` for the API. |
| `BASE_APP_URL` | Public root URL of the Mini App without a trailing slash. Local default: `http://localhost:5173`. |
| `BOT_TOKEN` | MAX bot token. Keep it on the server and out of the frontend. |
| `BOT_USERNAME` | Bot name from `https://max.ru/<name>`, without `@` or the URL. Used in launch links and the bot button. |
| `ADMIN_MAX_ID` | Numeric MAX ID of the initial administrator. The role is granted after a verified MAX login. |
| `BOT_API_URL` | MAX API base URL. Default: `https://platform-api2.max.ru`. |
| `MAX_CA_BUNDLE` | Optional path to a trusted PEM CA bundle that supplements the client's system trust store. |
| `DEV_AUTH` | Defaults to `false`. Local development only. |
| `SEED_DEMO` | Defaults to `false`. Requires `DEV_AUTH=true` and creates demo data when the API starts. |

## Connecting MAX

1. Create a bot in [MAX for Business](https://business.max.ru/) and copy its token. Set `BOT_TOKEN`, `BOT_USERNAME`, `ADMIN_MAX_ID`, and `BASE_APP_URL`.
2. Publish the Mini App over HTTPS and configure this URL in the bot settings. Disable the demo flags and use a clean database with migrations applied.
3. Start the API and frontend. For local development, start the bot separately from `backend`:

   ```bash
   uv run --directory backend python -m app.bot
   ```

   Compose starts the bot service automatically.

4. The bot uses long polling, not webhooks. Do not run multiple instances with the same token or leave an active webhook subscription. Remove an old webhook through the MAX API before enabling polling.
5. Send `/start` to the bot and open the arena using its button. A user without an assignment enters the pending state. The initial administrator creates an institution and selects "Invite manager" in its card. Pass the one-time link to the future manager; a username or ID is not required.
6. A manager creates subjects and groups, links them, and creates a one-time teacher invitation with the required workload. The workload of an accepted teacher can be edited separately. Students join through reusable group links, and their applications require approval.

When `BOT_USERNAME` is set, invitations use `https://max.ru/<name>?startapp=<token>`. MAX passes the token in the signed `start_param`. Without a bot name, the API returns a regular `BASE_APP_URL` link with `group_token` or `invite_token`. This is useful for local development, but a regular browser link does not provide MAX authentication by itself.

A new student group link revokes the previous one. Teacher and manager invitations are strictly one-time: after successful activation, a link cannot be used by another user or the same account again. Normal login after activation does not require an invitation link. Unused invitations can be revoked in the UI. Only administrators can invite managers.

### TLS and certificates

TLS verification is always enabled. If the system trust store does not trust the MAX API certificate, obtain the trusted root CA from an official source and set `MAX_CA_BUNDLE`. Never disable certificate verification.

For Compose, the PEM file must be available inside the `bot` container. Create a local `compose.override.yaml`, for example:

```yaml
services:
  bot:
    volumes:
      - ./certs/max-ca.pem:/certs/max-ca.pem:ro
    environment:
      MAX_CA_BUNDLE: /certs/max-ca.pem
```

The `environment` value in the override takes precedence over an empty `MAX_CA_BUNDLE=` in `.env`. Recreate the container after changing the CA or override file:

```bash
docker compose up -d --force-recreate bot
```

`ConnectTimeout` during a TLS handshake indicates a connection timeout, not a CA trust error. Check outbound HTTPS connectivity, DNS, and proxy settings from the host or container. Do not disable TLS verification.

### Bot diagnostics

- `GET /updates -> 200` confirms a successful HTTPS request and access to updates. A later `POST /messages -> 404` is a separate send error. The bot logs the MAX HTTP status, `code`, and `message` without logging the token or update contents.
- Direct replies (`bot_started` and messages with `chat_type=dialog`) use the user ID. Group replies use the chat ID. Do not put a user ID in `chat_id` for a group message.
- Permanent `4xx` send errors are skipped so one event cannot block the queue. For `401`, `408`, `429`, network errors, and `5xx`, the marker is not advanced and the request is retried. A retried batch can duplicate greetings that were already sent.
- Requests from scanners for `.env` are unrelated to MAX. The SPA fallback can return the application HTML with `200` for an unknown path; that does not indicate a file leak. Nginx explicitly returns `404` for hidden files and directories.

### Authentication and Bridge

The frontend sends the raw `window.WebApp.initData` to the server. The server verifies the two-stage HMAC-SHA256 signature, one-hour expiration, duplicate parameters, and user ID. `initDataUnsafe` is not used for authentication. After login, the JWT is stored in `sessionStorage`. WebSocket connections use a separate one-minute ticket instead of placing the token in the URL.

The official MAX Bridge (`https://st.max.ru/js/max-web-app.js`) is enabled. The application supports BackButton, verified phone numbers, and attachment downloads. In a regular browser, attachments use regular links; MAX requires HTTPS for downloads.

Official references: [Bridge](https://dev.max.ru/docs/webapps/bridge/), [validation](https://dev.max.ru/docs/webapps/validation/), [Mini Apps](https://dev.max.ru/docs/webapps/introduction/), [Bot API](https://dev.max.ru/docs-api/).

## Checks

Run backend checks from the repository root:

```bash
PYTHONPATH=backend uv run --directory backend pytest -q
uv run --directory backend ruff check app migrations tests
```

Run frontend checks from `frontend`:

```bash
cd frontend
npm test
npm run build
```

Backend tests use a temporary SQLite database and test credentials. They do not call MAX or modify the working database. They cover authentication, signatures, the demo seeder, idempotent rewards, concurrent assignment grading, revisions, invitations, moderation, events, duels, and migration cycles. Frontend tests cover session isolation after logout and re-login.

## Constraints

- A duel counts only academic assignment and event points recorded inside its time window and institution. PvP bonuses do not affect the duel score. Rewards and points are idempotent.
- API dates include time zones and are normalized to UTC. The UI displays local time.
- SQLite uses WAL mode and serialized business transactions. This prototype is designed for one API worker and one scheduler, not horizontal scaling.
- Each material can have up to 10 attachments, each up to 20 MB. Allowed extensions are restricted. Files are served through unpredictable `/media/...` URLs without separate download authorization. Do not store confidential documents. Production use requires ACLs or signed URLs, antivirus scanning, and cleanup of unused uploads.
- Notifications are implemented inside the Mini App. The bot sends a greeting and a launch button, but it does not send every notification to MAX direct messages.
- Background jobs, CDN avatars/images, and the MAX Bridge require external network access. Real MAX client and CA trust must be tested with a configured bot.
- The initial Alembic migration is generated from the current model metadata. Before changing the schema, freeze the baseline and add independent versioned migrations.

## Repository layout

```text
backend/app/          models, API routes, business rules, bot, seeder, and scheduler
backend/migrations/   Alembic migrations
backend/tests/        integration and security tests
frontend/src/         Vue components, role pages, router, and Pinia stores
frontend/tests/       session lifecycle tests
nginx/default.conf    HTTP proxy and frontend/upload serving
compose.yaml          API, bot, web, and volumes
```
