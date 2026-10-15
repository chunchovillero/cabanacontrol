import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


def receipt_path(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower()
    return f"tenants/{instance.tenant_id}/payments/{instance.pk}/{uuid.uuid4().hex}.{extension}"


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "Efectivo"
        TRANSFER = "transfer", "Transferencia"
        CARD = "card", "Tarjeta"
        OTHER = "other", "Otro"

    class Status(models.TextChoices):
        RECORDED = "recorded", "Registrado"
        VOIDED = "voided", "Anulado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT)
    reservation = models.ForeignKey(
        "reservations.Reservation", on_delete=models.PROTECT, related_name="payments"
    )
    request_id = models.UUIDField()
    amount = models.DecimalField(
        max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    currency = models.CharField(max_length=3)
    paid_at = models.DateTimeField()
    method = models.CharField(max_length=8, choices=Method.choices)
    reference = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.RECORDED)
    receipt_file = models.FileField(upload_to=receipt_path, max_length=255, blank=True)
    receipt_content_type = models.CharField(max_length=32, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recorded_payments"
    )
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="voided_payments",
        null=True,
        blank=True,
    )
    void_reason = models.TextField(max_length=1000, blank=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-paid_at", "-id"]
        indexes = [
            models.Index(fields=["tenant", "reservation", "status"]),
            models.Index(fields=["tenant", "paid_at"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["tenant", "request_id"], name="payment_request_unique"),
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="payment_amount_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(method__in=["cash", "transfer", "card", "other"]),
                name="payment_method_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["recorded", "voided"]), name="payment_status_valid"
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status="recorded",
                    voided_by__isnull=True,
                    voided_at__isnull=True,
                    void_reason="",
                )
                | (
                    models.Q(status="voided", voided_by__isnull=False, voided_at__isnull=False)
                    & ~models.Q(void_reason="")
                ),
                name="payment_void_consistent",
            ),
        ]

    def __str__(self):
        return str(self.pk)


PAYMENT_STATUS_CHOICES = Payment.Status.choices
