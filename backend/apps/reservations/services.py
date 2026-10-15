from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError

from apps.audit.services import record_event
from apps.guests.models import Guest
from apps.properties.models import Property
from apps.reservations.intervals import validate_interval
from apps.reservations.models import AvailabilityBlock, Reservation
from apps.reservations.queries import blocking_blocks, blocking_reservations
from apps.tenants.queries import authorized_memberships


class AvailabilityConflict(APIException):
    status_code = 409
    default_code = "availability_conflict"
    default_detail = "La cabaña no está disponible en esas fechas. Revisa reservas y bloqueos."


def require_operator(actor, tenant, *, blocks=False):
    membership = authorized_memberships(actor).filter(tenant=tenant)
    if blocks:
        membership = membership.filter(role__in=["owner", "manager"])
    if not membership.exists():
        raise PermissionDenied("No tienes permiso para esta operación en la empresa.")


def local_today(tenant):
    return timezone.localdate(timezone.now(), ZoneInfo(tenant.timezone))


def clean_text(value, maximum, field, *, required=False):
    if not isinstance(value, str):
        raise ValidationError({field: "Ingresa texto válido."})
    value = value.strip()
    if (
        len(value) > maximum
        or (required and not value)
        or any(ord(char) == 0 or 0xD800 <= ord(char) <= 0xDFFF for char in value)
    ):
        raise ValidationError({field: "Ingresa texto válido dentro del límite indicado."})
    return value


def money(value):
    if not isinstance(value, (str, Decimal, int)) or isinstance(value, bool):
        raise ValidationError({"total_amount": "Usa un importe decimal exacto, sin floats."})
    try:
        amount = Decimal(value)
    except (ValueError, ArithmeticError) as exc:
        raise ValidationError({"total_amount": "Importe no válido."}) from exc
    if not amount.is_finite() or amount < 0 or amount >= Decimal("1000000000000"):
        raise ValidationError({"total_amount": "Importe no válido."})
    if amount != amount.quantize(Decimal("0.01")):
        raise ValidationError({"total_amount": "El importe admite hasta dos decimales."})
    return amount


def validate_model(instance):
    try:
        instance.full_clean(validate_unique=False, validate_constraints=False)
    except DjangoValidationError as exc:
        raise ValidationError({key: "Valor no válido." for key in exc.message_dict}) from exc


def lock_properties(tenant, ids):
    # Orden estable al trasladar reservas/bloqueos entre cabañas.
    properties = list(
        Property.objects.select_for_update().filter(tenant=tenant, pk__in=ids).order_by("pk")
    )
    if len(properties) != len(set(str(pk) for pk in ids)):
        from django.http import Http404

        raise Http404
    return {str(item.pk): item for item in properties}


def assert_available(tenant, property_id, start, end, *, reservation=None, block=None):
    if blocking_reservations(tenant, property_id, start, end, exclude=reservation).exists():
        raise AvailabilityConflict()
    if blocking_blocks(tenant, property_id, start, end, exclude=block).exists():
        raise AvailabilityConflict()


def reservation_snapshot(instance):
    return {
        key: str(getattr(instance, key))
        for key in (
            "property_id",
            "primary_guest_id",
            "check_in",
            "check_out",
            "adults",
            "children",
            "status",
            "total_amount",
            "currency",
            "hold_until",
            "source",
        )
    }


