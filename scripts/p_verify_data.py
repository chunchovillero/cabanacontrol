"""Verify restored fictional financial records and private files without exposing PII."""

import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE = """
import os, json, hashlib
from decimal import Decimal
from django.conf import settings
from django.db.models import Sum, F
from django.db import connection
from apps.accounts.models import User
from apps.tenants.models import Tenant
from apps.properties.models import Property, PropertyPhoto
from apps.reservations.models import Reservation
from apps.payments.models import Payment
assert os.environ.get('P_REHEARSAL') == 'true'
assert settings.DATABASES['default']['NAME'] == 'cabanacontrol_pcheck'
assert not settings.AI_ENABLED and not settings.WHATSAPP_REAL_ENABLED
assert 'POSTGRES_ADMIN_PASSWORD' not in os.environ and 'POSTGRES_ADMIN_USER' not in os.environ
with connection.cursor() as cursor:
    cursor.execute('SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication FROM pg_roles WHERE rolname=current_user')
    assert cursor.fetchone() == (False, False, False, False)
assert User.objects.count() == Tenant.objects.count() == Property.objects.count() == 2
assert PropertyPhoto.objects.count() == Reservation.objects.count() == Payment.objects.count() == 2
assert Reservation.objects.aggregate(total=Sum('total_amount'))['total'] == Decimal('200000')
assert Payment.objects.aggregate(total=Sum('amount'))['total'] == Decimal('50000')
assert not Reservation.objects.exclude(tenant_id=F('property__tenant_id')).exists()
assert not Payment.objects.exclude(tenant_id=F('reservation__tenant_id')).exists()
hashes = []
for photo in PropertyPhoto.objects.all():
    with photo.file.open('rb') as image:
        content = image.read()
    assert content.startswith(b'\\x89PNG')
    hashes.append(hashlib.sha256(content).hexdigest())
assert len(set(hashes)) == 1
print(json.dumps({'users':2,'tenants':2,'properties':2,'reservations':2,'payments':2,
                 'photos':2,'agreed_clp':'200000.00','received_clp':'50000.00',
                 'tenant_relations':'consistent','private_files_sha256':hashes,
                 'db_role':'no cluster privileges','admin_credentials':'not exposed to application'}))
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--docker-config")
    parser.add_argument("--docker-host")
    args = parser.parse_args()
    if not re.fullmatch(r"cabanacontrol-p(?:check|restore)-?[a-z0-9]*", args.project):
        raise SystemExit("Solo proyectos ficticios P.")
    command = ["docker"]
    if args.docker_config:
        command += ["--config", args.docker_config]
    if args.docker_host:
        command += ["--host", args.docker_host]
    command += [
        "compose",
        "--env-file",
        ".local-production/rehearsal.env",
        "-p",
        args.project,
        "-f",
        "compose.production.yaml",
        "exec",
        "-T",
        "backend",
        "python",
        "manage.py",
        "shell",
    ]
    result = subprocess.run(
        command, input=CODE.encode(), capture_output=True, cwd=ROOT, check=True
    )
    print(result.stdout.decode().splitlines()[-1])


if __name__ == "__main__":
    main()
