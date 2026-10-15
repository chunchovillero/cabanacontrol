import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

from apps.tenants.invitation_models import Invitation  # noqa: F401


def validate_timezone(value):
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValidationError("Selecciona una zona horaria IANA válida.") from exc


class Tenant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    legal_name = models.CharField(max_length=200, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    timezone = models.CharField(
        max_length=64, default="America/Santiago", validators=[validate_timezone]
    )
    currency = models.CharField(
        max_length=3, default="CLP", validators=[RegexValidator(r"^[A-Z]{3}$")]
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]


class Membership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Propietario"
        MANAGER = "manager", "Administrador"
        STAFF = "staff", "Colaborador"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="memberships"
    )
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="memberships")
    role = models.CharField(max_length=10, choices=Role.choices)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "tenant"], name="membership_user_tenant_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(role__in=["owner", "manager", "staff"]),
                name="membership_role_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "active"]),
            models.Index(fields=["tenant", "active"]),
        ]
