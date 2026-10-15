import json

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from rest_framework.exceptions import APIException


class WhatsAppUnavailable(APIException):
    status_code = 503
    default_detail = "WhatsApp no está disponible. Continúa con la bandeja manual."


def keyring():
    try:
        keys = json.loads(settings.WHATSAPP_ENCRYPTION_KEYS)
        if not isinstance(keys, dict) or not keys:
            raise ValueError
        return {version: Fernet(key.encode()) for version, key in keys.items()}
    except (ValueError, TypeError, AttributeError):
        raise WhatsAppUnavailable() from None


def encrypt_token(connection, token):
    version = settings.WHATSAPP_ACTIVE_KEY_VERSION
    keys = keyring()
    if version not in keys or "." in version:
        raise WhatsAppUnavailable()
    plaintext = json.dumps(
        {"connection": str(connection.pk), "tenant": str(connection.tenant_id), "token": token}
    ).encode()
    return version + "." + keys[version].encrypt(plaintext).decode()


def decrypt_token(connection):
    try:
        version, ciphertext = connection.access_token_ciphertext.split(".", 1)
        value = json.loads(keyring()[version].decrypt(ciphertext.encode()))
        if value["tenant"] != str(connection.tenant_id) or value["connection"] != str(
            connection.pk
        ):
            raise ValueError
        return value["token"]
    except (InvalidToken, ValueError, KeyError, TypeError):
        raise WhatsAppUnavailable() from None
