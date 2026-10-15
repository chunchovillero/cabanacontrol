import json
from datetime import timedelta
from hashlib import sha256
from hmac import new as hmac_new
from unittest.mock import patch
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.inquiries.models import Inquiry
from apps.whatsapp.crypto import WhatsAppUnavailable, decrypt_token
from apps.whatsapp.models import (
    ConsentRecord,
    Conversation,
    Message,
    OutboxJob,
    Template,
    WebhookEvent,
)
from apps.whatsapp.providers import SendFailure
from apps.whatsapp.serializers import ConnectionSerializer
from apps.whatsapp.services import WhatsAppConflict, configure, consent, enqueue
from apps.whatsapp.worker import claim_job, run_once

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def wa(identities, settings):
    settings.WHATSAPP_ENCRYPTION_KEYS = json.dumps({"v1": Fernet.generate_key().decode()})
    settings.WHATSAPP_ACTIVE_KEY_VERSION = "v1"
    settings.WHATSAPP_REAL_ENABLED = True
    settings.WHATSAPP_TEST_PROVIDER = False
    settings.WHATSAPP_GRAPH_VERSION = "v0.0"
    settings.WHATSAPP_APP_SECRET = "fictitious-app-secret"
    settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN = "fictitious-verify"
    connection = configure(
        actor=identities["owner"],
        tenant=identities["tenant_a"],
        data={
            "business_id": "10001",
            "phone_number_id": "20001",
            "display_phone": "+56900000001",
            "access_token": "fictitious-private-token",
            "enabled": True,
        },
    )
    conversation = Conversation.objects.create(
        connection=connection,
        contact_phone="56900000002",
        last_inbound_at=timezone.now() - timedelta(minutes=1),
    )
    ConsentRecord.objects.create(
        conversation=conversation,
        granted=True,
        source="Fixture permiso",
        recorded_by=identities["owner"],
    )
    return connection, conversation


def data(conversation, **overrides):
    return {
        "conversation_id": conversation.pk,
        "revision": conversation.revision,
        "request_id": uuid4(),
        "text": "Respuesta ficticia revisada",
        "reviewed": True,
        "template_id": None,
        **overrides,
    }


def enqueue_for(identities, payload):
    return enqueue(actor=identities["staff"], tenant=identities["tenant_a"], data=payload)


def test_credentials_encrypted_and_bound_to_connection(wa, identities):
    connection, _ = wa
    assert "fictitious-private-token" not in connection.access_token_ciphertext
    assert decrypt_token(connection) == "fictitious-private-token"
    assert "access_token" not in json.dumps(ConnectionSerializer(connection).data)
    connection.tenant_id = identities["tenant_b"].pk
    with pytest.raises(WhatsAppUnavailable):
        decrypt_token(connection)
    with pytest.raises(PermissionDenied):
        configure(actor=identities["staff"], tenant=identities["tenant_a"], data={"enabled": False})


