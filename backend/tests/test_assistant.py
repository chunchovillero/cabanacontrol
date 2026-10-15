import json
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.http import Http404
from rest_framework.exceptions import Throttled

from apps.assistant.dispatcher import dispatch, read_context
from apps.assistant.models import TenantAISettings
from apps.assistant.privacy import mask_text
from apps.assistant.providers import ProviderUnavailable
from apps.assistant.schemas import function_definitions
from apps.assistant.services import reserve
from apps.reservations.services import local_today
from tests.test_reservations import setup  # noqa: F401

pytestmark = pytest.mark.django_db(transaction=True)


def invoke(identities, name, args, text="Consulta para 2027", previous=None):
    return dispatch(
        [(name, json.dumps(args))],
        actor=identities["owner"],
        tenant=identities["tenant_a"],
        text=text,
        previous=previous or {},
    )


def test_schemas_have_no_write_tools():
    for tool in function_definitions():
        assert tool["strict"]
        assert tool["parameters"]["additionalProperties"] is False
        assert set(tool["parameters"]["required"]) == set(tool["parameters"]["properties"])


@pytest.mark.parametrize("text", ["2027-01-15", "2027-01-20"])
def test_masks_preserve_dates(text):
    assert mask_text(text) == text


def test_masks_contacts():
    result = mask_text("mail@example.invalid RUT 12.345.678-5 +56 9 1234 5678")
    assert "example" not in result
    assert "345" not in result
    assert "5678" not in result


@pytest.mark.parametrize(
    "name,args",
    [
        ("confirm_reservation", {}),
        ("list_arrivals", {"date": "2027-01-15", "tenant_id": "other"}),
        ("list_arrivals", {"date": "no-fecha"}),
    ],
)
def test_rejects_untrusted_tools(identities, name, args):
    with pytest.raises(ProviderUnavailable):
        invoke(identities, name, args)


def test_context_actor_tenant_and_signature(identities):
    result = invoke(identities, "clarify", {"missing": ["year"]})
    assert read_context(result["context"], identities["owner"], identities["tenant_a"]) == {}
    for actor, tenant, token in [
        (identities["other"], identities["tenant_a"], result["context"]),
        (identities["owner"], identities["tenant_b"], result["context"]),
        (identities["owner"], identities["tenant_a"], "tampered"),
    ]:
        with pytest.raises(ProviderUnavailable):
            read_context(token, actor, tenant)


def test_availability_is_scoped_and_price_not_calculated(identities, setup):  # noqa: F811
    properties, _, data = setup
    args = {"check_in": str(data["check_in"]), "check_out": str(data["check_out"]), "guests": 3}
    result = invoke(identities, "search_available_properties", args)
    rows = result["results"][0]["data"]
    assert rows["total"] == 1
    assert rows["items"][0]["id"] == str(properties["a"].pk)
    assert rows["price_notice"] == "Precio por confirmar"
    args["property_id"] = str(properties["b"].pk)
    with pytest.raises(Http404):
        invoke(identities, "search_available_properties", args)


def test_missing_year_and_historical_balance_clarify(identities):
    result = invoke(
        identities,
        "search_available_properties",
        {"check_in": "2027-01-15", "check_out": "2027-01-20", "guests": 5},
        text="Del 15 al 20 de enero",
    )
    assert result["results"][0]["tool"] == "clarify"
    result = invoke(
        identities,
        "list_outstanding_balances",
        {"as_of_date": str(local_today(identities["tenant_a"]) - timedelta(days=1))},
    )
    assert "históricos" in result["results"][0]["data"]["messages"][0]


def test_disabled_fails_without_network(identities):
    with patch("apps.assistant.providers.AsyncOpenAI") as sdk:
        with pytest.raises(ProviderUnavailable):
            reserve(identities["owner"], identities["tenant_a"], "hola")
        sdk.assert_not_called()


def test_quota_conservative_failed_call_not_refunded(identities, settings):
    settings.AI_ENABLED = True
    settings.OPENAI_API_KEY = "fictitious-not-a-real-key"
    settings.OPENAI_TEXT_MODEL = "test-only"
    settings.AI_PRICE_INPUT_USD_PER_MILLION = "1"
    settings.AI_PRICE_OUTPUT_USD_PER_MILLION = "1"
    TenantAISettings.objects.create(tenant=identities["tenant_a"], enabled=True, daily_requests=1)
    reserve(identities["owner"], identities["tenant_a"], "consulta ficticia")
    with pytest.raises(Throttled):
        reserve(identities["owner"], identities["tenant_a"], "consulta ficticia")
