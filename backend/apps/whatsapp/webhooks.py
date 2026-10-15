import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from hmac import compare_digest
from hmac import new as hmac_new

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.exceptions import ValidationError

from apps.reservations.services import clean_text
from apps.whatsapp.models import Connection, WebhookEvent
from apps.whatsapp.providers import ready
from apps.whatsapp.services import phone

MAX_BODY = 1024 * 1024


def parse_events(payload):
    if payload.get("object") != "whatsapp_business_account":
        raise ValueError
    events = []
    if len(payload["entry"]) > 20:
        raise ValueError
    for entry in payload["entry"]:
        for change in entry["changes"]:
            if change["field"] != "messages":
                continue
            value = change["value"]
            if len(value.get("messages", [])) + len(value.get("statuses", [])) > 100:
                raise ValueError
            connection = Connection.objects.filter(
                business_id=str(entry["id"]),
                phone_number_id=str(value["metadata"]["phone_number_id"]),
                enabled=True,
                tenant__active=True,
            ).first()
            if not connection:
                if Connection.objects.filter(
                    phone_number_id=str(value["metadata"]["phone_number_id"]), enabled=True
                ).exists():
                    raise ValueError
                continue
            for message in value.get("messages", []):
                if message.get("type") != "text":
                    continue
                events.append(
                    {
                        "connection": connection,
                        "external_id": clean_text(message["id"], 250, "id", required=True),
                        "kind": "message",
                        "occurred_at": timestamp(message["timestamp"]),
                        "contact_phone": phone(message["from"]),
                        "text": clean_text(message["text"]["body"], 4000, "text", required=True),
                        "delivery_status": "",
                    }
                )
            for status in value.get("statuses", []):
                if status["status"] not in ["sent", "delivered", "read", "failed"]:
                    continue
                events.append(
                    {
                        "connection": connection,
                        "external_id": clean_text(status["id"], 250, "id", required=True),
                        "kind": "status",
                        "occurred_at": timestamp(status["timestamp"]),
                        "contact_phone": phone(status["recipient_id"]),
                        "text": "",
                        "delivery_status": status["status"],
                    }
                )
    if len(events) > 100:
        raise ValueError
    return events


def timestamp(value):
    if not isinstance(value, str) or not value.isdecimal() or len(value) > 12:
        raise ValueError
    result = datetime.fromtimestamp(int(value), UTC)
    if result > timezone.now() + timedelta(minutes=5):
        raise ValueError
    return result


@csrf_exempt
@require_http_methods(["GET", "POST"])
def webhook(request):
    if request.method == "GET":
        expected = settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN
        supplied = request.GET.get("hub.verify_token", "")
        if (
            expected
            and request.GET.get("hub.mode") == "subscribe"
            and compare_digest(expected.encode(), supplied.encode())
        ):
            challenge = request.GET.get("hub.challenge", "")
            if len(challenge) <= 200:
                return HttpResponse(challenge, content_type="text/plain")
        return JsonResponse({"error": "invalid_verification"}, status=403)
    if not settings.WHATSAPP_APP_SECRET or not ready():
        return JsonResponse({"error": "unconfigured"}, status=503)
    try:
        length = int(request.META.get("CONTENT_LENGTH") or 0)
        if length > MAX_BODY:
            return JsonResponse({"error": "payload_too_large"}, status=413)
        body = request.body
        if len(body) > MAX_BODY:
            return JsonResponse({"error": "payload_too_large"}, status=413)
        signature = (
            "sha256=" + hmac_new(settings.WHATSAPP_APP_SECRET.encode(), body, sha256).hexdigest()
        )
        if not compare_digest(
            signature.encode(), request.headers.get("X-Hub-Signature-256", "").encode()
        ):
            return JsonResponse({"error": "invalid_signature"}, status=403)
        events = parse_events(json.loads(body))
        with transaction.atomic():
            for event in events:
                key = {
                    field: event[field]
                    for field in ["connection", "external_id", "kind", "delivery_status"]
                }
                WebhookEvent.objects.get_or_create(
                    **key,
                    defaults={field: value for field, value in event.items() if field not in key},
                )
        return JsonResponse({"received": True})
    except (
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        OverflowError,
        OSError,
        ValidationError,
    ):
        return JsonResponse({"error": "invalid_event"}, status=400)
