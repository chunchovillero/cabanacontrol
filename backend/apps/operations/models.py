import uuid

from django.conf import settings
from django.db import models


class HousekeepingTask(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        IN_PROGRESS = "in_progress", "En curso"
        COMPLETED = "completed", "Completada"
        CANCELLED = "cancelled", "Cancelada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT)
    property = models.ForeignKey("properties.Property", on_delete=models.PROTECT)
    reservation = models.ForeignKey(
        "reservations.Reservation", on_delete=models.PROTECT, null=True, blank=True
    )
    assigned_to = models.ForeignKey(
        "tenants.Membership", on_delete=models.PROTECT, null=True, blank=True
    )
    source = models.CharField(
        max_length=8, choices=[("manual", "Manual"), ("checkout", "Check-out")], default="manual"
    )
    status = models.CharField(max_length=11, choices=Status.choices, default="pending")
    due_at = models.DateTimeField()
    bathroom = models.BooleanField(default=False)
    kitchen = models.BooleanField(default=False)
    bedrooms = models.BooleanField(default=False)
    inventory = models.BooleanField(default=False)
    notes = models.TextField(max_length=1000, blank=True)
    cancel_reason = models.TextField(max_length=1000, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_at", "id"]
        indexes = [
            models.Index(fields=["tenant", "status", "due_at"]),
            models.Index(fields=["tenant", "assigned_to", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["reservation"],
                condition=models.Q(source="checkout"),
                name="housekeeping_one_checkout",
            ),
            models.CheckConstraint(
                condition=models.Q(source="manual")
                | models.Q(source="checkout", reservation__isnull=False),
                name="housekeeping_source_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["pending", "in_progress", "completed", "cancelled"]),
                name="housekeeping_status_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status="completed",
                        completed_at__isnull=False,
                        bathroom=True,
                        kitchen=True,
                        bedrooms=True,
                        inventory=True,
                    )
                    | (~models.Q(status="completed") & models.Q(completed_at__isnull=True))
                ),
                name="housekeeping_complete_consistent",
            ),
            models.CheckConstraint(
                condition=(~models.Q(status="cancelled") | ~models.Q(cancel_reason="")),
                name="housekeeping_cancel_reason",
            ),
        ]


HOUSEKEEPING_STATUS_CHOICES = HousekeepingTask.Status.choices
HOUSEKEEPING_SOURCE_CHOICES = HousekeepingTask._meta.get_field("source").choices
