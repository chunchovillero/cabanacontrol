"""Stop/recover only the restored fictional DB; verify 503 and worker health."""

import argparse
import json
import re
import ssl
import subprocess
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="cabanacontrol-prestore")
    parser.add_argument("--docker-config")
    parser.add_argument("--docker-host")
    args = parser.parse_args()
    if not re.fullmatch(r"cabanacontrol-prestore-?[a-z0-9]*", args.project):
        raise SystemExit("Solo proyectos restaurados ficticios prestore.")
    docker = ["docker"]
    if args.docker_config:
        docker += ["--config", args.docker_config]
    if args.docker_host:
        docker += ["--host", args.docker_host]
    base = docker + [
        "compose",
        "--env-file",
        ".local-production/rehearsal.env",
        "-p",
        args.project,
        "-f",
        "compose.production.yaml",
    ]

    def command(*parts):
        return subprocess.run(
            base + list(parts), capture_output=True, cwd=ROOT, check=True
        ).stdout

    context = ssl.create_default_context(
        cafile=str(ROOT / ".local-production/tls/server.crt")
    )
    with httpx.Client(
        verify=context, base_url="https://localhost:25443", timeout=10, trust_env=False
    ) as client:
        assert client.get("/health/").status_code == 200
        marker = "fictional-sensitive-marker-never-log"
        assert client.get(f"/api/v1/properties/?email={marker}").status_code == 403
        try:
            command("stop", "db")
            response = client.get("/health/")
            assert response.status_code == 503
            assert response.json() == {
                "status": "unavailable",
                "database": "unavailable",
            }
            deadline = time.monotonic() + 160
            unhealthy = False
            while time.monotonic() < deadline:
                rows = [
                    json.loads(line)
                    for line in command("ps", "--all", "--format", "json").splitlines()
                    if line
                ]
                worker = next(
                    row for row in rows if row["Service"] == "whatsapp-worker"
                )
                if worker["Health"] == "unhealthy":
                    unhealthy = True
                    break
                time.sleep(5)
            assert unhealthy, "Worker no detectó interrupción de procesamiento"
        finally:
            command("start", "db")
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if client.get("/health/").status_code == 200:
                break
            time.sleep(2)
        assert client.get("/health/").status_code == 200
        # Existing containers may still report unhealthy until the next probe.
        # Compose --wait exits immediately for that state; observe recovery instead.
        deadline = time.monotonic() + 60
        recovered = False
        while time.monotonic() < deadline:
            rows = [
                json.loads(line)
                for line in command("ps", "--all", "--format", "json").splitlines()
                if line
            ]
            active = {
                row["Service"]: row.get("Health")
                for row in rows
                if row["Service"] in ("backend", "proxy", "whatsapp-worker", "db")
                and "-run-" not in row.get("Name", "")
                and not row.get("Name", "").startswith("p-")
            }
            if all(
                active.get(name) == "healthy"
                for name in ("backend", "proxy", "whatsapp-worker", "db")
            ):
                recovered = True
                break
            time.sleep(2)
        assert recovered, "Servicios no recuperados dentro del plazo"
        logs = command("logs", "--no-color", "backend", "proxy", "whatsapp-worker")
        assert marker.encode() not in logs
        print(
            json.dumps(
                {
                    "database_outage": "503",
                    "worker_outage": "unhealthy",
                    "recovery": "healthy",
                    "sensitive_log_marker": "absent",
                }
            )
        )


if __name__ == "__main__":
    main()
