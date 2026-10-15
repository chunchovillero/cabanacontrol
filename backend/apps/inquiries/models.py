import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


def expiry():
    return timezone.now() + timedelta(days=90)


class Inquiry(models.Model):
    class Channel(models.TextChoices):
        WHATSAPP = "whatsapp_manual", "WhatsApp manual"
        WHATSAPP_API = "whatsapp_api", "WhatsApp oficial"
        PHONE = "phone", "Teléfono"
        OTHER = "other", "Otro"

    class Status(models.TextChoices):
        NEW = "new", "Nueva"
        RESPONDED = "responded", "Respondida"
        WAITING = "waiting_customer", "Esperando cliente"
        CONVERTED = "converted", "Convertida"
        DISCARDED = "discarded", "Descartada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT)
    channel = models.CharField(max_length=16, choices=Channel.choices)
    original_text = models.TextField(max_length=4000)
    review_text = models.TextField(max_length=4000, blank=True)
    extraction = models.JSONField(default=dict)
    response_text = models.TextField(max_length=4000, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEW)
    assignee = models.ForeignKey("tenants.Membership", on_delete=models.PROTECT, null=True)
    guest = models.ForeignKey("guests.Guest", on_delete=models.PROTECT, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True)
    expires_at = models.DateTimeField(default=expiry)
    archived_at = models.DateTimeField(null=True)
    revision = models.PositiveIntegerField(default=1)
    converted_reservation = models.OneToOneField(
        "reservations.Reservation", on_delete=models.PROTECT, null=True
    )
    conversion_fingerprint = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        indexes = [
            models.Index(fields=["tenant", "status", "created_at"]),
            models.Index(fields=["tenant", "expires_at"]),
            models.Index(fields=["tenant", "assignee"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status="converted", converted_reservation__isnull=False)
                | (~models.Q(status="converted") & models.Q(converted_reservation__isnull=True)),
                name="inquiry_conversion_consistent",
            )
        ]


INQUIRY_STATUS_CHOICES = Inquiry.Status.choices
INQUIRY_CHANNEL_CHOICES = Inquiry.Channel.choices
