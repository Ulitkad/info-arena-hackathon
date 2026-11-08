#!/bin/sh
# Uses isolated, automatically cleaned-up demo volumes; never reads the host .env.
set -eu

image=${1:-info-arena:local}
name="info-arena-smoke-$$"

cleanup() {
    docker logs "$name" || true
    docker rm -f "$name" || true
    docker volume rm "$name-data" "$name-uploads" || true
}
trap cleanup EXIT

docker run -d --name "$name" \
    -e SECRET_KEY="$(openssl rand -hex 32)" \
    -e DEV_AUTH=true -e SEED_DEMO=true -e BOT_TOKEN= \
    -v "$name-data:/data" -v "$name-uploads:/uploads" \
    "$image"

wait_ready() {
    attempt=0
    until docker exec "$name" python /opt/arena/healthcheck.py; do
        attempt=$((attempt + 1))
        if [ "$attempt" -ge 60 ]; then
            echo "Container did not become ready" >&2
            exit 1
        fi
        sleep 2
    done
}

check_routes() {
    docker exec -i "$name" python - <<'PY'
import json
import urllib.error
import urllib.request

base = "http://127.0.0.1:8080"
for path in ("/", "/profile", "/api/health", "/api/config"):
    with urllib.request.urlopen(base + path, timeout=5) as response:
        assert response.status == 200, path
for path in ("/.env", "/.git/config"):
    try:
        urllib.request.urlopen(base + path, timeout=5)
    except urllib.error.HTTPError as exc:
        assert exc.code == 404, path
    else:
        raise AssertionError(f"Hidden path is accessible: {path}")
for persona in ("student", "teacher", "manager", "admin"):
    request = urllib.request.Request(
        base + "/api/auth/dev",
        data=json.dumps({"persona": persona}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        token = json.load(response)["access_token"]
    request = urllib.request.Request(base + "/api/me", headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(request, timeout=5) as response:
        assert json.load(response)["role"] == persona.upper(), persona
print("Frontend, SPA routes, hidden paths and all demo roles: OK")
PY
}

wait_ready
check_routes
docker exec "$name" sh -c 'test "$(id -u)" = 10001 && test -s /data/arena.db && touch /uploads/smoke-persisted'
docker restart --time 60 "$name"
wait_ready
check_routes
docker exec "$name" test -f /uploads/smoke-persisted
echo "Single-image startup and persistent restart: OK"
