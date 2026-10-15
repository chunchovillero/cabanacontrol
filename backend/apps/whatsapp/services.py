import json
import re
from datetime import timedelta
from hashlib import sha256

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import APIException, Throttled, ValidationError

from apps.accounts.throttling import consume_limit
from apps.audit.services import record_event
from apps.reservations.services import clean_text, local_today, require_operator
from apps.whatsapp.crypto import encrypt_token
from apps.whatsapp.models import (
    Connection,
    ConsentRecord,
    Conversation,
    Message,
    OutboxJob,
    SendUsageDaily,
    Template,
)
from apps.whatsapp.providers import ready


class WhatsAppConflict(APIException):
    status_code = 409
    default_detail = "La conversación, configuración o autorización cambió. Recarga y revisa."


def phone(value):
    value = str(value).removeprefix("+")
    if not re.fullmatch(r"[1-9]\d{6,14}", value):
        raise ValidationError("Usa un teléfono internacional válido.")
    return value


@transaction.atomic
def configure(*, actor, tenant, data):
    require_operator(actor, tenant, blocks=True)
    data = dict(data)
    connection = Connection.objects.select_for_update().filter(tenant=tenant).first()
    revision = data.pop("revision", None)
    if connection:
        if revision != connection.revision:
            raise WhatsAppConflict()
        if any(
            key in data and data[key] != getattr(connection, key)
            for key in ["business_id", "phone_number_id"]
        ):
            raise ValidationError("La cuenta y el número vinculados conservan su historial.")
    else:
        if not all(data.get(key) for key in ["business_id", "phone_number_id", "display_phone"]):
            raise ValidationError("Indica cuenta, identificador y teléfono de empresa.")
        connection = Connection(tenant=tenant)
    for key in ["business_id", "phone_number_id"]:
        if key in data and not re.fullmatch(r"[1-9]\d{0,39}", data[key]):
            raise ValidationError("Identificador de Meta inválido.")
    if "display_phone" in data:
        data["display_phone"] = phone(data["display_phone"])
    if (
        Connection.objects.exclude(tenant=tenant)
        .filter(
            Q(phone_number_id=data.get("phone_number_id", connection.phone_number_id))
            | Q(business_id=data.get("business_id", connection.business_id))
        )
        .exists()
    ):
        raise ValidationError("No se puede registrar esta conexión.")
    token = data.pop("access_token", None)
    for key, value in data.items():
        setattr(connection, key, value)
    if token is not None:
        connection.access_token_ciphertext = encrypt_token(connection, token)
    if connection.enabled and (not ready() or not connection.access_token_ciphertext):
        from apps.whatsapp.crypto import WhatsAppUnavailable

        raise WhatsAppUnavailable()
    connection.revision += 1
    try:
        with transaction.atomic():
            connection.save()
    except IntegrityError:
        raise ValidationError("No se puede registrar esta conexión.") from None
    record_event(
        actor=actor,
        tenant=tenant,
        entity="whatsapp_connection",
        entity_id=connection.pk,
        action="whatsapp_configured",
        after={"enabled": connection.enabled, "revision": connection.revision},
    )
    return connection


def conversation_scope(tenant):
    return Conversation.objects.filter(connection__tenant=tenant).select_related("connection")


def policy(conversation, template=None):
    now = timezone.now()
    if conversation.expires_at <= now:
        raise WhatsAppConflict()
    connection = conversation.connection
    if not connection.enabled or not ready():
        raise WhatsAppConflict()
    consent = ConsentRecord.objects.filter(conversation=conversation).first()
    if not consent or not consent.granted:
        raise ValidationError("Registra permiso vigente para responder a esta consulta.")
    if template:
        if (
            template.connection_id != connection.pk
            or not template.enabled
            or not template.approved
            or template.verified_at is None
            or template.purpose != consent.purpose
        ):
            raise ValidationError("Selecciona una plantilla verificada y autorizada.")
    elif not (
        conversation.last_inbound_at
        and now - timedelta(hours=24) < conversation.last_inbound_at <= now
    ):
        raise ValidationError("Fuera de la ventana de 24 horas usa una plantilla aprobada.")


