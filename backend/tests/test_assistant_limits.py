from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.db import close_old_connections
from rest_framework.exceptions import Throttled

from apps.assistant.models import AIUsageDaily, TenantAISettings
from apps.assistant.providers import Interpretation
from apps.assistant.services import record_consumption, reserve
from apps.assistant.testing import simulated

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def enabled(identities, settings):
    settings.AI_ENABLED = True
    settings.OPENAI_API_KEY = "fictitious-key"
    settings.OPENAI_TEXT_MODEL = "test"
    settings.AI_PRICE_INPUT_USD_PER_MILLION = "1"
    settings.AI_PRICE_OUTPUT_USD_PER_MILLION = "2"
    return TenantAISettings.objects.create(tenant=identities["tenant_a"], enabled=True)


def test_reconciles_known_usage_preserves_estimate_without_split(identities, enabled):
    reserved = reserve(identities["owner"], identities["tenant_a"], "consulta")
    record_consumption(reserved, Interpretation([], 30, 20, 10))
    usage = AIUsageDaily.objects.get()
    assert usage.reserved_tokens == usage.consumed_tokens == 30
    assert usage.reserved_usd == Decimal("0.000040")


def test_parallel_admission_never_exceeds_daily_limit(identities, enabled):
    enabled.daily_requests = 1
    enabled.save()
    barrier = Barrier(2)

    def worker():
        close_old_connections()
        try:
            barrier.wait(timeout=5)
            try:
                reserve(identities["owner"], identities["tenant_a"], "consulta")
                return "accepted"
            except Throttled:
                return "limited"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(lambda _: worker(), range(2))) == ["accepted", "limited"]
    assert AIUsageDaily.objects.get().requests == 1


def test_simulated_provider_cannot_run_in_main_database(settings):
    settings.AI_TEST_PROVIDER = True
    settings.E2E_TEST_MODE = False
    with pytest.raises(ImproperlyConfigured):
        simulated()
