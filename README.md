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

The application ships as **one image**, `ulitkad/info-arena:latest`.
It contains the built frontend, Nginx, FastAPI, the scheduler and the MAX bot.
Supervisor manages the processes as the unprivileged user UID 10001. The
container listens on HTTP port `8080`; the API health endpoint is `/api/health`.

The server only needs Docker Engine with Compose v2 and **two files in the same directory**:

```text
compose.yml
.env
```

No source checkout, Dockerfile, Python, Node.js or Nginx configuration is needed
on the server. The image must already be published. Obtain `compose.yml` and
copy the provided environment template:

```bash
cp .env.example .env
```

The image address `ulitkad/info-arena:latest` is fixed in `compose.yml`.
Set a persistent random `SECRET_KEY` of at least 32 characters in `.env`.
Generate a key with:

```bash
openssl rand -hex 32
chmod 600 .env
```

For **local hackathon review**, set `DEV_AUTH=true`, `SEED_DEMO=true`, leave
`BOT_TOKEN` empty and keep `WEB_BIND_ADDRESS=127.0.0.1`. The login page offers
student, teacher, manager and administrator demo users. Never expose demo
authentication publicly. Real MAX deployments need both demo flags set to
`false`, a bot token and a public HTTPS `BASE_APP_URL`.

Run from the directory containing the two files (public images require no login):

```bash
docker compose pull
docker compose up -d --wait
docker compose ps
curl --fail http://127.0.0.1:8080/api/health
docker compose logs -f app
```

Open <http://localhost:8080>. `WEB_PORT` controls the host port and
`WEB_BIND_ADDRESS` defaults to `127.0.0.1` (host-local access only). Set it to
`0.0.0.0` for direct remote access and configure your firewall. `BASE_APP_URL`
must match the address used to access the application.

Every startup applies Alembic migrations before starting the HTTP server. Failed
migrations prevent startup. The container runs exactly one API worker/scheduler,
one Nginx and one polling bot. The bot remains inactive without `BOT_TOKEN`.
All process logs go to `docker compose logs`. The healthcheck tests both the
frontend and API through Nginx, not external MAX connectivity.

SQLite and uploads persist in the named `database` and `uploads` volumes.
`docker compose down` keeps them; **do not use `down -v` for data you need**.
Keep the deployment directory/Compose project name unchanged to reuse the same
volumes. Before upgrades, back up SQLite consistently with the application
stopped or via the SQLite backup API, and back up uploads.

To update, wait for successful publication of the new `latest` image and run:

```bash
docker compose pull
docker compose up -d --wait
```

Keep `SECRET_KEY` unchanged. Each publication overwrites `latest`; record the
image digest to identify the submitted build. Image rollback does not roll back
database migrations. Updates can cause brief downtime.

The image serves HTTP only. A production Mini App needs an external HTTPS
reverse proxy with a valid certificate chain, WebSocket support for `/ws`, and
an HTTPS `BASE_APP_URL`. Keep the loopback binding for a host-level proxy. A
containerized proxy needs a shared Docker network or another reachable address:
its `127.0.0.1` does not refer to this application.

### Build the single image locally

From the repository root:

```bash
docker build -t info-arena:local .
sh docker/smoke-test.sh info-arena:local
```

The smoke test uses isolated demo volumes and a generated secret, never the
host `.env`. It checks frontend/SPA routes, API, all demo roles, hidden-file
blocking and a restart with persisted data, then removes the test volumes.

To use the local image with the deployment Compose file:

```bash
docker tag info-arena:local ulitkad/info-arena:latest
```

Run `docker compose up -d --wait --pull never`, without running
`docker compose pull`. This uses the local image instead of downloading `latest`.

### Publish using GitHub Actions

Create the public Docker Hub repository `ulitkad/info-arena`.
In GitHub → Settings → Secrets and variables → Actions, add:

- Repository secret `DOCKERHUB_TOKEN`: a Docker Hub PAT for `ulitkad` with Read & Write permissions.

On push to `main`, `.github/workflows/docker-publish.yml` runs the application
tests, builds the image, smoke-tests demo startup/restart on `amd64`, then
publishes one image for `linux/amd64` and `linux/arm64`. It does not test real MAX
connectivity. Pushes to `main`, `v*` tags and manual workflow runs publish
`ulitkad/info-arena:latest`. The username and tag are fixed in the workflow and
Compose; no additional GitHub Variables or image variables in `.env` are needed.

Submit `ulitkad/info-arena:latest`, `compose.yml`, a safe `.env.example` and demo
instructions. Do not share your working `.env`, tokens or databases. The Docker
Hub username in the image address is public, not a secret.

### Migrating from the previous Compose stack

The previous `compose.yaml` ran separate `api`, `web` and `bot` services. Stop it
**before** replacing the file, without `-v`, and back up your data. Keep the same
directory/project name and volumes, then start the new `compose.yml`. Never run
old and new stacks concurrently against the same SQLite database or polling
token. Do not leave the old `compose.yaml` next to `compose.yml`: Compose prefers it.

