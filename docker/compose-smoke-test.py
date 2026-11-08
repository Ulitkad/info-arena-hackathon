"""CI check: deploy the tested image with only compose.yml and .env in a new directory."""

import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile


def main():
    root = Path(__file__).resolve().parents[1]
    image = sys.argv[1] if len(sys.argv) > 1 else "info-arena:smoke"
    subprocess.run(["docker", "tag", image, "ulitkad/info-arena:latest"], check=True)
    base = Path(os.environ.get("RUNNER_TEMP", "/tmp/opencode"))
    base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="arena-compose-", dir=base) as directory:
        target = Path(directory)
        shutil.copyfile(root / "compose.yml", target / "compose.yml")
        template = (root / ".env.example").read_text()
        template = template.replace("replace-with-at-least-32-random-characters", secrets.token_hex(32))
        # Publish to an ephemeral loopback port, avoiding collisions with host services.
        template = template.replace("WEB_PORT=8080", "WEB_PORT=0")
        (target / ".env").write_text(template)
        (target / ".env").chmod(0o600)
        environment = os.environ.copy()
        for line in template.splitlines():
            if line and not line.startswith("#"):
                environment.pop(line.partition("=")[0], None)
        compose = ["docker", "compose", "--project-name", target.name]

        def run(*args, **kwargs):
            return subprocess.run([*compose, *args], cwd=target, env=environment, check=True, **kwargs)

        assert {p.name for p in target.iterdir()} == {"compose.yml", ".env"}
        config = json.loads(run("config", "--format", "json", capture_output=True, text=True).stdout)
        assert set(config["services"]) == {"app"}
        assert "build" not in config["services"]["app"]
        assert config["services"]["app"]["image"] == "ulitkad/info-arena:latest"
        try:
            run("up", "-d", "--pull", "never", "--wait", "--wait-timeout", "180")
            run("exec", "-T", "app", "python", "/opt/arena/healthcheck.py")
            run("exec", "-T", "app", "python", "-c", """
import hashlib
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from app.bot import ca_bundle, tls_context
from app.config import get_settings

settings = get_settings()
assert not settings.bot_token and not settings.dev_auth and not settings.seed_demo
assert not Path('/app/.env').exists()
bundle = Path(ca_bundle(settings))
assert bundle.is_file()
digest = hashlib.sha256(ssl.PEM_cert_to_DER_cert(bundle.read_text())).hexdigest()
assert digest == 'd26d2d0231b7c39f92cc738512ba54103519e4405d68b5bd703e9788ca8ecf31'
assert any(hashlib.sha256(c).hexdigest() == digest for c in tls_context(settings).get_ca_certs(binary_form=True))
request = urllib.request.Request('http://127.0.0.1:8080/api/auth/dev',
    data=b'{"persona":"admin"}', headers={'Content-Type': 'application/json'})
try:
    urllib.request.urlopen(request, timeout=5)
except urllib.error.HTTPError as exc:
    assert exc.code == 404
else:
    raise AssertionError('Demo auth must be disabled by default')
print('Two-file deployment, bundled CA and disabled public demo: OK')
""")
        finally:
            # This project and its volumes exist only for this isolated test.
            try:
                run("logs", "--no-color")
            finally:
                run("down", "--volumes", "--remove-orphans")


if __name__ == "__main__":
    main()
