"""Production settings: only reachable through the trusted TLS proxy."""

import os
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured

from config.settings import *  # noqa: F403
from config.settings import ALLOWED_HOSTS, DATABASES, FRONTEND_URL, SECRET_KEY

if os.environ.get("DJANGO_DEBUG", "false").lower() != "false":
    raise ImproperlyConfigured("Producción requiere DJANGO_DEBUG=false.")
if len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5:
    raise ImproperlyConfigured("Producción requiere un secreto dedicado de al menos 50 caracteres.")
if not ALLOWED_HOSTS or any(not h or h.startswith(("*", ".")) for h in ALLOWED_HOSTS):
    raise ImproperlyConfigured("Configura hosts explícitos para producción.")
origin = urlsplit(FRONTEND_URL)
if origin.scheme != "https" or origin.hostname not in ALLOWED_HOSTS or origin.path:
    raise ImproperlyConfigured("FRONTEND_URL debe ser un origen HTTPS de un host permitido.")
if not DATABASES["default"]["PASSWORD"]:
    raise ImproperlyConfigured("Configura una contraseña dedicada de PostgreSQL.")
if any(
    os.environ.get(flag, "false").lower() != "false"
    for flag in ("AI_TEST_PROVIDER", "WHATSAPP_TEST_PROVIDER", "E2E_TEST_MODE")
):
    raise ImproperlyConfigured("Producción no permite proveedores ni fixtures E2E.")

DEBUG = False
BILLING_SIMULATION_ENABLED = False
LOCAL_ONBOARDING_ENABLED = False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = False
SECURE_SSL_REDIRECT = True
SECURE_REDIRECT_EXEMPT = [r"^health/$"]
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = [FRONTEND_URL]
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin-allow-popups"
DATABASES["default"]["CONN_MAX_AGE"] = 60
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

# Never emit request paths, query strings, tracebacks, headers or arbitrary errors.
# Status markers support external alerts without replicating guest data.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {"safe": {"()": "config.production_logging.SafeFormatter"}},
    "handlers": {"safe": {"class": "logging.StreamHandler", "formatter": "safe"}},
    "root": {"handlers": ["safe"], "level": "WARNING"},
    "loggers": {
        "django": {"handlers": ["safe"], "level": "WARNING", "propagate": False},
        "gunicorn.error": {"handlers": ["safe"], "level": "INFO", "propagate": False},
    },
}