def payload(connection, message_id="wamid.fixture", text="Consulta ficticia"):
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": connection.business_id,
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "metadata": {"phone_number_id": connection.phone_number_id},
                            "messages": [
                                {
                                    "id": message_id,
                                    "from": "56900000002",
                                    "timestamp": str(int(timezone.now().timestamp())),
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


def webhook(client, settings, body, signed=True):
    raw = json.dumps(body).encode()
    signature = (
        "sha256=" + hmac_new(settings.WHATSAPP_APP_SECRET.encode(), raw, sha256).hexdigest()
        if signed
        else "bad"
    )
    return client.post(
        "/webhooks/whatsapp/",
        raw,
        content_type="application/json",
        HTTP_X_HUB_SIGNATURE_256=signature,
    )


def test_signature_challenge_dedup_and_no_automatic_ai(csrf_client, settings, wa):
    connection, _ = wa
    result = csrf_client.get(
        "/webhooks/whatsapp/",
        {
            "hub.mode": "subscribe",
            "hub.verify_token": settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN,
            "hub.challenge": "fixture",
        },
    )
    assert result.status_code == 200 and result.content == b"fixture"
    assert webhook(csrf_client, settings, payload(connection), signed=False).status_code == 403
    assert WebhookEvent.objects.count() == 0
    assert webhook(csrf_client, settings, payload(connection)).status_code == 200
    assert webhook(csrf_client, settings, payload(connection)).status_code == 200
    assert WebhookEvent.objects.count() == 1
    with patch("apps.assistant.providers.get_provider") as ai:
        run_once()
        run_once()
        ai.assert_not_called()
    assert Inquiry.objects.count() == 1 and Inquiry.objects.get().created_by_id is None
    assert Message.objects.filter(direction="inbound").count() == 1


def test_mismatched_business_routing_rejected(csrf_client, settings, wa):
    connection, _ = wa
    body = payload(connection)
    body["entry"][0]["id"] = "99999"
    assert webhook(csrf_client, settings, body).status_code == 400
    assert not WebhookEvent.objects.exists()


def test_human_send_idempotent_and_only_accepted(wa, identities):
    _, conversation = wa
    request = data(conversation)
    job = enqueue_for(identities, request)
    assert enqueue_for(identities, request).pk == job.pk
    with pytest.raises(WhatsAppConflict):
        enqueue_for(identities, {**request, "text": "Otro contenido"})
    with patch("apps.whatsapp.worker.send", return_value="wamid.outgoing") as provider:
        run_once()
        run_once()
        provider.assert_called_once()
    job.refresh_from_db()
    job.message.refresh_from_db()
    assert job.state == job.message.status == "accepted"
    assert OutboxJob.objects.count() == 1


def test_unknown_timeout_is_not_retried(wa, identities):
    _, conversation = wa
    job = enqueue_for(identities, data(conversation))
    with patch(
        "apps.whatsapp.worker.send", side_effect=SendFailure("timeout", uncertain=True)
    ) as provider:
        run_once()
        run_once()
        provider.assert_called_once()
    job.refresh_from_db()
    assert job.state == "unknown"


def test_crashed_sender_lease_unknown_not_reclaimed(wa, identities):
    _, conversation = wa
    job = enqueue_for(identities, data(conversation))
    claim_job()
    OutboxJob.objects.filter(pk=job.pk).update(lease_until=timezone.now() - timedelta(seconds=1))
    assert claim_job() is None
    job.refresh_from_db()
    assert job.state == "unknown"


@pytest.mark.parametrize("change", ["disabled", "revoked", "membership"])
def test_worker_revalidates_before_sending(wa, identities, change):
    connection, conversation = wa
    job = enqueue_for(identities, data(conversation))
    if change == "disabled":
        configure(
            actor=identities["owner"],
            tenant=identities["tenant_a"],
            data={"enabled": False, "revision": connection.revision},
        )
    elif change == "revoked":
        consent(
            actor=identities["staff"],
            tenant=identities["tenant_a"],
            conversation_id=conversation.pk,
            revision=conversation.revision,
            granted=False,
            source="Baja explícita",
        )
    else:
        membership = identities["memberships"]["staff"]
        membership.active = False
        membership.save()
    with patch("apps.whatsapp.worker.send") as provider:
        run_once()
        provider.assert_not_called()
    job.refresh_from_db()
    assert job.state == "blocked"


def test_window_requires_verified_template_and_consents(wa, identities):
    connection, conversation = wa
    conversation.last_inbound_at = timezone.now() - timedelta(hours=25)
    conversation.save()
    with pytest.raises(ValidationError):
        enqueue_for(identities, data(conversation))
    template = Template.objects.create(
        connection=connection,
        name="fixture",
        language="es_CL",
        body="Plantilla ficticia",
        approved=True,
        enabled=True,
        verified_at=timezone.now(),
    )
    assert enqueue_for(identities, data(conversation, text=template.body, template_id=template.pk))
    with pytest.raises(ValidationError):
        enqueue_for(
            identities, data(conversation, text="Contenido cambiado", template_id=template.pk)
        )


def test_inbound_opt_out_blocks_queued_send(wa, identities, csrf_client, settings):
    connection, conversation = wa
    job = enqueue_for(identities, data(conversation))
    webhook(csrf_client, settings, payload(connection, text="BAJA"))
    with patch("apps.whatsapp.worker.send") as provider:
        run_once()
        provider.assert_not_called()
    job.refresh_from_db()
    assert job.state == "blocked"
