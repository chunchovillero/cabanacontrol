import json
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.whatsapp.models import Message, OutboxJob, WebhookEvent
from apps.whatsapp.services import enqueue
from apps.whatsapp.worker import run_once
from tests.conftest import csrf_token, login_client, select_company
from tests.test_whatsapp import wa  # noqa: F401

pytestmark = pytest.mark.django_db(transaction=True)


def enter(client, identities, who="staff"):
    assert login_client(client, identities[who].email).status_code == 200
    assert select_company(client, identities["tenant_a"]).status_code == 200


def post(client, identities, path, data):
    return client.post(
        path,
        data,
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token(client),
        HTTP_X_TENANT_CONTEXT=str(identities["tenant_a"].pk),
    )


def test_staff_cannot_configure_and_cross_tenant_ids_are_404(csrf_client, identities, request):
    _, conversation = request.getfixturevalue("wa")
    enter(csrf_client, identities)
    assert csrf_client.get("/api/v1/whatsapp/connection/").status_code == 403
    response = csrf_client.patch(
        "/api/v1/whatsapp/connection/",
        {"enabled": False},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token(csrf_client),
        HTTP_X_TENANT_CONTEXT=str(identities["tenant_a"].pk),
    )
    assert response.status_code == 403
    assert csrf_client.get(f"/api/v1/whatsapp/conversations/{conversation.pk}/").status_code == 200
    assert select_company(csrf_client, identities["tenant_b"]).status_code == 404
    assert login_client(csrf_client, identities["other"].email).status_code == 200
    assert select_company(csrf_client, identities["tenant_b"]).status_code == 200
    assert csrf_client.get(f"/api/v1/whatsapp/conversations/{conversation.pk}/").status_code == 404


def test_csrf_review_context_and_unexpected_fields(csrf_client, identities, request):
    _, conversation = request.getfixturevalue("wa")
    enter(csrf_client, identities)
    from tests.test_whatsapp import data

    body = json.loads(json.dumps(data(conversation), default=str))
    assert (
        csrf_client.post("/api/v1/whatsapp/messages/send/", body, format="json").status_code == 403
    )
    assert (
        post(
            csrf_client, identities, "/api/v1/whatsapp/messages/send/", {**body, "reviewed": False}
        ).status_code
        == 400
    )
    assert (
        post(
            csrf_client,
            identities,
            "/api/v1/whatsapp/messages/send/",
            {**body, "tenant_id": str(identities["tenant_b"].pk)},
        ).status_code
        == 400
    )
    assert post(csrf_client, identities, "/api/v1/whatsapp/messages/send/", body).status_code == 202
    assert OutboxJob.objects.count() == 1


def test_delivery_status_does_not_regress(request, identities):
    connection, conversation = request.getfixturevalue("wa")
    from tests.test_whatsapp import data

    job = enqueue(actor=identities["staff"], tenant=identities["tenant_a"], data=data(conversation))
    with patch("apps.whatsapp.worker.send", return_value="wamid.status"):
        run_once()
    for status in ["read", "sent", "delivered", "failed"]:
        WebhookEvent.objects.create(
            connection=connection,
            external_id="wamid.status",
            kind="status",
            occurred_at=timezone.now(),
            contact_phone=conversation.contact_phone,
            delivery_status=status,
        )
        run_once()
    job.message.refresh_from_db()
    assert job.message.status == "read"


def test_archive_retains_original_and_does_not_send(csrf_client, identities, request):
    _, conversation = request.getfixturevalue("wa")
    enter(csrf_client, identities)
    message = Message.objects.create(
        conversation=conversation,
        direction="inbound",
        text="Historial ficticio",
        status="received",
        occurred_at=timezone.now(),
        expires_at=timezone.now() - timedelta(seconds=1),
    )
    url = f"/api/v1/whatsapp/conversations/{conversation.pk}/messages/"
    assert csrf_client.get(url).json()["count"] == 0
    assert csrf_client.get(url + "?archived=true").json()["count"] == 1
    assert Message.objects.get(pk=message.pk).text == "Historial ficticio"


def test_new_inbound_blocks_old_review_without_auto_resend(request, identities):
    connection, conversation = request.getfixturevalue("wa")
    from tests.test_whatsapp import data

    job = enqueue(actor=identities["staff"], tenant=identities["tenant_a"], data=data(conversation))
    WebhookEvent.objects.create(
        connection=connection,
        external_id="wamid.new",
        kind="message",
        occurred_at=timezone.now(),
        contact_phone=conversation.contact_phone,
        text="Nueva información",
    )
    with patch("apps.whatsapp.worker.send") as send:
        run_once()
        send.assert_not_called()
    job.refresh_from_db()
    assert job.state == "blocked"
