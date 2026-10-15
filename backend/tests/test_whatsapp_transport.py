import logging
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from apps.whatsapp.logging import OmitWebhookVerification
from apps.whatsapp.models import Message
from apps.whatsapp.providers import SendFailure, send
from tests.test_whatsapp import wa  # noqa: F401

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize(
    "status,outcome", [(200, "accepted"), (429, "retry"), (500, "unknown"), (401, "failed")]
)
def test_transport_is_fixed_and_classifies_errors(request, status, outcome):
    connection, conversation = request.getfixturevalue("wa")
    from django.utils import timezone

    message = Message.objects.create(
        conversation=conversation,
        direction="outbound",
        text="Texto ficticio revisado",
        status="queued",
        occurred_at=timezone.now(),
    )
    response = httpx.Response(status, json={"messages": [{"id": "wamid.transport.fixture"}]})
    with patch("apps.whatsapp.providers.httpx.AsyncClient") as client:
        client.return_value.__aenter__.return_value.post = AsyncMock(return_value=response)
        if outcome == "accepted":
            assert send(connection, message) == "wamid.transport.fixture"
        else:
            with pytest.raises(SendFailure) as error:
                send(connection, message)
            assert error.value.uncertain == (outcome == "unknown")
            assert error.value.retry == (outcome == "retry")
        args, kwargs = client.return_value.__aenter__.return_value.post.call_args
        assert args[0].startswith("https://graph.facebook.com/")
        assert kwargs["json"]["to"] == conversation.contact_phone
        assert kwargs["json"]["text"]["body"] == message.text
        assert "tenant" not in kwargs["json"]
        assert client.call_args.kwargs["follow_redirects"] is False


def test_verification_token_is_not_logged():
    record = logging.LogRecord(
        "django.server",
        logging.INFO,
        "",
        0,
        "GET /webhooks/whatsapp/?hub.verify_token=private-fixture",
        (),
        None,
    )
    assert not OmitWebhookVerification().filter(record)
    record.msg = "GET /health/"
    assert OmitWebhookVerification().filter(record)
