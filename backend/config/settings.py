import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY or SECRET_KEY == "replace-with-a-random-local-secret":
    raise ImproperlyConfigured("Configura DJANGO_SECRET_KEY con un secreto local aleatorio.")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
CSRF_TRUSTED_ORIGINS = os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
CSRF_TRUSTED_ORIGINS = [origin for origin in CSRF_TRUSTED_ORIGINS if origin]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "rest_framework",
    "drf_spectacular",
    "apps.accounts",
    "apps.tenants",
    "apps.audit",
    "apps.properties",
    "apps.guests",
    "apps.reservations",
    "apps.payments",
    "apps.insights",
    "apps.operations",
    "apps.assistant",
    "apps.inquiries",
    "apps.whatsapp",
    "apps.billing",
]
AUTH_USER_MODEL = "accounts.User"
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.tenants.middleware.TenantContextMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "safe_server": {
            "()": "django.utils.log.ServerFormatter",
            "format": "[{server_time}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "safe_server": {
            "class": "logging.StreamHandler",
            "formatter": "safe_server",
            "filters": ["omit_webhook_verification"],
        },
    },
    "filters": {
        "omit_webhook_verification": {
            "()": "apps.whatsapp.logging.OmitWebhookVerification",
        },
    },
    "loggers": {
        "django.server": {"handlers": ["safe_server"], "level": "INFO", "propagate": False},
        "django.request": {"filters": ["omit_webhook_verification"], "propagate": True},
    },
}
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "cabanacontrol"),
        "USER": os.environ.get("POSTGRES_USER", "cabanacontrol"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "OPTIONS": {"connect_timeout": 3},
    }
}
LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
MEDIA_ROOT = os.environ.get("PRIVATE_MEDIA_ROOT", "/var/lib/cabanacontrol/media")
FILE_UPLOAD_PERMISSIONS = 0o600
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o700
PROPERTY_PHOTO_MAX_BYTES = 5 * 1024 * 1024
PROPERTY_PHOTO_MAX_DIMENSION = 4096
PROPERTY_PHOTO_MAX_COUNT = 10
FILE_UPLOAD_MAX_MEMORY_SIZE = PROPERTY_PHOTO_MAX_BYTES
FILE_UPLOAD_HANDLERS = [
    "apps.properties.uploads.BoundedUploadHandler",
    "django.core.files.uploadhandler.MemoryFileUploadHandler",
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
]
DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FILES = 1
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
PASSWORD_RESET_TIMEOUT = 3600
SESSION_COOKIE_AGE = 43200
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_FAILURE_VIEW = "apps.accounts.views.csrf_failure"
SECURE_REFERRER_POLICY = "no-referrer"
X_FRAME_OPTIONS = "DENY"
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173").rstrip("/")
PUBLIC_APP_URL = os.environ.get("PUBLIC_APP_URL", FRONTEND_URL).rstrip("/")
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.filebased.EmailBackend"
    if DEBUG
    else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_FILE_PATH = os.environ.get("EMAIL_FILE_PATH", "/tmp/cabanacontrol-emails")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL", "CabañaControl <no-reply@example.invalid>"
)
LOGIN_ACCOUNT_LIMIT = 5
BILLING_SIMULATION_ENABLED = os.environ.get("BILLING_SIMULATION_ENABLED", "false").lower() == "true"
LOCAL_ONBOARDING_ENABLED = os.environ.get("LOCAL_ONBOARDING_ENABLED", "true").lower() == "true"
GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "").strip()
LOGIN_IP_LIMIT = 30
AUTH_THROTTLE_SECONDS = 600
AI_ENABLED = os.environ.get("AI_ENABLED", "false").lower() == "true"
WHATSAPP_REAL_ENABLED = os.environ.get("WHATSAPP_REAL_ENABLED", "false").lower() == "true"
WHATSAPP_TEST_PROVIDER = os.environ.get("WHATSAPP_TEST_PROVIDER", "false").lower() == "true"
WHATSAPP_GRAPH_VERSION = os.environ.get("WHATSAPP_GRAPH_VERSION", "")
WHATSAPP_APP_SECRET = os.environ.get("WHATSAPP_APP_SECRET", "")
WHATSAPP_WEBHOOK_VERIFY_TOKEN = os.environ.get("WHATSAPP_WEBHOOK_VERIFY_TOKEN", "")
WHATSAPP_ENCRYPTION_KEYS = os.environ.get("WHATSAPP_ENCRYPTION_KEYS", "{}")
WHATSAPP_ACTIVE_KEY_VERSION = os.environ.get("WHATSAPP_ACTIVE_KEY_VERSION", "v1")
AI_TEST_PROVIDER = os.environ.get("AI_TEST_PROVIDER", "false").lower() == "true"
E2E_TEST_MODE = os.environ.get("E2E_TEST_MODE", "false").lower() == "true"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_TEXT_MODEL = os.environ.get("OPENAI_TEXT_MODEL", "")
OPENAI_TRANSCRIPTION_MODEL = os.environ.get("OPENAI_TRANSCRIPTION_MODEL", "")
AI_PRICE_AUDIO_USD_PER_MINUTE = os.environ.get("AI_PRICE_AUDIO_USD_PER_MINUTE", "")
AI_PRICE_INPUT_USD_PER_MILLION = os.environ.get("AI_PRICE_INPUT_USD_PER_MILLION", "")
AI_PRICE_OUTPUT_USD_PER_MILLION = os.environ.get("AI_PRICE_OUTPUT_USD_PER_MILLION", "")
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "EXCEPTION_HANDLER": "apps.accounts.errors.exception_handler",
}
SPECTACULAR_SETTINGS = {
    "TITLE": "CabañaControl API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "InvitationRoleEnum": [("manager", "Administrador"), ("staff", "Colaborador")],
        "MembershipRoleEnum": [
            ("owner", "Propietario"),
            ("manager", "Administrador"),
            ("staff", "Colaborador"),
        ],
        "HousekeepingStatusEnum": "apps.operations.models.HOUSEKEEPING_STATUS_CHOICES",
        "HousekeepingSourceEnum": "apps.operations.models.HOUSEKEEPING_SOURCE_CHOICES",
        "PaymentStatusEnum": "apps.payments.models.PAYMENT_STATUS_CHOICES",
        "InquiryStatusEnum": "apps.inquiries.models.INQUIRY_STATUS_CHOICES",
        "InquiryChannelEnum": "apps.inquiries.models.INQUIRY_CHANNEL_CHOICES",
        "InquiryEditableStatusEnum": ["new", "responded", "waiting_customer", "discarded"],
        "ReservationStatusEnum": "apps.reservations.models.RESERVATION_STATUS_CHOICES",
        "ReservationSourceEnum": "apps.reservations.models.RESERVATION_SOURCE_CHOICES",
        "ReservationInitialStatusEnum": ["draft", "pending", "confirmed"],
    },
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAuthenticated"],
}