## Environment variables

The configuration file is resolved relative to the current working directory. Local development uses `backend/.env` when the API is started from `backend`; Compose passes the root `.env` to its services.

| Variable | Description |
| --- | --- |
| `WEB_PORT` | Host HTTP port, default `8080`. |
| `WEB_BIND_ADDRESS` | Default `127.0.0.1`; `0.0.0.0` exposes the port on all IPv4 interfaces. |
| `SECRET_KEY` | Required random JWT secret, at least 32 characters. Use the same value for all API instances. Changing it invalidates existing tokens. |
| `DATABASE_URL` | Local: `sqlite+aiosqlite:///./data/arena.db`. Compose fixes it to `sqlite+aiosqlite:////data/arena.db` to match the volume. |
| `UPLOAD_DIR` | Local: `uploads`. Compose fixes it to `/uploads` to match Nginx and the volume. |
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

    The single container starts the bot process automatically.

4. The bot uses long polling, not webhooks. Do not run multiple instances with the same token or leave an active webhook subscription. Remove an old webhook through the MAX API before enabling polling.
5. Send `/start` to the bot and open the arena using its button. A user without an assignment enters the pending state. The initial administrator creates an institution and selects "Invite manager" in its card. Pass the one-time link to the future manager; a username or ID is not required.
6. A manager creates subjects and groups, links them, and creates a one-time teacher invitation with the required workload. The workload of an accepted teacher can be edited separately. Students join through reusable group links, and their applications require approval.

When `BOT_USERNAME` is set, invitations use `https://max.ru/<name>?startapp=<token>`. MAX passes the token in the signed `start_param`. Without a bot name, the API returns a regular `BASE_APP_URL` link with `group_token` or `invite_token`. This is useful for local development, but a regular browser link does not provide MAX authentication by itself.

A new student group link revokes the previous one. Teacher and manager invitations are strictly one-time: after successful activation, a link cannot be used by another user or the same account again. Normal login after activation does not require an invitation link. Unused invitations can be revoked in the UI. Only administrators can invite managers.

### TLS and certificates

TLS verification is always enabled. If the system trust store does not trust the MAX API certificate, obtain the trusted root CA from an official source and set `MAX_CA_BUNDLE`. Never disable certificate verification.

If a custom CA is required, its PEM file must be accessible inside `app`. This
optional extension requires a certificate file in addition to the two deployment
files. Add a mount to `compose.yml`, for example:

```yaml
services:
  app:
    volumes:
      - ./certs/max-ca.pem:/certs/max-ca.pem:ro
    environment:
      MAX_CA_BUNDLE: /certs/max-ca.pem
```

The `environment` value takes precedence over an empty `MAX_CA_BUNDLE=` in `.env`.
Recreate the container after changing the CA:

```bash
docker compose up -d --force-recreate app
```

`ConnectTimeout` during a TLS handshake indicates a connection timeout, not a CA trust error. Check outbound HTTPS connectivity, DNS, and proxy settings from the host or container. Do not disable TLS verification.

### Bot diagnostics

In the deployed container, run:

```bash
docker compose exec app python -m app.bot_check
docker compose logs --since=10m app
```

The command checks token/CA configuration, DNS, direct TCP/TLS connectivity,
`GET /me` and `GET /subscriptions` using the bot's HTTP client. It **never calls
`/updates`**, consumes events, sends messages or deletes subscriptions. It does
not print the token or proxy environment values. Direct probes may fail on
proxy-only networks; the HTTP checks determine whether the bot can connect.

- A connection/TLS handshake timeout means connection setup did not finish.
  Check outbound TCP/443, routing, DNS and provider connectivity. Changing Caddy
  or opening application ingress ports will not fix this.
- Certificate verification failure means the trusted root CA or `MAX_CA_BUNDLE`
  mount needs fixing. Do not disable TLS verification.
- HTTP `401`: replace the invalid/revoked token and run
  `docker compose up -d --force-recreate --wait`; `restart` does not reload `.env`.
- Active webhooks conflict with polling. Remove subscriptions separately only
  when deliberately switching to polling; the bot never deletes them automatically.
- If checks pass but replies are missing, stop other polling instances with the
  same token (old Compose stacks/local processes) and send `/start` again.

Startup checks validate the token and subscriptions. Logs distinguish successful
polling (`MAX long polling connected successfully`), received events
(`MAX received ... updates`) and sent greetings (`MAX greeting sent successfully`).
Supervisor's `bot entered RUNNING` only means the process is alive, not that MAX
is reachable. The Mini App healthcheck does not test bot connectivity either.

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
uv run --directory backend python -m pytest -q
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
Dockerfile            single image: frontend, API, Nginx and bot
docker/               process/Nginx configuration, healthcheck and smoke test
compose.yml           one app service and persistent volumes
nginx/default.conf    previous split frontend build configuration
```
