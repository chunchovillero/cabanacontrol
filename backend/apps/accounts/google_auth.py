import base64
import json
import time
from dataclasses import dataclass
from threading import Lock

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.hashes import SHA256
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed

GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
_cache: tuple[float, dict] | None = None
_cache_lock = Lock()


@dataclass(frozen=True)
class GoogleIdentity:
    subject: str
    email: str
    first_name: str
    last_name: str


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _json_part(value: str) -> dict:
    try:
        result = json.loads(_decode(value))
    except (ValueError, TypeError) as exc:
        raise AuthenticationFailed("No fue posible validar la cuenta de Google.") from exc
    if not isinstance(result, dict):
        raise AuthenticationFailed("No fue posible validar la cuenta de Google.")
    return result


def _keys() -> dict:
    global _cache
    now = time.time()
    with _cache_lock:
        if _cache and _cache[0] > now:
            return _cache[1]
        try:
            response = httpx.get(GOOGLE_CERTS_URL, timeout=5, follow_redirects=False)
            response.raise_for_status()
            body = response.json()
            keys = {item["kid"]: item for item in body["keys"] if item.get("kty") == "RSA"}
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise AuthenticationFailed("Google no está disponible. Intenta nuevamente.") from exc
        max_age = 3600
        for directive in response.headers.get("cache-control", "").split(","):
            if directive.strip().startswith("max-age="):
                try:
                    max_age = min(max(int(directive.split("=", 1)[1]), 60), 86400)
                except ValueError:
                    pass
        _cache = (now + max_age, keys)
        return keys


def verify_google_credential(credential: str) -> GoogleIdentity:
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        raise AuthenticationFailed("El acceso con Google no está configurado.")
    try:
        encoded_header, encoded_payload, encoded_signature = credential.split(".")
    except ValueError as exc:
        raise AuthenticationFailed("No fue posible validar la cuenta de Google.") from exc
    header = _json_part(encoded_header)
    payload = _json_part(encoded_payload)
    if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
        raise AuthenticationFailed("No fue posible validar la cuenta de Google.")
    key = _keys().get(header["kid"])
    if not key:
        global _cache
        _cache = None
        key = _keys().get(header["kid"])
    if not key:
        raise AuthenticationFailed("No fue posible validar la cuenta de Google.")
    try:
        public_key = rsa.RSAPublicNumbers(
            int.from_bytes(_decode(key["e"]), "big"), int.from_bytes(_decode(key["n"]), "big")
        ).public_key()
        public_key.verify(
            _decode(encoded_signature),
            f"{encoded_header}.{encoded_payload}".encode(),
            padding.PKCS1v15(),
            SHA256(),
        )
    except (InvalidSignature, ValueError, TypeError) as exc:
        raise AuthenticationFailed("No fue posible validar la cuenta de Google.") from exc
    now = int(time.time())
    if (
        payload.get("aud") != settings.GOOGLE_OAUTH_CLIENT_ID
        or payload.get("iss") not in GOOGLE_ISSUERS
        or not isinstance(payload.get("exp"), int)
        or payload["exp"] <= now
        or payload["exp"] > now + 3700
        or payload.get("email_verified") is not True
        or not isinstance(payload.get("sub"), str)
        or not isinstance(payload.get("email"), str)
    ):
        raise AuthenticationFailed("No fue posible validar la cuenta de Google.")
    email = payload["email"].strip().lower()
    if not email or len(email) > 254:
        raise AuthenticationFailed("No fue posible validar la cuenta de Google.")
    return GoogleIdentity(
        subject=payload["sub"],
        email=email,
        first_name=str(payload.get("given_name", ""))[:150],
        last_name=str(payload.get("family_name", ""))[:150],
    )
