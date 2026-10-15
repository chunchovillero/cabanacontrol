import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Reservation(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Borrador"
        PENDING = "pending", "Pendiente"
        CONFIRMED = "confirmed", "Confirmada"
        CHECKED_IN = "checked_in", "En estadía"
        CHECKED_OUT = "checked_out", "Finalizada"
        CANCELLED = "cancelled", "Cancelada"
        NO_SHOW = "no_show", "No se presentó"

    class Source(models.TextChoices):
        DIRECT = "direct", "Directa"
        PHONE = "phone", "Teléfono"
        WHATSAPP = "whatsapp", "WhatsApp"
        OTHER = "other", "Otra"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT)
    property = models.ForeignKey(
        "properties.Property", on_delete=models.PROTECT, related_name="reservations"
    )
    primary_guest = models.ForeignKey(
        "guests.Guest", on_delete=models.PROTECT, related_name="reservations"
    )
    check_in = models.DateField()
    check_out = models.DateField()
    adults = models.PositiveSmallIntegerField()
    children = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=12, choices=Status.choices)
    hold_until = models.DateTimeField(null=True, blank=True)
    total_amount = models.DecimalField(
        max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )
    currency = models.CharField(max_length=3)
    source = models.CharField(max_length=8, choices=Source.choices)
    notes = models.TextField(max_length=2000, blank=True)
    cancel_reason = models.TextField(max_length=1000, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["check_in", "id"]
        indexes = [
            models.Index(fields=["tenant", "property", "check_in", "check_out"]),
            models.Index(fields=["tenant", "status", "check_in"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(adults__gte=1), name="reservation_adult_required"
            ),
            models.CheckConstraint(
                condition=~models.Q(status="pending") | models.Q(hold_until__isnull=False),
                name="reservation_pending_has_hold",
            ),
            models.CheckConstraint(
                condition=models.Q(check_out__gt=models.F("check_in")),
                name="reservation_dates_ordered",
            ),
            models.CheckConstraint(
                condition=models.Q(total_amount__gte=0), name="reservation_amount_nonnegative"
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=[
                        "draft",
                        "pending",
                        "confirmed",
                        "checked_in",
                        "checked_out",
                        "cancelled",
                        "no_show",
                    ]
                ),
                name="reservation_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(source__in=["direct", "phone", "whatsapp", "other"]),
                name="reservation_source_valid",
            ),
        ]

    def __str__(self):
        return str(self.pk)


RESERVATION_STATUS_CHOICES = Reservation.Status.choices
RESERVATION_SOURCE_CHOICES = Reservation.Source.choices


class AvailabilityBlock(models.Model):
    class Reason(models.TextChoices):
        MAINTENANCE = "maintenance", "Mantenimiento"
        OWNER_USE = "owner_use", "Uso del propietario"
        OTHER = "other", "Otro"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT)
    property = models.ForeignKey(
        "properties.Property", on_delete=models.PROTECT, related_name="availability_blocks"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=11, choices=Reason.choices)
    notes = models.TextField(max_length=2000, blank=True)
    active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_date", "id"]
        indexes = [models.Index(fields=["tenant", "property", "active", "start_date"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gt=models.F("start_date")),
                name="availability_block_dates_ordered",
            ),
            models.CheckConstraint(
                condition=models.Q(reason__in=["maintenance", "owner_use", "other"]),
                name="availability_block_reason_valid",
            ),
        ]

    def __str__(self):
        return str(self.pk)
