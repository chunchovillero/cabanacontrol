"""Closed local simulator. No HTTP client, credentials or external provider adapter."""

from calendar import monthrange
from datetime import UTC, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.profile import SettingsConflict
from apps.audit.services import record_event
from apps.billing.models import (
    CheckoutAttempt,
    PlanPrice,
    SaaSCharge,
    SimulatedContract,
    SimulatedProviderEvent,
    SimulationCompany,
    SubscriptionPlan,
    TenantSubscription,
)
from apps.billing.services import CATALOG, lock_tenant
from apps.tenants.models import Membership

PRICES = {"initial": "4500.00", "growth": "9900.00", "operator": "19900.00"}
TERMS = "simulation-v1"


def require_environment():
    if not settings.DEBUG or not settings.BILLING_SIMULATION_ENABLED:
        raise PermissionDenied("La simulación comercial está deshabilitada.")


def authorize(actor, tenant, *, platform=False):
    require_environment()
    tenant = lock_tenant(tenant)
    if not actor.is_authenticated or not actor.is_active or not tenant.active:
        raise PermissionDenied()
    if platform:
        if not actor.is_platform_admin:
            raise PermissionDenied("Requiere administrador de plataforma.")
    elif not Membership.objects.filter(
        user=actor, tenant=tenant, role="owner", active=True
    ).exists():
        raise PermissionDenied("Solo el propietario puede gestionar contratación simulada.")
    if not SimulationCompany.objects.filter(tenant=tenant).exists():
        raise PermissionDenied(
            "Esta empresa no está habilitada como empresa ficticia de simulación."
        )
    sub = get_object_or_404(TenantSubscription, tenant=tenant)
    if not sub.enforced:
        raise ValidationError("Primero revisa, asigna y habilita límites manualmente.")
    return sub


@transaction.atomic
def prepare_company(*, actor, tenant, reason):
    require_environment()
    tenant = lock_tenant(tenant)
    if not actor.is_active or not actor.is_platform_admin:
        raise PermissionDenied()
    if not reason.strip() or len(reason) > 300:
        raise ValidationError("Indica un motivo sin datos personales (máximo 300 caracteres).")
    if not TenantSubscription.objects.filter(tenant=tenant, enforced=True).exists():
        raise ValidationError(
            "Revisa, asigna y habilita límites antes de marcar la empresa ficticia."
        )
    _, created = SimulationCompany.objects.get_or_create(
        tenant=tenant, defaults={"enabled_by": actor}
    )
    for code, amount in PRICES.items():
        name, properties, members = CATALOG[code]
        plan, _ = SubscriptionPlan.objects.get_or_create(
            code=code,
            version=1,
            defaults={"name": name, "property_limit": properties, "member_limit": members},
        )
        if (plan.name, plan.property_limit, plan.member_limit) != CATALOG[code]:
            raise ValidationError("La versión del plan fue alterada.")
        price, _ = PlanPrice.objects.get_or_create(
            plan=plan, version=1, defaults={"amount": Decimal(amount)}
        )
        if price.amount != Decimal(amount) or price.currency != "CLP":
            raise ValidationError("Catálogo de precios alterado.")
    if created:
        record_event(
            actor=actor,
            tenant=tenant,
            entity="simulation_company",
            entity_id=tenant.pk,
            action="billing_simulation_enabled",
        )


def month_end(anchor, offset):
    anchor = anchor.astimezone(UTC)
    year, month = divmod(anchor.year * 12 + anchor.month - 1 + offset, 12)
    month += 1
    return anchor.replace(year=year, month=month, day=min(anchor.day, monthrange(year, month)[1]))


def prorate(old, new, start, end, quoted_at):
    def micros(delta):
        return (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds

    remaining = max(0, micros(end - quoted_at))
    return ((new - old) * Decimal(remaining) / Decimal(micros(end - start))).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )


def revision(contract):
    return contract.revision if contract else 0


def contract_for(tenant):
    return (
        SimulatedContract.objects.select_related("price__plan", "next_price__plan")
        .filter(tenant=tenant)
        .first()
    )


def check_revision(contract, expected):
    if revision(contract) != expected:
        raise SettingsConflict()


def no_unresolved(tenant):
    if CheckoutAttempt.objects.filter(tenant=tenant, state__in=["pending", "uncertain"]).exists():
        raise SettingsConflict("Hay un intento pendiente o incierto. Concilia antes de continuar.")


