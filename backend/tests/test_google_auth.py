import base64
import json
import time
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.hashes import SHA256
from rest_framework.exceptions import AuthenticationFailed

from apps.accounts.google_auth import verify_google_credential


def encoded(value):
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


@pytest.fixture
def google_token(settings):
    settings.GOOGLE_OAUTH_CLIENT_ID = "client.apps.googleusercontent.com"
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = private_key.public_key().public_numbers()
    jwk = {
        "kid": "test-key",
        "kty": "RSA",
        "e": encoded(numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")),
        "n": encoded(numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")),
    }

    def make(**overrides):
        header = encoded(json.dumps({"alg": "RS256", "kid": "test-key"}).encode())
        payload = {
            "aud": settings.GOOGLE_OAUTH_CLIENT_ID,
            "iss": "https://accounts.google.com",
            "exp": int(time.time()) + 600,
            "email_verified": True,
            "sub": "google-subject",
            "email": "Person@Example.invalid",
            "given_name": "Persona",
            "family_name": "Google",
            **overrides,
        }
        body = encoded(json.dumps(payload).encode())
        signature = private_key.sign(f"{header}.{body}".encode(), padding.PKCS1v15(), SHA256())
        return f"{header}.{body}.{encoded(signature)}"

    with patch("apps.accounts.google_auth._keys", return_value={"test-key": jwk}):
        yield make


def test_verified_google_token_is_accepted(google_token):
    identity = verify_google_credential(google_token())
    assert identity.email == "person@example.invalid"
    assert identity.first_name == "Persona" and identity.last_name == "Google"


@pytest.mark.parametrize(
    "claim",
    [
        {"aud": "another-client"},
        {"iss": "https://attacker.invalid"},
        {"exp": 1},
        {"email_verified": False},
    ],
)
def test_invalid_google_claims_are_rejected(google_token, claim):
    with pytest.raises(AuthenticationFailed):
        verify_google_credential(google_token(**claim))


def test_modified_google_signature_is_rejected(google_token):
    token = google_token()
    with pytest.raises(AuthenticationFailed):
        verify_google_credential(token[:-2] + "aa")
