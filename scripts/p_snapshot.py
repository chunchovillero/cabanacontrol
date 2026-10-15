"""Encrypted backup/restore rehearsal. Never operate on the development project.

Uses subprocess argument lists (no shell), no deletion and no overwrite. This local
single-host rehearsal is deliberately limited to fictional data and small backups.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
import uuid
from pathlib import Path

from cryptography.fernet import Fernet

ROOT = Path(__file__).resolve().parent.parent
LOCAL = ROOT / ".local-production"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["backup", "restore"])
    parser.add_argument("--project", required=True)
    parser.add_argument("--env-file", default=".local-production/rehearsal.env")
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--key-file", type=Path)
    parser.add_argument("--docker-config")
    parser.add_argument("--docker-host")
    args = parser.parse_args()
    if not re.fullmatch(r"cabanacontrol-p(?:check|restore)-?[a-z0-9]*", args.project):
        raise SystemExit("Solo proyectos de ensayo pcheck/prestore explícitos.")
    env_path = (ROOT / args.env_file).resolve()
    if not env_path.is_relative_to(LOCAL.resolve()):
        raise SystemExit("El entorno debe estar en .local-production.")
    values = dict(
        line.split("=", 1)
        for line in env_path.read_text(encoding="utf-8").splitlines()
        if "=" in line and not line.startswith("#")
    )
    if (
        values.get("P_REHEARSAL") != "true"
        or values.get("POSTGRES_DB") != "cabanacontrol_pcheck"
    ):
        raise SystemExit("Requiere configuración ficticia protegida.")
    for flag in (
        "AI_ENABLED",
        "WHATSAPP_REAL_ENABLED",
        "AI_TEST_PROVIDER",
        "WHATSAPP_TEST_PROVIDER",
    ):
        if values.get(flag) != "false":
            raise SystemExit("No se permiten proveedores en el ensayo.")
    docker = ["docker"]
    if args.docker_config:
        docker += ["--config", args.docker_config]
    if args.docker_host:
        docker += ["--host", args.docker_host]
    base = docker + [
        "compose",
        "--env-file",
        str(env_path),
        "-p",
        args.project,
        "-f",
        str(ROOT / "compose.production.yaml"),
    ]
    # Compose gives host environment priority over --env-file; keep this guarded
    # rehearsal configuration authoritative for all its declared variables.
    environment = {**os.environ, **values}

    def command(*parts, data=None):
        result = subprocess.run(
            base + list(parts),
            input=data,
            capture_output=True,
            cwd=ROOT,
            env=environment,
            check=False,
        )
        if result.returncode:
            raise RuntimeError(
                "Operación Docker fallida; servicios conservados. Revisar su estado."
            )
        return result.stdout

    def sql(query):
        return command(
            "exec",
            "-T",
            "db",
            "psql",
            "-U",
            values["POSTGRES_USER"],
            "-d",
            values["POSTGRES_DB"],
            "-At",
            "-c",
            query,
        ).strip()

    started = time.monotonic()
    if args.action == "backup":
        if args.snapshot or args.key_file:
            raise SystemExit(
                "Backup genera rutas nuevas; no acepta destinos existentes."
            )
        identifier = uuid.uuid4().hex
        snapshot = LOCAL / "backups" / identifier
        snapshot.mkdir(parents=True, exist_ok=False)
        key_dir = LOCAL / "keys"
        key_dir.mkdir(exist_ok=True)
        key_file = key_dir / f"{identifier}.key"
        key = Fernet.generate_key()
        with key_file.open("xb") as output:
            output.write(key)
        key_file.chmod(0o600)
        # Stop every application writer, wait for graceful shutdown and keep DB online.
        # On failure stay stopped: never reopen a potentially partial maintenance operation.
        command("stop", "proxy", "whatsapp-worker", "backend")
        database = command(
            "exec",
            "-T",
            "db",
            "pg_dump",
            "-U",
            values["POSTGRES_USER"],
            "-d",
            values["POSTGRES_DB"],
            "--format=custom",
            "--no-owner",
            "--no-privileges",
        )
        media = command(
            "run",
            "--no-deps",
            "-T",
            "--name",
            f"p-backup-{identifier}",
            "backend",
            "python",
            "-c",
            "import sys,tarfile; t=tarfile.open(fileobj=sys.stdout.buffer,mode='w|'); "
            "t.add('/var/lib/cabanacontrol/media',arcname='media'); t.close()",
        )
        manifest = {"version": 1, "source_project": args.project, "files": {}}
        cipher = Fernet(key)
        for filename, content in (("database.dump", database), ("media.tar", media)):
            encrypted = cipher.encrypt(content)
            (snapshot / f"{filename}.fernet").write_bytes(encrypted)
            manifest["files"][filename] = {
                "plain_sha256": digest(content),
                "encrypted_sha256": digest(encrypted),
            }
        manifest["seconds"] = round(time.monotonic() - started, 2)
        (snapshot / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "snapshot": str(snapshot.relative_to(ROOT)),
                    "key_file": str(key_file.relative_to(ROOT)),
                    "seconds": manifest["seconds"],
                    "writers": "stopped",
                }
            )
        )
    else:
        if not args.project.startswith("cabanacontrol-prestore"):
            raise SystemExit("Restaurar requiere un proyecto prestore nuevo.")
        if not args.snapshot or not args.key_file:
            raise SystemExit("Indica snapshot y clave custodiada por separado.")
        snapshot = args.snapshot.resolve()
        key_file = args.key_file.resolve()
        if not snapshot.is_relative_to(LOCAL.resolve()) or not key_file.is_relative_to(
            LOCAL.resolve()
        ):
            raise SystemExit("Solo artefactos locales del ensayo.")
        manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
        if manifest["source_project"] == args.project or manifest["version"] != 1:
            raise SystemExit("El destino debe ser distinto al origen.")
        cipher = Fernet(key_file.read_bytes())
        content = {}
        for filename in ("database.dump", "media.tar"):
            encrypted = (snapshot / f"{filename}.fernet").read_bytes()
            if digest(encrypted) != manifest["files"][filename]["encrypted_sha256"]:
                raise SystemExit("Copia alterada; restauración rechazada.")
            content[filename] = cipher.decrypt(encrypted)
            if digest(content[filename]) != manifest["files"][filename]["plain_sha256"]:
                raise SystemExit("Integridad inválida.")
        command("up", "-d", "--wait", "db")
        if sql("SELECT count(*) FROM pg_tables WHERE schemaname='public'") != b"0":
            raise SystemExit("Base destino no vacía; no se sobrescribirá.")
        identifier = uuid.uuid4().hex
        command(
            "run",
            "--no-deps",
            "-T",
            "--name",
            f"p-empty-{identifier}",
            "backend",
            "python",
            "-c",
            "from pathlib import Path\n"
            "if any(Path('/var/lib/cabanacontrol/media').iterdir()):\n"
            "    raise RuntimeError('El volumen destino no está vacío')",
        )
        # No --clean: all objects must be new. Atomic DB restore; media stays offline on failure.
        command(
            "exec",
            "-T",
            "db",
            "pg_restore",
            "-U",
            values["POSTGRES_USER"],
            "-d",
            values["POSTGRES_DB"],
            "--exit-on-error",
            "--single-transaction",
            "--no-owner",
            "--no-privileges",
            data=content["database.dump"],
        )
        code = (
            "import io,sys,tarfile\nfrom pathlib import Path\n"
            "p=Path('/var/lib/cabanacontrol/media')\n"
            "if any(p.iterdir()): raise RuntimeError('Destino no vacío')\n"
            "t=tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read()))\n"
            "members=t.getmembers()\n"
            "if not all((m.name=='media' or m.name.startswith('media/')) "
            "and not m.issym() and not m.islnk() and (m.isfile() or m.isdir()) for m in members):\n"
            "    raise RuntimeError('Archivo inválido')\n"
            "t.extractall('/var/lib/cabanacontrol',filter='data')"
        )
        command(
            "run",
            "--no-deps",
            "-T",
            "--name",
            f"p-restore-{identifier}",
            "backend",
            "python",
            "-c",
            code,
            data=content["media.tar"],
        )
        print(
            json.dumps(
                {
                    "restored_project": args.project,
                    "seconds": round(time.monotonic() - started, 2),
                    "writers": "stopped",
                }
            )
        )


if __name__ == "__main__":
    main()
