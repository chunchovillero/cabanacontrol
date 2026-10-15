import uuid
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import APIException

from apps.reservations.services import require_operator
from apps.whatsapp.models import Connection, Message, OutboxJob, WebhookEvent
from apps.whatsapp.providers import SendFailure, send
from apps.whatsapp.services import WhatsAppConflict, ingest_message, policy, template_snapshot


@transaction.atomic
def claim_event():
    now = timezone.now()
    item = (
        WebhookEvent.objects.select_for_update(skip_locked=True)
        .filter(
            Q(state__in=["pending", "retry"], next_attempt_at__lte=now)
            | Q(state="working", lease_until__lte=now),
            expires_at__gt=now,
        )
        .order_by("created_at", "pk")
        .first()
    )
    if item:
        item.state, item.lease_token = "working", uuid.uuid4()
        item.lease_until = now + timedelta(seconds=60)
        item.attempts += 1
        item.save()
    return item


@transaction.atomic
def process_event(claim):
    event = WebhookEvent.objects.select_for_update().get(pk=claim.pk)
    if event.state != "working" or event.lease_token != claim.lease_token:
        return
    connection = (
        Connection.objects.select_for_update().select_related("tenant").get(pk=event.connection_id)
    )
    if not connection.enabled or not connection.tenant.active:
        event.state = "ignored"
    elif event.kind == "message":
        ingest_message(event)
        event.state = "done"
    else:
        message = (
            Message.objects.select_for_update()
            .filter(
                conversation__connection=connection,
                external_id=event.external_id,
                conversation__contact_phone=event.contact_phone,
                direction="outbound",
            )
            .first()
        )
        if message:
            rank = {
                "queued": 0,
                "accepted": 1,
                "unknown": 1,
                "sent": 2,
                "failed": 2,
                "delivered": 3,
                "read": 4,
            }
            if rank[event.delivery_status] > rank.get(message.status, 0):
                message.status = event.delivery_status
                message.save(update_fields=["status"])
            event.state = "done"
        elif event.attempts < 5:
            event.state = "retry"
            event.next_attempt_at = timezone.now() + timedelta(seconds=2**event.attempts)
        else:
            event.state = "unmatched"
    event.lease_until = None
    event.save()


@transaction.atomic
def claim_job():
    now = timezone.now()
    # A crashed sender may already have delivered: do not take over and resend.
    expired = list(
        OutboxJob.objects.select_for_update(skip_locked=True)
        .filter(state="working", lease_until__lte=now)
        .values_list("pk", "message_id")
    )
    for job_id, message_id in expired:
        OutboxJob.objects.filter(pk=job_id).update(
            state="unknown", last_error_code="sender_interrupted"
        )
        Message.objects.filter(pk=message_id, status="queued").update(status="unknown")
    job = (
        OutboxJob.objects.select_for_update(skip_locked=True)
        .filter(state__in=["pending", "retry"], next_attempt_at__lte=now)
        .order_by("created_at", "pk")
        .first()
    )
    if job:
        job.state, job.lease_token = "working", uuid.uuid4()
        job.lease_until = now + timedelta(seconds=60)
        job.attempts += 1
        job.save()
    return job


def process_job(claim):
    # Short authorization transaction. No HTTP request holds database locks.
    with transaction.atomic():
        job = (
            OutboxJob.objects.select_for_update(of=("self",))
            .select_related("message__conversation", "template", "authorized_by")
            .get(pk=claim.pk)
        )
        if job.state != "working" or job.lease_token != claim.lease_token:
            return
        connection = (
            Connection.objects.select_for_update()
            .select_related("tenant")
            .get(pk=job.connection_id)
        )
        conversation = job.message.conversation
        conversation.connection = connection
        try:
            require_operator(job.authorized_by, connection.tenant)
            if (
                not connection.tenant.active
                or connection.revision != job.connection_revision
                or conversation.revision != job.conversation_revision
                or job.message.expires_at <= timezone.now()
            ):
                raise WhatsAppConflict()
            policy(conversation, job.template)
            if job.template_snapshot != template_snapshot(job.template):
                raise WhatsAppConflict()
        except APIException:
            job.state, job.last_error_code = "blocked", "authorization_changed"
            job.save()
            Message.objects.filter(pk=job.message_id, status="queued").update(status="blocked")
            return
    result, failure = None, None
    try:
        result = send(connection, job.message, job.template)
    except SendFailure as error:
        failure = error
    except APIException:
        failure = SendFailure("unconfigured")
    except Exception:
        # Never retry a request with an unknown send result, or expose exception bodies.
        failure = SendFailure("delivery_unknown", uncertain=True)
    with transaction.atomic():
        current = OutboxJob.objects.select_for_update().get(pk=claim.pk)
        if current.state not in ["working", "unknown"] or current.lease_token != claim.lease_token:
            return
        if failure:
            current.last_error_code = failure.code
            current.state = (
                "unknown"
                if failure.uncertain
                else "retry"
                if failure.retry and current.attempts < 3
                else "failed"
            )
            current.next_attempt_at = timezone.now() + timedelta(seconds=10 * 2**current.attempts)
            Message.objects.filter(pk=current.message_id, status="queued").update(
                status="queued" if current.state == "retry" else current.state
            )
        else:
            current.state = "accepted"
            Message.objects.filter(pk=current.message_id).update(external_id=result)
            Message.objects.filter(pk=current.message_id, status__in=["queued", "unknown"]).update(
                status="accepted"
            )
        current.lease_until = None
        current.save()


def run_once():
    event = claim_event()
    if event:
        process_event(event)
    job = claim_job()
    if job:
        process_job(job)
    return bool(event or job)
