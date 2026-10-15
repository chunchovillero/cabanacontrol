import uuid

from django.conf import settings
from django.db import models


class Invitation(models.Model):
    class State(models.TextChoices):
        PENDING = "pending", "Pendiente"
        ACCEPTED = "accepted", "Aceptada"
        REVOKED = "revoked", "Revocada"
        EXPIRED = "expired", "Vencida"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT)
    email = models.EmailField()
    role = models.CharField(
        max_length=10, choices=[("manager", "Administrador"), ("staff", "Colaborador")]
    )
    token_hash = models.CharField(max_length=64, unique=True)
    state = models.CharField(max_length=8, choices=State.choices, default=State.PENDING)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="invitations_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        related_name="invitations_accepted",
    )
    accepted_at = models.DateTimeField(null=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        related_name="invitations_revoked",
    )
    revoked_at = models.DateTimeField(null=True)
    membership = models.ForeignKey("tenants.Membership", on_delete=models.PROTECT, null=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["tenant", "state", "expires_at"])]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "email"],
                condition=models.Q(state="pending"),
                name="invitation_pending_email_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(role__in=["manager", "staff"]), name="invitation_role_valid"
            ),
            models.CheckConstraint(
                condition=models.Q(state__in=["pending", "accepted", "revoked", "expired"]),
                name="invitation_state_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        state="accepted",
                        accepted_by__isnull=False,
                        accepted_at__isnull=False,
                        membership__isnull=False,
                    )
                    | (
                        ~models.Q(state="accepted")
                        & models.Q(
                            accepted_by__isnull=True,
                            accepted_at__isnull=True,
                            membership__isnull=True,
                        )
                    )
                ),
                name="invitation_acceptance_consistent",
            ),
        ]
