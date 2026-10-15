import asyncio
import re
import uuid

import httpx
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from apps.whatsapp.crypto import WhatsAppUnavailable, decrypt_token, keyring


def simulated():
    if not settings.WHATSAPP_TEST_PROVIDER:
        return False
    if not (
        settings.E2E_TEST_MODE and settings.DATABASES["default"]["NAME"] == "cabanacontrol_e2e"
    ):
        raise ImproperlyConfigured("WhatsApp simulado requiere la base E2E aislada.")
    return True


def ready():
    if simulated():
        return True
    try:
        keys = keyring()
    except WhatsAppUnavailable:
        return False
    return bool(
        settings.WHATSAPP_REAL_ENABLED
        and re.fullmatch(r"v\d+\.\d+", settings.WHATSAPP_GRAPH_VERSION)
        and settings.WHATSAPP_APP_SECRET
        and settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN
        and settings.WHATSAPP_ACTIVE_KEY_VERSION in keys
    )


class SendFailure(Exception):
    def __init__(self, code, *, retry=False, uncertain=False):
        self.code, self.retry, self.uncertain = code, retry, uncertain


def send(connection, message, template=None):
    if simulated():
        return "wamid.simulated." + uuid.uuid4().hex
    if not ready():
        raise WhatsAppUnavailable()
    token = decrypt_token(connection)
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": message.conversation.contact_phone,
    }
    if template:
        payload.update(
            type="template",
            template={"name": template.name, "language": {"code": template.language}},
        )
    else:
        payload.update(type="text", text={"body": message.text, "preview_url": False})

    async def request():
        try:
            async with (
                asyncio.timeout(25),
                httpx.AsyncClient(timeout=25, follow_redirects=False) as client,
            ):
                response = await client.post(
                    f"https://graph.facebook.com/{settings.WHATSAPP_GRAPH_VERSION}/{connection.phone_number_id}/messages",
                    headers={"Authorization": f"Bearer {token}"},
                    json=payload,
                )
            if response.status_code == 429:
                raise SendFailure("rate_limited", retry=True)
            if response.status_code >= 500:
                raise SendFailure("provider_unknown", uncertain=True)
            if not response.is_success:
                raise SendFailure("provider_rejected")
            result = response.json()["messages"][0]["id"]
            if not isinstance(result, str) or not 1 <= len(result) <= 250:
                raise ValueError
            return result
        except SendFailure:
            raise
        except (httpx.HTTPError, TimeoutError, ValueError, KeyError, IndexError, TypeError):
            raise SendFailure("delivery_unknown", uncertain=True) from None

    return asyncio.run(request())