@transaction.atomic
def quote(*, actor, tenant, code, expected_revision):
    sub = authorize(actor, tenant)
    no_unresolved(tenant)
    contract = contract_for(tenant)
    check_revision(contract, expected_revision)
    price = get_object_or_404(
        PlanPrice.objects.select_related("plan"), plan__code=code, plan__version=1, version=1
    )
    now = timezone.now()
    kind, amount = "purchase", price.amount
    if contract and not contract.finalized:
        if now >= contract.period_end:
            raise SettingsConflict("Procesa el vencimiento antes de crear una cotización.")
        if contract.cancel_at_end or contract.next_price_id:
            raise SettingsConflict("Revisa y retira la intención pendiente antes de subir de plan.")
        if price.amount <= contract.price.amount:
            raise ValidationError(
                "Programa las bajadas al próximo periodo; no son compras inmediatas."
            )
        kind = "upgrade"
        amount = prorate(
            contract.price.amount, price.amount, contract.period_start, contract.period_end, now
        )
    return CheckoutAttempt.objects.create(
        tenant=tenant,
        price=price,
        kind=kind,
        amount=amount,
        prior_price=contract.price if kind == "upgrade" else None,
        target_start=contract.period_start if kind == "upgrade" else None,
        target_end=contract.period_end if kind == "upgrade" else None,
        contract_revision=revision(contract),
        projection_version=sub.updated_at,
        quoted_at=now,
        expires_at=now + timedelta(minutes=15),
    )


@transaction.atomic
def accept_quote(*, actor, tenant, attempt_id, key, terms):
    sub = authorize(actor, tenant)
    attempt = get_object_or_404(
        CheckoutAttempt.objects.select_for_update(), pk=attempt_id, tenant=tenant
    )
    previous = CheckoutAttempt.objects.filter(tenant=tenant, idempotency_key=key).first()
    if previous:
        if previous.pk != attempt.pk or previous.terms_version != terms:
            raise SettingsConflict("La clave de idempotencia corresponde a otra confirmación.")
        return previous
    if terms != TERMS:
        raise ValidationError("Revisa y acepta las condiciones actuales de simulación.")
    no_unresolved(tenant)
    contract = contract_for(tenant)
    if attempt.state != "quoted" or timezone.now() >= attempt.expires_at:
        raise SettingsConflict("La cotización ya no está vigente. Solicita otra.")
    check_revision(contract, attempt.contract_revision)
    if attempt.projection_version != sub.updated_at:
        raise SettingsConflict("Cambió la asignación manual. Cotiza nuevamente.")
    if contract and attempt.kind == "upgrade" and timezone.now() >= contract.period_end:
        raise SettingsConflict("El periodo terminó. Cotiza nuevamente.")
    attempt.idempotency_key, attempt.terms_version = key, terms
    attempt.accepted_by, attempt.accepted_at, attempt.state = actor, timezone.now(), "pending"
    attempt.save()
    record_event(
        actor=actor,
        tenant=tenant,
        entity="checkout",
        entity_id=attempt.pk,
        action="simulated_checkout_accepted",
    )
    return attempt


@transaction.atomic
def manage_intent(*, actor, tenant, operation, expected_revision, code=None, terms=None):
    authorize(actor, tenant)
    no_unresolved(tenant)
    contract = contract_for(tenant)
    if not contract or contract.finalized or timezone.now() >= contract.period_end:
        raise SettingsConflict("No hay un periodo vigente para modificar.")
    check_revision(contract, expected_revision)
    if operation == "cancel":
        contract.cancel_at_end = True
    elif operation == "resume":
        if terms != TERMS:
            raise ValidationError("Acepta expresamente las condiciones y renovación.")
        if code != (contract.next_price or contract.price).plan.code:
            raise SettingsConflict("Revisa el plan y precio de la próxima renovación.")
        contract.cancel_at_end = False
        contract.consent_by, contract.consent_at, contract.terms_version = (
            actor,
            timezone.now(),
            terms,
        )
    elif operation == "clear_change":
        contract.next_price = None
    elif operation == "downgrade":
        if terms != TERMS or contract.cancel_at_end:
            raise ValidationError(
                "Revisa la cancelación y acepta precio/renovación antes de programar."
            )
        price = get_object_or_404(
            PlanPrice.objects.select_related("plan"), plan__code=code, plan__version=1, version=1
        )
        if price.amount >= contract.price.amount:
            raise ValidationError("Solo puedes programar un plan de menor precio.")
        contract.next_price = price
        contract.consent_by, contract.consent_at, contract.terms_version = (
            actor,
            timezone.now(),
            terms,
        )
    else:
        raise ValidationError("Operación inválida.")
    contract.revision += 1
    contract.save()
    record_event(
        actor=actor,
        tenant=tenant,
        entity="simulated_contract",
        entity_id=tenant.pk,
        action=f"simulated_{operation}",
        after={
            "revision": contract.revision,
            "plan": (contract.next_price or contract.price).plan.code,
            "terms": contract.terms_version,
        },
    )
    return contract