@transaction.atomic
def save_reservation(*, actor, tenant, data, instance=None):
    require_operator(actor, tenant)
    if tenant.currency != "CLP":
        raise ValidationError("Esta fase admite reservas en CLP; no se convierten monedas.")
    allowed = {
        "property_id",
        "primary_guest_id",
        "check_in",
        "check_out",
        "adults",
        "children",
        "total_amount",
        "source",
        "notes",
        "hold_until",
    }
    if instance is None:
        allowed.add("status")
    if set(data) - allowed:
        raise ValidationError("Campo no permitido; usa las acciones para cambiar el estado.")
    before = {}
    old_property_id = None
    old_check_in = None
    if instance is None:
        instance = Reservation(tenant=tenant, created_by=actor, currency=tenant.currency)
    else:
        instance = get_object_or_404(
            Reservation.objects.select_for_update(), tenant=tenant, pk=instance.pk
        )
        if instance.status in ["cancelled", "checked_out", "no_show"]:
            raise ValidationError("Una reserva cerrada conserva su historial y no se puede editar.")
        before = reservation_snapshot(instance)
        old_property_id, old_check_in = instance.property_id, instance.check_in
    new_property_id = data.get("property_id", instance.property_id)
    properties = lock_properties(
        tenant,
        [new_property_id]
        + (
            [old_property_id]
            if old_property_id and str(old_property_id) != str(new_property_id)
            else []
        ),
    )
    property = properties[str(new_property_id)]
    if not property.active:
        raise ValidationError({"property_id": "Selecciona una cabaña activa."})
    for key, value in data.items():
        setattr(instance, key, value)
    instance.property = property
    guest = get_object_or_404(Guest, tenant=tenant, pk=instance.primary_guest_id)
    if not guest.active:
        raise ValidationError({"primary_guest_id": "Selecciona un huésped activo."})
    validate_interval(instance.check_in, instance.check_out)
    if old_check_in != instance.check_in and instance.check_in < local_today(tenant):
        raise ValidationError({"check_in": "La entrada no puede ser anterior a hoy."})
    for field, minimum in (("adults", 1), ("children", 0)):
        value = getattr(instance, field)
        if type(value) is not int or value < minimum or value > 32767:
            raise ValidationError({field: "Cantidad de personas no válida."})
    if instance.adults + instance.children > property.capacity:
        raise ValidationError(
            {"adults": "La cantidad de personas supera la capacidad de la cabaña."}
        )
    if (
        before
        and before["status"] == "checked_in"
        and any(
            key in data and str(getattr(instance, key)) != before.get(key)
            for key in ("property_id", "check_in", "check_out", "adults", "children")
        )
    ):
        raise ValidationError(
            "No cambies cabaña, fechas ni ocupación durante una estadía iniciada."
        )
    instance.total_amount = money(instance.total_amount)
    instance.notes = clean_text(instance.notes, 2000, "notes")
    if not before and instance.status not in ["draft", "pending", "confirmed"]:
        raise ValidationError({"status": "Crea un borrador, pendiente o confirmada."})
    if instance.status == "pending":
        hold = instance.hold_until
        if (
            hold is None
            or not isinstance(hold, datetime)
            or timezone.is_naive(hold)
            or hold <= timezone.now()
        ):
            raise ValidationError(
                {"hold_until": "Indica una fecha y hora futura con zona horaria."}
            )
    else:
        if data.get("hold_until") is not None:
            raise ValidationError(
                {"hold_until": "La retención corresponde solo a reservas pendientes."}
            )
        instance.hold_until = None
    validate_model(instance)
    if instance.status in ["pending", "confirmed", "checked_in"]:
        assert_available(
            tenant, property.pk, instance.check_in, instance.check_out, reservation=instance.pk
        )
    instance.save()
    record_event(
        actor=actor,
        tenant=tenant,
        entity="reservation",
        entity_id=instance.pk,
        action="reservation_updated" if before else "reservation_created",
        before=before,
        after={**reservation_snapshot(instance), "changed_fields": sorted(data)},
    )
    return instance


