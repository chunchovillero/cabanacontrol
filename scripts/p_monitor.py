"""Read-only local service/queue probe. Exit nonzero so a scheduler can alert."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--docker-config")
    parser.add_argument("--docker-host")
    args = parser.parse_args()
    if not re.fullmatch(r"cabanacontrol-p(?:check|restore)-?[a-z0-9]*", args.project):
        raise SystemExit("Probe local limitado a los proyectos ficticios P.")
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
    result = subprocess.run(
        base + ["ps", "--all", "--format", "json"],
        capture_output=True,
        cwd=ROOT,
        check=True,
    )
    # Compose v2 emits one JSON object per line.
    rows = [json.loads(line) for line in result.stdout.splitlines() if line]
    services = {
        row["Service"]: {"state": row["State"], "health": row.get("Health", "")}
        for row in rows
        if not row.get("Name", "").startswith("p-")
        and "-run-" not in row.get("Name", "")
    }
    healthy = all(
        services.get(name) == {"state": "running", "health": "healthy"}
        for name in ("db", "backend", "whatsapp-worker", "proxy")
    )
    report = {"services": services, "healthy": healthy}
    if healthy:
        code = (
            "import json; from django.db.models import Count; "
            "from apps.whatsapp.models import OutboxJob,WebhookEvent; "
            "print(json.dumps({'outbox':list(OutboxJob.objects.values('state').annotate(count=Count('id'))),"
            "'events':list(WebhookEvent.objects.values('state').annotate(count=Count('id')))}))"
        )
        queues = subprocess.run(
            base
            + ["exec", "-T", "backend", "python", "manage.py", "shell", "-c", code],
            capture_output=True,
            cwd=ROOT,
            check=True,
        )
        # manage.py shell may emit an import notice before the JSON report.
        report["queues"] = json.loads(queues.stdout.splitlines()[-1])
    print(json.dumps(report))
    return 0 if healthy else 1


if __name__ == "__main__":
    sys.exit(main())
