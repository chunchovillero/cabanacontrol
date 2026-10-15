"""Create isolated fictional configuration and a local-only TLS certificate."""

import ipaddress
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

ROOT = Path(__file__).resolve().parent.parent
directory = ROOT / ".local-production"
tls = directory / "tls"
directory.mkdir(exist_ok=True)
tls.mkdir(exist_ok=True)
env = directory / "rehearsal.env"
if env.exists() or any(tls.iterdir()):
    raise SystemExit("La configuración local ya existe; no se sobrescribirá.")
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
now = datetime.now(UTC)
certificate = (
    x509.CertificateBuilder()
    .subject_name(name)
    .issuer_name(name)
    .public_key(key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(now - timedelta(minutes=1))
    .not_valid_after(now + timedelta(days=7))
    .add_extension(
        x509.SubjectAlternativeName(
            [
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
            ]
        ),
        critical=False,
    )
    .sign(key, hashes.SHA256())
)
(tls / "server.key").write_bytes(
    key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
)
(tls / "server.crt").write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
values = {
    "DJANGO_DEBUG": "false",
    "DJANGO_SECRET_KEY": secrets.token_urlsafe(64),
    "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1",
    "FRONTEND_URL": "https://localhost:25443",
    "POSTGRES_DB": "cabanacontrol_pcheck",
    "POSTGRES_USER": "cabanacontrol_pcheck",
    "POSTGRES_PASSWORD": secrets.token_urlsafe(32),
    "POSTGRES_ADMIN_USER": "cabanacontrol_admin",
    "POSTGRES_ADMIN_PASSWORD": secrets.token_urlsafe(32),
    "EMAIL_BACKEND": "django.core.mail.backends.filebased.EmailBackend",
    "EMAIL_FILE_PATH": "/tmp/p-rehearsal-emails",
    "DEFAULT_FROM_EMAIL": "CabañaControl <no-reply@example.invalid>",
    "P_REHEARSAL": "true",
    "AI_ENABLED": "false",
    "AI_TEST_PROVIDER": "false",
    "WHATSAPP_REAL_ENABLED": "false",
    "WHATSAPP_TEST_PROVIDER": "false",
    "E2E_TEST_MODE": "false",
    "PUBLIC_HOST": "localhost",
    "PUBLIC_ORIGIN": "https://localhost:25443",
    "PRODUCTION_HTTP_PORT": "25080",
    "PRODUCTION_HTTPS_PORT": "25443",
    "TLS_DIRECTORY": tls.relative_to(ROOT).as_posix(),
}
env.write_text("".join(f"{k}={v}\n" for k, v in values.items()), encoding="utf-8")
for path in (env, tls / "server.key"):
    path.chmod(0o600)
print(
    "Configuración ficticia creada; certificado local de 7 días. No se imprimen secretos."
)
