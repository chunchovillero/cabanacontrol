import json
from hashlib import sha256

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from apps.audit.services import record_event
from apps.guests.models import Guest
from apps.inquiries.models import Inquiry
from apps.reservations.services import (
    assert_available,
    lock_properties,
    require_operator,
    save_reservation,
)
from apps.tenants.models import Membership


class InquiryConflict(APIException):
    status_code = 409
    default_detail = "La consulta cambió, venció o ya fue convertida. Recarga antes de continuar."


def editable(inquiry, revision):
    if (
        inquiry.revision != revision
        or inquiry.expires_at <= timezone.now()
        or inquiry.archived_at is not None
        or inquiry.status == "converted"
    ):
        raise InquiryConflict()


@transaction.atomic
def save_inquiry(*, actor, tenant, data, inquiry_id=None):
    require_operator(actor, tenant)
    data = dict(data)
    if inquiry_id:
        inquiry = get_object_or_404(
            Inquiry.objects.select_for_update(), tenant=tenant, pk=inquiry_id
        )
        editable(inquiry, data.pop("revision", None))
    else:
        inquiry = Inquiry(tenant=tenant, created_by=actor)
    if data.get("channel") == "whatsapp_api" and inquiry.channel != "whatsapp_api":
        raise ValidationError("La recepción oficial se registra solo mediante el webhook.")
    if data.get("assignee_id"):
        get_object_or_404(
            Membership, tenant=tenant, pk=data["assignee_id"], active=True, user__is_active=True
        )
    if data.get("guest_id"):
        get_object_or_404(Guest, tenant=tenant, pk=data["guest_id"], active=True)
    if "original_text" in data or "review_text" in data:
        inquiry.extraction = {}
    for key, value in data.items():
        setattr(inquiry, key, value)
    if inquiry_id:
        inquiry.revision += 1
    inquiry.save()
    record_event(
        actor=actor,
        tenant=tenant,
        entity="inquiry",
        entity_id=inquiry.pk,
        action="inquiry_updated" if inquiry_id else "inquiry_created",
        after={"revision": inquiry.revision, "status": inquiry.status},
    )
    return inquiry


@transaction.atomic
def convert(*, actor, tenant, inquiry_id, data):
    require_operator(actor, tenant)
    data = dict(data)
    revision = data.pop("revision")
    if not data.pop("reviewed"):
        raise ValidationError("Revisa los datos antes de convertir.")
    fingerprint = sha256(json.dumps(data, default=str, sort_keys=True).encode()).hexdigest()
    inquiry = get_object_or_404(Inquiry.objects.select_for_update(), tenant=tenant, pk=inquiry_id)
    if inquiry.converted_reservation_id:
        if inquiry.conversion_fingerprint != fingerprint:
            raise InquiryConflict()
        return inquiry.converted_reservation
    editable(inquiry, revision)
    lock_properties(tenant, [data["property_id"]])
    assert_available(tenant, data["property_id"], data["check_in"], data["check_out"])
    reservation = save_reservation(actor=actor, tenant=tenant, data={**data, "status": "draft"})
    inquiry.converted_reservation = reservation
    inquiry.guest_id = reservation.primary_guest_id
    inquiry.conversion_fingerprint = fingerprint
    inquiry.status = "converted"
    inquiry.revision += 1
    inquiry.save()
    record_event(
        actor=actor,
        tenant=tenant,
        entity="inquiry",
        entity_id=inquiry.pk,
        action="inquiry_converted",
        after={"reservation_id": str(reservation.pk)},
    )
    return reservation
