from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError

from apps.audit.services import record_event
from apps.billing.models import SubscriptionEvent, SubscriptionPlan, TenantSubscription
from apps.properties.models import Property
from apps.tenants.models import Membership, Tenant

CATALOG = {
    "initial": ("Inicial", 3, 2),
    "growth": ("Crecimiento", 8, 5),
    "operator": ("Operador", 20, 10),
    "trial": ("Prueba de 14 días", 1, 1),
}


class CapacityExceeded(APIException):
    status_code = 409
    default_code = "plan_capacity_exceeded"
    default_detail = "Se alcanzó la capacidad del plan. Consulta al propietario."


def lock_tenant(tenant):
    return Tenant.objects.select_for_update().get(pk=tenant.pk)


def usage(tenant):
    return {
        "properties": Property.objects.filter(tenant=tenant, active=True).count(),
        "members": Membership.objects.filter(tenant=tenant, active=True).count(),
    }


def check_capacity(tenant, resource):
    """Caller holds Tenant lock in the same transaction before resource locks."""
    subscription = (
        TenantSubscription.objects.select_related("plan")
        .filter(tenant=tenant, enforced=True)
        .first()
    )
    if not subscription:
        return
    limit = (
        subscription.plan.property_limit
        if resource == "properties"
        else subscription.plan.member_limit
    )
    if usage(tenant)[resource] >= limit:
        raise CapacityExceeded()


def snapshot(tenant):
    counts = usage(tenant)
    sub = TenantSubscription.objects.select_related("plan").filter(tenant=tenant).first()
    if not sub:
        return {
            "status": "unassigned",
            "enforced": False,
            "plan": None,
            "usage": counts,
            "trial_ends_at": None,
            "over_capacity": False,
        }
    status = "manual"
    if sub.plan.code == "trial":
        status = "trial" if timezone.now() < sub.trial_ends_at else "expired"
    return {
        "status": status,
        "enforced": sub.enforced,
        "plan": {
            "code": sub.plan.code,
            "version": sub.plan.version,
            "name": sub.plan.name,
            "property_limit": sub.plan.property_limit,
            "member_limit": sub.plan.member_limit,
        },
        "usage": counts,
        "trial_ends_at": sub.trial_ends_at,
        "over_capacity": counts["properties"] > sub.plan.property_limit
        or counts["members"] > sub.plan.member_limit,
    }


@transaction.atomic
def assign_plan(*, actor, tenant, code, reason):
    if not actor.is_active or not actor.is_platform_admin:
        raise PermissionDenied("Requiere un administrador de plataforma activo.")
    reason = reason.strip()
    if not reason or len(reason) > 300 or any(ord(c) < 32 for c in reason):
        raise ValidationError(
            "Indica un motivo válido de hasta 300 caracteres, sin datos personales."
        )
    if code not in CATALOG:
        raise ValidationError("Plan desconocido.")
    tenant = lock_tenant(tenant)
    from apps.billing.models import SimulatedContract

    if SimulatedContract.objects.filter(tenant=tenant, finalized=False).exists():
        raise ValidationError(
            "Gestiona el contrato simulado vigente antes de reasignar manualmente."
        )
    sub = TenantSubscription.objects.filter(tenant=tenant).first()
    if code == "trial" and sub and sub.trial_used:
        raise ValidationError("Esta empresa ya utilizó su prueba; no se reinicia.")
    name, properties, members = CATALOG[code]
    plan, _ = SubscriptionPlan.objects.get_or_create(
        code=code,
        version=1,
        defaults={"name": name, "property_limit": properties, "member_limit": members},
    )
    if (plan.name, plan.property_limit, plan.member_limit) != CATALOG[code]:
        raise ValidationError("La versión del catálogo fue alterada; revisa la configuración.")
    if not sub:
        sub = TenantSubscription(tenant=tenant)
    sub.plan = plan
    if code == "trial":
        counts = usage(tenant)
        if counts["properties"] > 1 or counts["members"] > 1:
            raise ValidationError("El uso actual supera la prueba 1/1; asigna un plan comercial.")
        sub.trial_used = True
        sub.trial_started_at = timezone.now()
        sub.trial_ends_at = sub.trial_started_at + timedelta(days=14)
    sub.save()
    SubscriptionEvent.objects.create(
        tenant=tenant, actor=actor, plan=plan, action="assigned", reason=reason
    )
    record_event(
        actor=actor,
        tenant=tenant,
        entity="subscription",
        entity_id=tenant.pk,
        action="subscription_assigned",
        after={"plan": code, "version": 1},
    )
    return sub


@transaction.atomic
def enable_limits(*, actor, tenant, reason):
    if not actor.is_active or not actor.is_platform_admin:
        raise PermissionDenied("Requiere administrador de plataforma.")
    if not reason.strip() or len(reason) > 300 or any(ord(c) < 32 for c in reason):
        raise ValidationError("Indica un motivo válido sin datos personales.")
    tenant = lock_tenant(tenant)
    sub = TenantSubscription.objects.select_related("plan").filter(tenant=tenant).first()
    if not sub:
        raise ValidationError("Revisa el uso y asigna un plan antes de habilitar límites.")
    if snapshot(tenant)["over_capacity"]:
        raise ValidationError("El uso supera el plan; revisa la asignación antes de habilitar.")
    if sub.enforced:
        return sub
    sub.enforced = True
    sub.save(update_fields=["enforced", "updated_at"])
    SubscriptionEvent.objects.create(
        tenant=tenant, actor=actor, plan=sub.plan, action="enabled", reason=reason.strip()
    )
    record_event(
        actor=actor,
        tenant=tenant,
        entity="subscription",
        entity_id=tenant.pk,
        action="subscription_limits_enabled",
    )
    return sub
