from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from django.db import close_old_connections
from django.utils import timezone

from apps.whatsapp.models import Message, OutboxJob, WebhookEvent
from apps.whatsapp.services import enqueue
from apps.whatsapp.worker import claim_event, process_event
from tests.test_whatsapp import data, wa  # noqa: F401

pytestmark = pytest.mark.django_db(transaction=True)


def test_concurrent_double_click_creates_one_intent(identities, request):
    _, conversation = request.getfixturevalue("wa")
    payload = data(conversation)
    barrier = Barrier(2)

    def worker():
        close_old_connections()
        try:
            barrier.wait(timeout=5)
            return enqueue(
                actor=identities["staff"], tenant=identities["tenant_a"], data=payload
            ).pk
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = list(executor.map(lambda _: worker(), range(2)))
    assert first == second
    assert OutboxJob.objects.count() == Message.objects.filter(direction="outbound").count() == 1


def test_event_lease_recovery_rejects_old_worker(request):
    connection, conversation = request.getfixturevalue("wa")
    event = WebhookEvent.objects.create(
        connection=connection,
        external_id="wamid.recovery",
        kind="message",
        occurred_at=timezone.now(),
        contact_phone=conversation.contact_phone,
        text="Recuperación ficticia",
    )
    first = claim_event()
    WebhookEvent.objects.filter(pk=event.pk).update(
        lease_until=timezone.now() - timedelta(seconds=1)
    )
    second = claim_event()
    process_event(first)
    assert not Message.objects.filter(event=event).exists()
    process_event(second)
    process_event(second)
    assert Message.objects.filter(event=event).count() == 1