@transaction.atomic
def renew_due(*, actor, tenant, retry=False):
    sub = authorize(actor, tenant, platform=True)
    contract = contract_for(tenant)
    if not contract or contract.finalized or timezone.now() < contract.period_end:
        return None
    existing = (
        CheckoutAttempt.objects.filter(
            tenant=tenant, kind="renewal", contract_revision=contract.revision
        )
        .order_by("-retry_number")
        .first()
    )
    if existing and not (retry and existing.state == "rejected"):
        return existing
    no_unresolved(tenant)
    if contract.cancel_at_end:
        contract.finalized = True
        contract.revision += 1
        contract.save()
        record_event(
            actor=actor,
            tenant=tenant,
            entity="simulated_contract",
            entity_id=tenant.pk,
            action="simulated_contract_finalized",
        )
        return None
    end = month_end(contract.anchor, contract.period_index + 1)
    if timezone.now() >= end:
        raise SettingsConflict("El periodo a renovar ya terminó; requiere revisión manual.")
    price = contract.next_price or contract.price
    return CheckoutAttempt.objects.create(
        tenant=tenant,
        price=price,
        kind="renewal",
        retry_number=existing.retry_number + 1 if existing else 0,
        amount=price.amount,
        contract_revision=contract.revision,
        projection_version=sub.updated_at,
        quoted_at=timezone.now(),
        expires_at=end,
        state="pending",
        terms_version=TERMS,
        accepted_by=actor,
        accepted_at=timezone.now(),
        target_start=contract.period_end,
        target_end=end,
    )


@transaction.atomic
def simulate_result(*, actor, tenant, attempt_id, event_id, result):
    sub = authorize(actor, tenant)
    attempt = get_object_or_404(
        CheckoutAttempt.objects.select_for_update().select_related("price__plan"),
        pk=attempt_id,
        tenant=tenant,
    )
    old_event = SimulatedProviderEvent.objects.filter(pk=event_id).first()
    if old_event:
        if old_event.attempt_id != attempt.pk or old_event.result != result:
            raise SettingsConflict("El identificador de evento ya fue utilizado.")
        return attempt
    if result not in ("approved", "rejected", "pending", "uncertain"):
        raise ValidationError("Resultado de simulación inválido.")
    if attempt.state not in ("pending", "uncertain"):
        outcome = "ignored_terminal"
    elif result in ("pending", "uncertain"):
        attempt.state = result
        outcome = result
    elif result == "rejected":
        attempt.state = "rejected"
        outcome = "rejected"
    else:
        contract = contract_for(tenant)
        obsolete = (
            revision(contract) != attempt.contract_revision
            or sub.updated_at != attempt.projection_version
        )
        if attempt.kind == "upgrade" and (not contract or timezone.now() >= contract.period_end):
            obsolete = True
        if attempt.kind == "renewal" and timezone.now() >= attempt.target_end:
            obsolete = True
        if obsolete:
            attempt.state, outcome = "obsolete", "manual_review"
        else:
            now = timezone.now()
            if attempt.kind == "purchase":
                if not contract:
                    contract = SimulatedContract(tenant=tenant)
                contract.price = attempt.price
                contract.anchor = contract.period_start = now
                contract.period_index = 1
                contract.period_end = month_end(now, 1)
                attempt.target_start, attempt.target_end = (
                    contract.period_start,
                    contract.period_end,
                )
                contract.next_price = None
                contract.cancel_at_end = contract.finalized = False
                contract.consent_by = attempt.accepted_by
                contract.consent_at = attempt.accepted_at
                contract.terms_version = attempt.terms_version
            elif attempt.kind == "upgrade":
                contract.price = attempt.price
                contract.consent_by = attempt.accepted_by
                contract.consent_at = attempt.accepted_at
                contract.terms_version = attempt.terms_version
            else:
                contract.price = attempt.price
                contract.period_start, contract.period_end = (
                    attempt.target_start,
                    attempt.target_end,
                )
                contract.period_index += 1
                contract.next_price = None
            contract.revision += 1
            contract.save()
            sub.plan = attempt.price.plan
            sub.save(update_fields=["plan", "updated_at"])
            if attempt.amount > 0:
                SaaSCharge.objects.create(attempt=attempt, amount=attempt.amount)
            attempt.state, outcome = "approved", "applied"
    attempt.save()
    SimulatedProviderEvent.objects.create(
        id=event_id, attempt=attempt, result=result, outcome=outcome
    )
    record_event(
        actor=actor,
        tenant=tenant,
        entity="checkout",
        entity_id=attempt.pk,
        action="simulated_result",
        after={"outcome": outcome},
    )
    return attempt
