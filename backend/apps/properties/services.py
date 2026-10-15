from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.audit.services import record_event
from apps.billing.services import check_capacity, lock_tenant
from apps.properties.images import normalize_photo
from apps.properties.models import Property, PropertyPhoto
from apps.tenants.models import Membership
from apps.tenants.queries import authorized_memberships


def require_editor(actor, tenant):
    if (
        not authorized_memberships(actor)
        .filter(tenant=tenant, role__in=[Membership.Role.OWNER, Membership.Role.MANAGER])
        .exists()
    ):
        raise PermissionDenied("No tienes permiso para modificar cabañas de esta empresa.")


def property_snapshot(instance):
    return {
        key: str(getattr(instance, key))
        for key in ("capacity", "base_rate", "check_in_time", "check_out_time", "active")
    }


def save_property(*, actor, tenant, data, instance=None):
    with transaction.atomic():
        require_editor(actor, tenant)
        lock_tenant(tenant)
        if instance is None:
            before = {}
            instance = Property(tenant=tenant, created_by=actor)
            action = "property_created"
        else:
            instance = get_object_or_404(
                Property.objects.select_for_update(), pk=instance.pk, tenant=tenant
            )
            action = "property_updated"
            before = property_snapshot(instance)
            if "active" in data and data["active"] != instance.active:
                action = "property_activated" if data["active"] else "property_deactivated"
        was_active = bool(before) and instance.active
        allowed = {
            "name",
            "code",
            "description",
            "capacity",
            "address",
            "base_rate",
            "check_in_time",
            "check_out_time",
            "active",
        }
        if set(data) - allowed:
            raise ValidationError("La empresa, autor e identificador no se pueden modificar.")
        if isinstance(data.get("base_rate"), float):
            raise ValidationError({"base_rate": "Usa Decimal o texto decimal, sin floats."})
        for key, value in data.items():
            setattr(instance, key, value)
        if instance.active and not was_active:
            check_capacity(tenant, "properties")
        try:
            instance.full_clean(validate_unique=False, validate_constraints=False)
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict) from exc
        if before and "capacity" in data:
            from apps.reservations.models import Reservation
            from apps.reservations.services import local_today

            incompatible = (
                Reservation.objects.filter(
                    tenant=tenant,
                    property=instance,
                )
                .filter(
                    Q(status="checked_in")
                    | Q(
                        status__in=["draft", "pending", "confirmed"],
                        check_out__gt=local_today(tenant),
                    )
                )
                .annotate(occupants=F("adults") + F("children"))
                .filter(occupants__gt=instance.capacity)
            )
            if incompatible.exists():
                raise ValidationError(
                    {"capacity": "Hay reservas vigentes que superan esa capacidad."}
                )
        try:
            with transaction.atomic():
                instance.save()
        except IntegrityError as exc:
            if getattr(exc.__cause__.diag, "constraint_name", "") == "property_tenant_code_unique":
                raise ValidationError(
                    {"code": "Ya existe una cabaña con ese código en esta empresa."}
                ) from exc
            raise
        record_event(
            actor=actor,
            tenant=tenant,
            entity="property",
            entity_id=instance.pk,
            action=action,
            before=before,
            after=property_snapshot(instance),
        )
        return instance


def upload_photo(*, actor, tenant, property, upload, alt, order):
    require_editor(actor, tenant)
    content, content_type = normalize_photo(upload)
    with transaction.atomic():
        require_editor(actor, tenant)
        property = get_object_or_404(
            Property.objects.select_for_update(), pk=property.pk, tenant=tenant
        )
        if property.photos.filter(active=True).count() >= settings.PROPERTY_PHOTO_MAX_COUNT:
            raise ValidationError({"file": "La cabaña ya tiene diez fotos activas."})
        photo = PropertyPhoto(property=property, alt=alt, order=order, content_type=content_type)
        # Validar BD/auditoría antes de escribir el archivo para reducir archivos huérfanos.
        photo.file.name = "pending"
        photo.save()
        record_event(
            actor=actor,
            tenant=tenant,
            entity="property_photo",
            entity_id=photo.pk,
            action="photo_uploaded",
        )
        photo.file.save(content.name, content, save=True)
        return photo


@transaction.atomic
def update_photo(*, actor, tenant, instance, data):
    require_editor(actor, tenant)
    if set(data) - {"alt", "order", "active"}:
        raise ValidationError("Solo se puede modificar descripción, orden y estado de la foto.")
    property = get_object_or_404(
        Property.objects.select_for_update(), pk=instance.property_id, tenant=tenant
    )
    photo = PropertyPhoto.objects.select_for_update().get(pk=instance.pk, property=property)
    if data.get("active") is True and not photo.active:
        if property.photos.filter(active=True).count() >= settings.PROPERTY_PHOTO_MAX_COUNT:
            raise ValidationError({"active": "La cabaña ya tiene diez fotos activas."})
    for key, value in data.items():
        setattr(photo, key, value)
    photo.save()
    record_event(
        actor=actor,
        tenant=tenant,
        entity="property_photo",
        entity_id=photo.pk,
        action="photo_updated",
    )
    return photo
