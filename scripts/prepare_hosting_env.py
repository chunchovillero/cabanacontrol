from pathlib import Path
from secrets import token_urlsafe


target = Path(__file__).resolve().parents[1] / ".env.hosting"
if target.exists():
    raise SystemExit(f"Conservado: {target} ya existe")

values = {
    "DJANGO_SECRET_KEY": token_urlsafe(64),
    "POSTGRES_DB": "cabanacontrol_hosting",
    "POSTGRES_USER": "cabanacontrol_app",
    "POSTGRES_PASSWORD": token_urlsafe(48),
    "POSTGRES_ADMIN_USER": "cabanacontrol_admin",
    "POSTGRES_ADMIN_PASSWORD": token_urlsafe(48),
    "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
    "EMAIL_HOST": "localhost",
    "EMAIL_PORT": "587",
    "EMAIL_USE_TLS": "true",
    "EMAIL_HOST_USER": "",
    "EMAIL_HOST_PASSWORD": "",
    "DEFAULT_FROM_EMAIL": "no-reply@labrawebs.com",
    "GOOGLE_OAUTH_CLIENT_ID": "",
    "WHATSAPP_ENCRYPTION_KEYS": "{}",
    "WHATSAPP_ACTIVE_KEY_VERSION": "v1",
}
target.write_text("".join(f"{key}={value}\n" for key, value in values.items()), encoding="utf-8")
target.chmod(0o600)
print(f"Configuración privada creada con permisos 0600: {target}")
