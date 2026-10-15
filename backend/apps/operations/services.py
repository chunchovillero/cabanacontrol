from datetime import datetime, time
from zoneinfo import ZoneInfo

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.audit.services import record_event
from apps.operations.models import HousekeepingTask
from apps.properties.models import Property
from apps.reservations.services import clean_text, local_today, require_operator, validate_model
from apps.tenants.models import Membership

CHECKLIST = ("bathroom", "kitchen", "bedrooms", "inventory")


def task_snapshot(task):
    return {
        "property_id": str(task.property_id),
        "reservation_id": str(task.reservation_id) if task.reservation_id else None,
        "assigned_to_id": str(task.assigned_to_id) if task.assigned_to_id else None,
        "source": task.source,
        "status": task.status,
        "due_at": task.due_at.isoformat(),
        **{field: getattr(task, field) for field in CHECKLIST},
    }


def checkout_task(actor, tenant, reservation):
    # Called inside the reservation transaction after the reservation row is locked.
    require_operator(actor, tenant)
    if reservation.tenant_id != tenant.pk or reservation.status != "checked_out":
        raise ValidationError(
            "La tarea automática requiere una reserva finalizada de esta empresa."
        )
    due = datetime.combine(local_today(tenant), time(23, 59, 59), ZoneInfo(tenant.timezone))
    task, created = HousekeepingTask.objects.get_or_create(
        reservation=reservation,
        source="checkout",
        defaults={
            "tenant": tenant,
            "property_id": reservation.property_id,
            "due_at": due,
            "created_by": actor,
        },
    )
    if created:
        record_event(
            actor=actor,
            tenant=tenant,
            entity="housekeeping_task",
            entity_id=task.pk,
            action="housekeeping_created",
            after=task_snapshot(task),
        )
    return task


@transaction.atomic
def save_task(*, actor, tenant, data, instance=None):
    require_operator(actor, tenant)
    allowed = {
        "property_id",
        "assigned_to_id",
        "due_at",
        "notes",
        "status",
        "cancel_reason",
        *CHECKLIST,
    }
    if set(data) - allowed:
        raise ValidationError("Campo no permitido.")
    before = {}
    if instance is None:
        if data.get("status", "pending") != "pending":
            raise ValidationError("Crea una tarea pendiente.")
        instance = HousekeepingTask(tenant=tenant, created_by=actor)
    else:
        instance = get_object_or_404(
            HousekeepingTask.objects.select_for_update(), tenant=tenant, pk=instance.pk
        )
        before = task_snapshot(instance)
        if instance.status in ["completed", "cancelled"]:
            raise ValidationError(
                "La tarea cerrada conserva su historial; crea otra tarea para corregirla."
            )
    property_id = data.get("property_id", instance.property_id)
    property = get_object_or_404(Property, tenant=tenant, pk=property_id)
    if instance.source == "checkout" and str(property.pk) != str(instance.property_id):
        raise ValidationError("La tarea de check-out conserva su cabaña original.")
    if (not before or str(property.pk) != before["property_id"]) and not property.active:
        raise ValidationError("Selecciona una cabaña activa para una tarea nueva.")
    instance.property = property
    if "assigned_to_id" in data:
        assigned = data["assigned_to_id"]
        instance.assigned_to = (
            get_object_or_404(
                Membership, pk=assigned, tenant=tenant, active=True, user__is_active=True
            )
            if assigned
            else None
        )
    for field, value in data.items():
        if field not in ["property_id", "assigned_to_id"]:
            setattr(instance, field, value)
    if not isinstance(instance.due_at, datetime) or timezone.is_naive(instance.due_at):
        raise ValidationError({"due_at": "Indica fecha y hora con zona horaria."})
    instance.notes = clean_text(instance.notes, 1000, "notes")
    instance.cancel_reason = clean_text(
        instance.cancel_reason, 1000, "cancel_reason", required=instance.status == "cancelled"
    )
    if instance.status != "cancelled" and instance.cancel_reason:
        raise ValidationError("El motivo corresponde solo a una cancelación.")
    if instance.status == "completed":
        if not all(getattr(instance, field) is True for field in CHECKLIST):
            raise ValidationError("Completa los cuatro puntos del checklist antes de finalizar.")
        instance.completed_at = timezone.now()
    validate_model(instance)
    instance.save()
    record_event(
        actor=actor,
        tenant=tenant,
        entity="housekeeping_task",
        entity_id=instance.pk,
        action="housekeeping_updated" if before else "housekeeping_created",
        before=before,
        after={**task_snapshot(instance), "changed_fields": sorted(data)},
    )
    return instance
