from datetime import datetime
from uuid import UUID

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from apps.audit.services import record_event
from apps.payments.models import Payment
from apps.payments.queries import CHARGEABLE_STATES
from apps.properties.images import normalize_photo
from apps.reservations.models import Reservation
from apps.reservations.services import clean_text, money, require_operator, validate_model


class PaymentConflict(APIException):
    status_code = 409
    default_code = "payment_conflict"
    default_detail = "La solicitud ya existe con otros datos. Revisa el historial de pagos."


def existing_request(tenant, data, reservation):
    existing = Payment.objects.filter(tenant=tenant, request_id=data["request_id"]).first()
    if existing is None:
        return None
    if existing.reservation_id != reservation.pk or any(
        getattr(existing, field) != data[field]
        for field in ("amount", "paid_at", "method", "reference")
    ):
        raise PaymentConflict()
    return existing


@transaction.atomic
def record_payment(*, actor, tenant, reservation_id, data):
    require_operator(actor, tenant)
    if set(data) != {"request_id", "amount", "paid_at", "method", "reference"}:
        raise ValidationError("Campos de pago no válidos.")
    reservation = get_object_or_404(
        Reservation.objects.select_for_update(), tenant=tenant, pk=reservation_id
    )
    data = dict(data)
    data["amount"] = money(data["amount"])
    if data["amount"] <= 0:
        raise ValidationError({"amount": "El abono debe ser mayor que cero."})
    try:
        data["request_id"] = UUID(str(data["request_id"]))
    except (ValueError, TypeError) as exc:
        raise ValidationError({"request_id": "Identificador de solicitud no válido."}) from exc
    if (
        not isinstance(data["paid_at"], datetime)
        or timezone.is_naive(data["paid_at"])
        or data["paid_at"] > timezone.now()
    ):
        raise ValidationError(
            {"paid_at": "Indica cuándo se recibió el pago, con zona horaria y sin fecha futura."}
        )
    data["reference"] = clean_text(data["reference"], 150, "reference")
    existing = existing_request(tenant, data, reservation)
    if existing:
        return existing, False
    if reservation.status not in CHARGEABLE_STATES:
        raise ValidationError("Esta reserva no admite pagos nuevos en su estado actual.")
    if reservation.currency != "CLP":
        raise ValidationError("Esta fase registra pagos solo en CLP.")
    payment = Payment(
        tenant=tenant,
        reservation=reservation,
        currency=reservation.currency,
        recorded_by=actor,
        **data,
    )
    validate_model(payment)
    try:
        with transaction.atomic():
            payment.save()
    except IntegrityError as exc:
        if (
            getattr(getattr(exc.__cause__, "diag", None), "constraint_name", "")
            == "payment_request_unique"
        ):
            existing = existing_request(tenant, data, reservation)
            if existing:
                return existing, False
        raise
    record_event(
        actor=actor,
        tenant=tenant,
        entity="payment",
        entity_id=payment.pk,
        action="payment_recorded",
        after={
            "reservation_id": str(reservation.pk),
            "amount": str(payment.amount),
            "currency": payment.currency,
            "method": payment.method,
            "paid_at": payment.paid_at.isoformat(),
        },
    )
    return payment, True


@transaction.atomic
def void_payment(*, actor, tenant, payment_id, reason):
    require_operator(actor, tenant)
    candidate = get_object_or_404(Payment, tenant=tenant, pk=payment_id)
    get_object_or_404(
        Reservation.objects.select_for_update(), tenant=tenant, pk=candidate.reservation_id
    )
    payment = get_object_or_404(Payment.objects.select_for_update(), tenant=tenant, pk=payment_id)
    reason = clean_text(reason, 1000, "reason", required=True)
    if payment.status == "voided":
        if payment.void_reason != reason:
            raise PaymentConflict("El pago ya fue anulado. Su motivo original se conserva.")
        return payment
    payment.status = "voided"
    payment.voided_by, payment.void_reason, payment.voided_at = actor, reason, timezone.now()
    validate_model(payment)
    payment.save()
    record_event(
        actor=actor,
        tenant=tenant,
        entity="payment",
        entity_id=payment.pk,
        action="payment_voided",
        before={"status": "recorded"},
        after={
            "status": "voided",
            "reservation_id": str(payment.reservation_id),
            "amount": str(payment.amount),
            "currency": payment.currency,
        },
    )
    return payment


def attach_receipt(*, actor, tenant, payment_id, upload):
    require_operator(actor, tenant)
    # Referencia autorizada antes de decodificar/escribir el archivo.
    candidate = get_object_or_404(Payment, tenant=tenant, pk=payment_id)
    content, content_type = normalize_photo(upload)
    with transaction.atomic():
        require_operator(actor, tenant)
        get_object_or_404(
            Reservation.objects.select_for_update(), tenant=tenant, pk=candidate.reservation_id
        )
        payment = get_object_or_404(
            Payment.objects.select_for_update(), tenant=tenant, pk=payment_id
        )
        if payment.receipt_file or payment.status == "voided":
            raise PaymentConflict(
                "El pago ya tiene comprobante o está anulado; se conserva su historial."
            )
        record_event(
            actor=actor,
            tenant=tenant,
            entity="payment",
            entity_id=payment.pk,
            action="payment_receipt_attached",
        )
        payment.receipt_content_type = content_type
        payment.receipt_file.save(content.name, content, save=True)
        return payment
