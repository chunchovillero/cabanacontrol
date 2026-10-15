import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.inquiries.models import expiry


class Connection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField("tenants.Tenant", on_delete=models.PROTECT)
    business_id = models.CharField(max_length=40, unique=True)
    phone_number_id = models.CharField(max_length=40, unique=True)
    display_phone = models.CharField(max_length=20)
    access_token_ciphertext = models.TextField(blank=True)
    enabled = models.BooleanField(default=False)
    revision = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.ForeignKey(Connection, on_delete=models.PROTECT)
    contact_phone = models.CharField(max_length=20)
    last_inbound_at = models.DateTimeField(null=True)
    revision = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=expiry)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["connection", "contact_phone"], name="wa_conversation_contact_unique"
            )
        ]
        ordering = ["-last_inbound_at", "-pk"]


class WebhookEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.ForeignKey(Connection, on_delete=models.PROTECT)
    external_id = models.CharField(max_length=250)
    kind = models.CharField(max_length=16)
    occurred_at = models.DateTimeField()
    contact_phone = models.CharField(max_length=20, blank=True)
    text = models.TextField(max_length=4000, blank=True)
    delivery_status = models.CharField(max_length=16, blank=True)
    state = models.CharField(max_length=12, default="pending")
    attempts = models.PositiveIntegerField(default=0)
    lease_until = models.DateTimeField(null=True)
    lease_token = models.UUIDField(null=True)
    next_attempt_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(default=expiry)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["connection", "external_id", "kind", "delivery_status"],
                name="wa_event_unique",
            )
        ]
        indexes = [models.Index(fields=["state", "next_attempt_at"])]


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.PROTECT)
    event = models.OneToOneField(WebhookEvent, on_delete=models.PROTECT, null=True)
    inquiry = models.OneToOneField("inquiries.Inquiry", on_delete=models.PROTECT, null=True)
    external_id = models.CharField(max_length=250, blank=True)
    direction = models.CharField(max_length=8)
    text = models.TextField(max_length=4000)
    status = models.CharField(max_length=16)
    occurred_at = models.DateTimeField()
    expires_at = models.DateTimeField(default=expiry)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["occurred_at", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "external_id"],
                condition=~models.Q(external_id=""),
                name="wa_message_external_unique",
            )
        ]


class ConsentRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.PROTECT)
    purpose = models.CharField(max_length=32, default="reservation_inquiry")
    source = models.CharField(max_length=150)
    granted = models.BooleanField()
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]


class Template(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.ForeignKey(Connection, on_delete=models.PROTECT)
    name = models.CharField(max_length=100)
    language = models.CharField(max_length=12)
    body = models.TextField(max_length=4000)
    approved = models.BooleanField(default=False)
    enabled = models.BooleanField(default=False)
    purpose = models.CharField(max_length=32, default="reservation_inquiry")
    verified_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["connection", "name", "language"], name="wa_template_unique"
            )
        ]


class OutboxJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.OneToOneField(Message, on_delete=models.PROTECT)
    connection = models.ForeignKey(Connection, on_delete=models.PROTECT)
    request_id = models.UUIDField()
    fingerprint = models.CharField(max_length=64)
    template = models.ForeignKey(Template, on_delete=models.PROTECT, null=True)
    template_snapshot = models.JSONField(default=dict)
    connection_revision = models.PositiveIntegerField()
    conversation_revision = models.PositiveIntegerField(null=True)
    authorized_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    state = models.CharField(max_length=16, default="pending")
    attempts = models.PositiveIntegerField(default=0)
    lease_token = models.UUIDField(null=True)
    lease_until = models.DateTimeField(null=True)
    next_attempt_at = models.DateTimeField(default=timezone.now)
    last_error_code = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["connection", "request_id"], name="wa_outbox_request_unique"
            )
        ]
        indexes = [models.Index(fields=["state", "next_attempt_at"])]


class SendUsageDaily(models.Model):
    connection = models.ForeignKey(Connection, on_delete=models.PROTECT)
    date = models.DateField()
    requests = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["connection", "date"], name="wa_send_usage_day_unique")
        ]
