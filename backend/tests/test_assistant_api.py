import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from apps.assistant.models import AIUsageDaily, TenantAISettings
from apps.assistant.providers import Interpretation, OpenAIProvider, ProviderUnavailable
from apps.inquiries.models import Inquiry
from apps.reservations.services import local_today
from tests.conftest import csrf_token, login_client, select_company
from tests.test_reservations import setup as reservation_setup  # noqa: F401

pytestmark = pytest.mark.django_db(transaction=True)


def enter(client, identities, who="owner"):
    assert login_client(client, identities[who].email).status_code == 200
    assert select_company(client, identities["tenant_a"]).status_code == 200


def post(client, identities, path, data):
    return client.post(
        path,
        data,
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token(client),
        HTTP_X_TENANT_CONTEXT=str(identities["tenant_a"].pk),
    )


@pytest.fixture
def enabled(identities, settings):
    settings.AI_ENABLED = True
    settings.AI_TEST_PROVIDER = False
    settings.OPENAI_API_KEY = "fictional-key"
    settings.OPENAI_TEXT_MODEL = "test"
    settings.AI_PRICE_INPUT_USD_PER_MILLION = "1"
    settings.AI_PRICE_OUTPUT_USD_PER_MILLION = "1"
    TenantAISettings.objects.create(tenant=identities["tenant_a"], enabled=True)


def test_staff_can_consult_but_cannot_configure(csrf_client, identities, enabled):
    enter(csrf_client, identities, "staff")
    result = csrf_client.patch(
        "/api/v1/assistant/settings/",
        {"enabled": False},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token(csrf_client),
        HTTP_X_TENANT_CONTEXT=str(identities["tenant_a"].pk),
    )
    assert result.status_code == 403
    with patch("apps.assistant.views.get_provider") as provider:
        provider.return_value.interpret.return_value = Interpretation(
            [("clarify", json.dumps({"missing": ["dates"]}))], 15
        )
        result = post(
            csrf_client,
            identities,
            "/api/v1/assistant/messages/",
            {"text": "Consulta ficticia", "reviewed": True},
        )
    assert result.status_code == 200
    assert AIUsageDaily.objects.get().consumed_tokens == 15


def test_message_requires_csrf_context_and_review(csrf_client, identities, enabled):
    enter(csrf_client, identities)
    with patch("apps.assistant.views.get_provider") as provider:
        assert (
            csrf_client.post(
                "/api/v1/assistant/messages/", {"text": "hola", "reviewed": True}, format="json"
            ).status_code
            == 403
        )
        assert (
            post(
                csrf_client,
                identities,
                "/api/v1/assistant/messages/",
                {"text": "hola", "reviewed": False},
            ).status_code
            == 400
        )
        result = csrf_client.post(
            "/api/v1/assistant/messages/",
            {"text": "hola", "reviewed": True},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token(csrf_client),
        )
        assert result.status_code == 409
        provider.assert_not_called()


def test_provider_only_receives_review_text_not_original_or_guest_records(
    csrf_client, identities, enabled
):
    enter(csrf_client, identities)
    inquiry = Inquiry.objects.create(
        tenant=identities["tenant_a"],
        created_by=identities["owner"],
        channel="phone",
        original_text="Original reservado",
        review_text="",
    )
    with patch("apps.inquiries.views.get_provider") as provider:
        provider.return_value.interpret.return_value = Interpretation(
            [("clarify", json.dumps({"missing": ["dates"]}))]
        )
        result = post(
            csrf_client,
            identities,
            f"/api/v1/inquiries/{inquiry.pk}/analyze/",
            {"revision": 1, "text": "2 personas email@example.invalid", "reviewed": True},
        )
        args = provider.return_value.interpret.call_args.args
    assert result.status_code == 200
    assert "Original" not in str(args) and "example" not in str(args)


def test_revoked_membership_and_foreign_inquiry(csrf_client, identities):
    enter(csrf_client, identities)
    other = Inquiry.objects.create(
        tenant=identities["tenant_b"],
        created_by=identities["other"],
        channel="phone",
        original_text="Contenido ajeno",
    )
    assert csrf_client.get(f"/api/v1/inquiries/{other.pk}/").status_code == 404
    membership = identities["memberships"]["owner"]
    membership.active = False
    membership.save()
    assert csrf_client.get("/api/v1/assistant/capabilities/").status_code == 403


def test_sdk_uses_strict_readonly_tools_store_false_and_no_retries(identities, enabled):
    response = SimpleNamespace(
        status="completed",
        usage=SimpleNamespace(total_tokens=10),
        output=[
            SimpleNamespace(type="function_call", name="clarify", arguments='{"missing":["year"]}')
        ],
    )
    with patch("apps.assistant.providers.AsyncOpenAI") as sdk:
        sdk.return_value.__aenter__.return_value.responses.create = AsyncMock(return_value=response)
        result = OpenAIProvider().interpret(
            "Consulta revisada", local_today(identities["tenant_a"]), "America/Santiago", {}
        )
        kwargs = sdk.return_value.__aenter__.return_value.responses.create.call_args.kwargs
    assert result.tokens == 10
    assert kwargs["store"] is False and kwargs["parallel_tool_calls"] is False
    assert kwargs["max_output_tokens"] == 1200
    assert all(tool["strict"] for tool in kwargs["tools"])
    assert sdk.call_args.kwargs["max_retries"] == 0


def test_provider_has_a_whole_call_deadline(identities, enabled):
    async def slow_response(**kwargs):
        await asyncio.sleep(1)

    with (
        patch("apps.assistant.providers.AsyncOpenAI") as sdk,
        patch("apps.assistant.providers.PROVIDER_TIMEOUT_SECONDS", 0.01),
    ):
        sdk.return_value.__aenter__.return_value.responses.create = AsyncMock(
            side_effect=slow_response
        )
        with pytest.raises(ProviderUnavailable):
            OpenAIProvider().interpret(
                "Consulta", local_today(identities["tenant_a"]), "America/Santiago", {}
            )


def test_manual_whatsapp_selection_revalidates_without_provider(csrf_client, identities, request):
    properties, _, data = request.getfixturevalue("reservation_setup")
    enter(csrf_client, identities, "staff")
    payload = {
        "property_id": str(properties["a"].pk),
        "check_in": str(data["check_in"]),
        "check_out": str(data["check_out"]),
        "guests": 2,
    }
    with patch("apps.assistant.views.get_provider") as provider:
        response = post(csrf_client, identities, "/api/v1/assistant/whatsapp/", payload)
        assert response.status_code == 200
        message = response.json()["results"][0]["data"]["message"]
        assert "Precio por confirmar" in message
        payload["property_id"] = str(properties["b"].pk)
        assert (
            post(csrf_client, identities, "/api/v1/assistant/whatsapp/", payload).status_code == 404
        )
        provider.assert_not_called()
    assert not AIUsageDaily.objects.exists()