@transaction.atomic
def consent(*, actor, tenant, conversation_id, granted, source, revision):
    require_operator(actor, tenant)
    conversation = get_object_or_404(
        conversation_scope(tenant).select_for_update(), pk=conversation_id
    )
    if conversation.revision != revision or conversation.expires_at <= timezone.now():
        raise WhatsAppConflict()
    ConsentRecord.objects.create(
        conversation=conversation,
        granted=granted,
        source=clean_text(source, 150, "source", required=True),
        recorded_by=actor,
    )
    conversation.revision += 1
    conversation.save(update_fields=["revision"])
    record_event(
        actor=actor,
        tenant=tenant,
        entity="whatsapp_conversation",
        entity_id=conversation.pk,
        action="whatsapp_consent",
        after={"granted": granted},
    )
    return conversation


def template_snapshot(template):
    return (
        {
            "name": template.name,
            "language": template.language,
            "body": template.body,
            "purpose": template.purpose,
        }
        if template
        else {}
    )


@transaction.atomic
def enqueue(*, actor, tenant, data):
    require_operator(actor, tenant)
    if not data["reviewed"]:
        raise ValidationError("Revisa destinatario y contenido antes de enviar.")
    connection = get_object_or_404(Connection.objects.select_for_update(), tenant=tenant)
    fingerprint = sha256(
        json.dumps(
            {key: str(value) for key, value in data.items() if key not in ["revision", "reviewed"]},
            sort_keys=True,
        ).encode()
    ).hexdigest()
    previous = OutboxJob.objects.filter(
        connection=connection, request_id=data["request_id"]
    ).first()
    if previous:
        if previous.fingerprint != fingerprint:
            raise WhatsAppConflict()
        return previous
    conversation = get_object_or_404(
        Conversation.objects.select_for_update(), connection=connection, pk=data["conversation_id"]
    )
    if conversation.revision != data["revision"]:
        raise WhatsAppConflict()
    template = None
    if data.get("template_id"):
        template = get_object_or_404(
            Template.objects.select_for_update(), connection=connection, pk=data["template_id"]
        )
    policy(conversation, template)
    text = clean_text(data["text"], 4000, "text", required=True)
    if template and text != template.body:
        raise ValidationError("El texto debe coincidir con la plantilla verificada.")
    consume_limit("wa:send:user", str(actor.pk), 6, window_seconds=60)
    consume_limit("wa:send:tenant", str(tenant.pk), 15, window_seconds=60)
    usage, _ = SendUsageDaily.objects.get_or_create(connection=connection, date=local_today(tenant))
    if usage.requests >= 50:
        raise Throttled(wait=86400, detail="Se alcanzó el límite diario de WhatsApp.")
    usage.requests += 1
    usage.save(update_fields=["requests"])
    message = Message.objects.create(
        conversation=conversation,
        direction="outbound",
        text=text,
        status="queued",
        occurred_at=timezone.now(),
    )
    job = OutboxJob.objects.create(
        message=message,
        connection=connection,
        request_id=data["request_id"],
        fingerprint=fingerprint,
        template=template,
        template_snapshot=template_snapshot(template),
        connection_revision=connection.revision,
        conversation_revision=conversation.revision,
        authorized_by=actor,
    )
    record_event(
        actor=actor,
        tenant=tenant,
        entity="whatsapp_message",
        entity_id=message.pk,
        action="whatsapp_send_authorized",
        after={"job_id": str(job.pk)},
    )
    return job


@transaction.atomic
def ingest_message(event):
    connection = event.connection
    conversation, _ = Conversation.objects.get_or_create(
        connection=connection, contact_phone=event.contact_phone
    )
    conversation = Conversation.objects.select_for_update().get(pk=conversation.pk)
    if Message.objects.filter(event=event).exists():
        return
    # Webhook authorization never provides a user: record the source independently.
    from apps.inquiries.models import Inquiry

    inquiry = Inquiry.objects.create(
        tenant=connection.tenant,
        created_by=None,
        channel="whatsapp_api",
        original_text=event.text,
    )
    Message.objects.create(
        conversation=conversation,
        event=event,
        inquiry=inquiry,
        external_id=event.external_id,
        direction="inbound",
        text=event.text,
        status="received",
        occurred_at=event.occurred_at,
    )
    if conversation.last_inbound_at is None or event.occurred_at > conversation.last_inbound_at:
        from apps.inquiries.models import expiry

        conversation.last_inbound_at = event.occurred_at
        conversation.expires_at = expiry()
    conversation.revision += 1
    conversation.save()
    if event.text.strip().casefold() in {
        "stop",
        "baja",
        "no me contacten",
        "no me escriban",
        "no más mensajes",
        "cancelar suscripción",
    }:
        ConsentRecord.objects.create(
            conversation=conversation, granted=False, source="whatsapp_opt_out", recorded_by=None
        )