@transaction.atomic
def transition_reservation(*, actor, tenant, instance, status, reason="", hold_until=None):
    require_operator(actor, tenant)
    instance = get_object_or_404(
        Reservation.objects.select_for_update(), tenant=tenant, pk=instance.pk
    )
    property = lock_properties(tenant, [instance.property_id])[str(instance.property_id)]
    transitions = {
        "draft": {"pending", "confirmed", "cancelled"},
        "pending": {"draft", "confirmed", "cancelled"},
        "confirmed": {"checked_in", "cancelled", "no_show"},
        "checked_in": {"checked_out"},
    }
    if status not in transitions.get(instance.status, set()):
        raise ValidationError({"status": "Transición de estado no permitida."})
    today = local_today(tenant)
    before = reservation_snapshot(instance)
    if status in ["pending", "confirmed"]:
        if not property.active or not instance.primary_guest.active:
            raise ValidationError("La cabaña y el huésped deben estar activos.")
        if instance.check_in < today:
            raise ValidationError({"check_in": "La entrada no puede ser anterior a hoy."})
        if instance.adults + instance.children > property.capacity:
            raise ValidationError({"adults": "La ocupación supera la capacidad actual."})
        assert_available(
            tenant, property.pk, instance.check_in, instance.check_out, reservation=instance.pk
        )
    if status == "pending":
        if (
            not isinstance(hold_until, datetime)
            or timezone.is_naive(hold_until)
            or hold_until <= timezone.now()
        ):
            raise ValidationError(
                {"hold_until": "Indica una fecha y hora futura con zona horaria."}
            )
    elif hold_until is not None:
        raise ValidationError({"hold_until": "Solo una reserva pendiente admite retención."})
    if status == "checked_in" and not instance.check_in <= today < instance.check_out:
        raise ValidationError("El inicio de estadía debe estar dentro de las fechas reservadas.")
    if status == "checked_out" and today < instance.check_out:
        raise ValidationError("Finaliza la estadía desde su fecha de salida.")
    if status == "no_show" and today < instance.check_in:
        raise ValidationError("Marca ausencia desde la fecha de entrada.")
    if status in ["cancelled", "no_show"]:
        instance.cancel_reason = clean_text(reason, 1000, "reason", required=True)
    instance.status, instance.hold_until = status, hold_until if status == "pending" else None
    validate_model(instance)
    instance.save()
    record_event(
        actor=actor,
        tenant=tenant,
        entity="reservation",
        entity_id=instance.pk,
        action="reservation_" + status,
        before=before,
        after=reservation_snapshot(instance),
    )
    if status == "checked_out":
        from apps.operations.services import checkout_task

        checkout_task(actor, tenant, instance)
    return instance


@transaction.atomic
def save_block(*, actor, tenant, data, instance=None):
    require_operator(actor, tenant, blocks=True)
    if set(data) - {"property_id", "start_date", "end_date", "reason", "notes", "active"}:
        raise ValidationError("Campo no permitido.")
    before = {}
    old_property_id = None
    if instance is None:
        instance = AvailabilityBlock(tenant=tenant, created_by=actor)
    else:
        instance = get_object_or_404(
            AvailabilityBlock.objects.select_for_update(), tenant=tenant, pk=instance.pk
        )
        old_property_id = instance.property_id
        before = {
            "active": instance.active,
            "property_id": str(instance.property_id),
            "start_date": str(instance.start_date),
            "end_date": str(instance.end_date),
            "reason": instance.reason,
        }
    new_property_id = data.get("property_id", instance.property_id)
    properties = lock_properties(
        tenant,
        [new_property_id]
        + (
            [old_property_id]
            if old_property_id and str(old_property_id) != str(new_property_id)
            else []
        ),
    )
    property = properties[str(new_property_id)]
    for key, value in data.items():
        setattr(instance, key, value)
    instance.property = property
    validate_interval(instance.start_date, instance.end_date)
    instance.notes = clean_text(instance.notes, 2000, "notes")
    validate_model(instance)
    if instance.active:
        if not property.active:
            raise ValidationError({"property_id": "Selecciona una cabaña activa."})
        assert_available(
            tenant, property.pk, instance.start_date, instance.end_date, block=instance.pk
        )
    instance.save()
    record_event(
        actor=actor,
        tenant=tenant,
        entity="availability_block",
        entity_id=instance.pk,
        action="availability_block_updated" if before else "availability_block_created",
        before=before,
        after={
            "active": instance.active,
            "property_id": str(property.pk),
            "start_date": str(instance.start_date),
            "end_date": str(instance.end_date),
            "reason": instance.reason,
            "changed_fields": sorted(data),
        },
    )
    return instance
