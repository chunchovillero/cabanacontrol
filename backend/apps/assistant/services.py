from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import Throttled

from apps.accounts.throttling import consume_limit
from apps.assistant.models import AIUsageDaily, TenantAISettings
from apps.assistant.providers import ProviderUnavailable
from apps.reservations.services import local_today


@dataclass(frozen=True)
class UsageReservation:
    usage_id: int
    tokens: int
    cost: Decimal
    input_rate: Decimal
    output_rate: Decimal


def configuration(tenant):
    return TenantAISettings.objects.filter(tenant=tenant).first() or TenantAISettings(tenant=tenant)


def pricing():
    from apps.assistant.testing import simulated

    if simulated():
        return [Decimal("1"), Decimal("1")]
    try:
        rates = [
            Decimal(settings.AI_PRICE_INPUT_USD_PER_MILLION),
            Decimal(settings.AI_PRICE_OUTPUT_USD_PER_MILLION),
        ]
        if any(not rate.is_finite() or not 0 < rate <= 100000 for rate in rates):
            raise ValueError
        return rates
    except (InvalidOperation, ValueError):
        raise ProviderUnavailable() from None


def ready():
    from apps.assistant.testing import simulated

    if simulated():
        return True
    try:
        pricing()
    except ProviderUnavailable:
        return False
    return bool(settings.AI_ENABLED and settings.OPENAI_API_KEY and settings.OPENAI_TEXT_MODEL)


def reserve(actor, tenant, text):
    config = configuration(tenant)
    if not ready() or not config.enabled:
        raise ProviderUnavailable()
    consume_limit("ai:user", str(actor.pk), 6, window_seconds=60)
    consume_limit("ai:tenant", str(tenant.pk), 15, window_seconds=60)
    # UTF-8 bytes bound token count conservatively; reserve schema/instructions overhead.
    input_tokens = len(text.encode("utf-8")) + 10000
    tokens = input_tokens + 1200
    input_rate, output_rate = pricing()
    cost = ((input_tokens * input_rate + 1200 * output_rate) / Decimal(1000000)).quantize(
        Decimal("0.000001"), rounding="ROUND_UP"
    )
    with transaction.atomic():
        config = TenantAISettings.objects.select_for_update().get(tenant=tenant)
        if not config.enabled:
            raise ProviderUnavailable()
        AIUsageDaily.objects.get_or_create(tenant=tenant, date=local_today(tenant))
        usage = AIUsageDaily.objects.select_for_update().get(
            tenant=tenant, date=local_today(tenant)
        )
        if (
            usage.requests >= config.daily_requests
            or usage.reserved_tokens + tokens > config.daily_tokens
            or usage.reserved_usd + cost > config.daily_budget_usd
        ):
            raise Throttled(wait=86400, detail="Se alcanzó el límite diario del asistente.")
        usage.requests += 1
        usage.reserved_tokens += tokens
        usage.reserved_usd += cost
        usage.save(update_fields=["requests", "reserved_tokens", "reserved_usd"])
        return UsageReservation(usage.pk, tokens, cost, input_rate, output_rate)


def record_consumption(reservation, interpretation):
    tokens = interpretation.tokens
    if tokens is None or type(tokens) is not int or tokens < 0:
        return
    with transaction.atomic():
        usage = AIUsageDaily.objects.select_for_update().get(pk=reservation.usage_id)
        usage.consumed_tokens += tokens
        usage.reserved_tokens += tokens - reservation.tokens
        input_tokens, output_tokens = interpretation.input_tokens, interpretation.output_tokens
        if (
            type(input_tokens) is int
            and type(output_tokens) is int
            and input_tokens >= 0
            and output_tokens >= 0
            and input_tokens + output_tokens == tokens
        ):
            cost = (
                (input_tokens * reservation.input_rate + output_tokens * reservation.output_rate)
                / Decimal(1000000)
            ).quantize(Decimal("0.000001"), rounding="ROUND_UP")
            usage.reserved_usd += cost - reservation.cost
        usage.save(update_fields=["consumed_tokens", "reserved_tokens", "reserved_usd"])
