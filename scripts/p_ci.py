"""Complete fictional production rehearsal for CI on a clean checkout."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(*args, capture=False):
    return subprocess.run(list(args), cwd=ROOT, check=True, capture_output=capture)


def main():
    run(sys.executable, "scripts/prepare_p_rehearsal.py")
    base = [
        "docker",
        "compose",
        "--env-file",
        ".local-production/rehearsal.env",
        "-f",
        "compose.production.yaml",
    ]

    def compose(project, *args):
        run(*base, "-p", project, *args)

    source, target = "cabanacontrol-pcheck", "cabanacontrol-prestore"
    try:
        compose(source, "build")
        compose(source, "up", "-d", "--wait", "db")
        compose(source, "run", "--no-deps", "-T", "migrate")
        compose(
            source,
            "run",
            "--no-deps",
            "-T",
            "backend",
            "python",
            "manage.py",
            "seed_p_rehearsal",
        )
        compose(source, "up", "-d", "--wait", "backend", "whatsapp-worker", "proxy")
        run(sys.executable, "scripts/p_smoke.py")
        backup = run(
            sys.executable,
            "scripts/p_snapshot.py",
            "backup",
            "--project",
            source,
            capture=True,
        )
        metadata = json.loads(backup.stdout)
        compose(source, "up", "-d", "--wait", "backend", "whatsapp-worker", "proxy")
        run(sys.executable, "scripts/p_smoke.py", "--reset-mail")
        compose(source, "stop", "proxy", "backend", "whatsapp-worker")
        run(
            sys.executable,
            "scripts/p_snapshot.py",
            "restore",
            "--project",
            target,
            "--snapshot",
            metadata["snapshot"],
            "--key-file",
            metadata["key_file"],
        )
        compose(target, "up", "-d", "--wait", "backend", "whatsapp-worker", "proxy")
        run(sys.executable, "scripts/p_smoke.py", "--project", target)
        run(sys.executable, "scripts/p_verify_data.py", "--project", target)
        run(sys.executable, "scripts/p_monitor.py", "--project", target)
        subprocess.run(
            ["npm", "run", "test:e2e:production"], cwd=ROOT / "frontend", check=True
        )
    finally:
        # Preserve containers, artifacts, keys and volumes. Never delete existing data.
        for project in (source, target):
            subprocess.run(base + ["-p", project, "stop"], cwd=ROOT, check=False)


if __name__ == "__main__":
    main()
