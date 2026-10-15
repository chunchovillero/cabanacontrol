from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError

from apps.audit.services import record_event
from apps.guests.models import Guest
from apps.tenants.queries import authorized_memberships


class DuplicateRut(APIException):
    status_code = 409
    default_code = "duplicate_document"
    default_detail = "Este RUT ya está registrado en la empresa. Reutiliza la ficha existente."


def require_editor(actor, tenant):
    if (
        not authorized_memberships(actor)
        .filter(tenant=tenant, role__in=["owner", "manager"])
        .exists()
    ):
        raise PermissionDenied("No tienes permiso para modificar huéspedes de esta empresa.")


def reject_duplicate(instance):
    if instance.document_type != "rut":
        return
    existing = Guest.objects.filter(
        tenant_id=instance.tenant_id, document_type="rut", document_number=instance.document_number
    )
    if instance.pk:
        existing = existing.exclude(pk=instance.pk)
    existing_id = existing.values_list("pk", flat=True).first()
    if existing_id:
        raise DuplicateRut(
            {"document_number": DuplicateRut.default_detail, "existing_guest_id": str(existing_id)}
        )


def save_guest(*, actor, tenant, data, instance=None):
    with transaction.atomic():
        require_editor(actor, tenant)
        before = {}
        if instance is None:
            instance = Guest(tenant=tenant, created_by=actor)
            action = "guest_created"
        else:
            instance = get_object_or_404(
                Guest.objects.select_for_update(), pk=instance.pk, tenant=tenant
            )
            before = {"active": instance.active}
            action = "guest_updated"
            if "active" in data and data["active"] != instance.active:
                action = "guest_activated" if data["active"] else "guest_deactivated"
        allowed = {
            "first_name",
            "last_name",
            "document_type",
            "document_number",
            "phone",
            "email",
            "notes",
            "active",
        }
        if set(data) - allowed:
            raise ValidationError("La empresa, autor e identificador no se pueden modificar.")
        for key, value in data.items():
            setattr(instance, key, value)
        try:
            instance.full_clean(validate_unique=False, validate_constraints=False)
        except DjangoValidationError as exc:
            # Nunca incluir documento/contacto en el mensaje devuelto ni en logs.
            raise ValidationError(
                {key: "Valor no válido. Revisa este campo." for key in exc.message_dict}
            ) from exc
        reject_duplicate(instance)
        try:
            with transaction.atomic():
                instance.save()
        except IntegrityError as exc:
            if (
                getattr(getattr(exc.__cause__, "diag", None), "constraint_name", "")
                == "guest_tenant_rut_unique"
            ):
                reject_duplicate(instance)
                raise DuplicateRut() from exc
            raise
        record_event(
            actor=actor,
            tenant=tenant,
            entity="guest",
            entity_id=instance.pk,
            action=action,
            before=before,
            after={"active": instance.active, "changed_fields": sorted(data)},
        )
        return instance
