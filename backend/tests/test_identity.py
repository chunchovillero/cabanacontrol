from datetime import timedelta
from io import StringIO
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pytest
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.accounts.models import AuthThrottleBucket, User
from apps.audit.models import AuditEvent
from apps.tenants.models import Membership, Tenant
from tests.conftest import csrf_token, login_client, select_company

pytestmark = pytest.mark.django_db


def test_custom_user_and_email_normalization():
    user = User.objects.create_user("OWNER@EXAMPLE.INVALID", "long-password-for-testing")
    assert user.email == "owner@example.invalid"
    assert user.check_password("long-password-for-testing")
    with transaction.atomic(), pytest.raises(IntegrityError):
        User.objects.bulk_create([User(email="OWNER@EXAMPLE.INVALID")])


def test_login_requires_csrf_even_without_session(csrf_client, identities):
    response = csrf_client.post(
        "/api/v1/auth/login/",
        {"email": identities["owner"].email, "password": "Test-strong-passphrase-2026"},
        format="json",
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"


def test_login_rotates_csrf_and_session_cookie_is_httponly(csrf_client, identities):
    old_token = csrf_token(csrf_client)
    response = login_client(csrf_client, "OWNER@EXAMPLE.INVALID")
    assert response.status_code == 200
    assert response.json()["active_tenant"] is None
    assert csrf_client.cookies["sessionid"]["httponly"]
    assert csrf_client.cookies["sessionid"]["samesite"] == "Lax"
    assert csrf_token(csrf_client) != old_token
    assert csrf_client.get("/api/v1/auth/me/").status_code == 200
    assert AuditEvent.objects.filter(action="login").exists()


def test_logout_requires_csrf_and_invalidates_session(csrf_client, identities):
    assert login_client(csrf_client).status_code == 200
    assert csrf_client.post("/api/v1/auth/logout/", {}, format="json").status_code == 403
    response = csrf_client.post(
        "/api/v1/auth/logout/", {}, format="json", HTTP_X_CSRFTOKEN=csrf_token(csrf_client)
    )
    assert response.status_code == 204
    assert csrf_client.get("/api/v1/auth/me/").status_code == 403


@pytest.mark.parametrize("email", ["owner@example.invalid", "missing@example.invalid"])
def test_login_error_does_not_reveal_account(email, csrf_client, identities):
    response = login_client(csrf_client, email, "wrong-password")
    assert response.status_code == 403
    assert response.json()["error"]["details"]["detail"] == "Correo o contraseña incorrectos."


def test_inactive_account_cannot_login(csrf_client, identities):
    user = identities["owner"]
    user.is_active = False
    user.save()
    assert login_client(csrf_client).status_code == 403


def test_account_rate_limit_persists_in_database(csrf_client, identities):
    for _ in range(5):
        assert login_client(csrf_client, password="wrong-password").status_code == 403
    response = login_client(csrf_client)
    assert response.status_code == 429
    assert int(response["Retry-After"]) > 0
    assert AuthThrottleBucket.objects.count() == 2
    assert all("owner" not in bucket.key for bucket in AuthThrottleBucket.objects.all())
    AuthThrottleBucket.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    assert login_client(csrf_client).status_code == 200


def test_ip_rate_limit_ignores_untrusted_forwarded_header(csrf_client, settings):
    settings.LOGIN_IP_LIMIT = 1
    token = csrf_token(csrf_client)
    for index in range(2):
        response = csrf_client.post(
            "/api/v1/auth/login/",
            {"email": f"unknown{index}@example.invalid", "password": "wrong-password"},
            format="json",
            HTTP_X_CSRFTOKEN=token,
            HTTP_X_FORWARDED_FOR=f"192.0.2.{index}",
        )
    assert response.status_code == 429


def test_login_rejects_untrusted_origin(csrf_client, identities):
    response = csrf_client.post(
        "/api/v1/auth/login/",
        {"email": identities["owner"].email, "password": "Test-strong-passphrase-2026"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token(csrf_client),
        HTTP_ORIGIN="https://attacker.example.invalid",
    )
    assert response.status_code == 403


def test_tenants_list_never_uses_client_tenant_id(csrf_client, identities):
    login_client(csrf_client)
    response = csrf_client.get(
        f"/api/v1/tenants/?tenant_id={identities['tenant_b'].pk}",
        HTTP_X_TENANT_ID=str(identities["tenant_b"].pk),
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["id"] == str(identities["tenant_a"].pk)


@pytest.mark.parametrize(
    "user_key,own_key,foreign_key",
    [("owner", "tenant_a", "tenant_b"), ("other", "tenant_b", "tenant_a")],
)
def test_tenant_id_tampering_both_directions(
    user_key, own_key, foreign_key, csrf_client, identities
):
    login_client(csrf_client, identities[user_key].email)
    foreign = identities[foreign_key]
    assert csrf_client.get(f"/api/v1/tenants/{foreign.pk}/").status_code == 404
    assert select_company(csrf_client, foreign).status_code == 404
    assert select_company(csrf_client, identities[own_key]).status_code == 200
    assert csrf_client.get(f"/api/v1/tenants/{foreign.pk}/memberships/").status_code == 404


def test_company_selection_requires_csrf(csrf_client, identities):
    login_client(csrf_client)
    assert (
        csrf_client.post(
            f"/api/v1/tenants/{identities['tenant_a'].pk}/select/", {}, format="json"
        ).status_code
        == 403
    )


def test_multiple_memberships_and_active_context(csrf_client, identities):
    Membership.objects.create(user=identities["owner"], tenant=identities["tenant_b"], role="staff")
    login_client(csrf_client)
    assert csrf_client.get("/api/v1/tenants/").json()["count"] == 2
    select_company(csrf_client, identities["tenant_b"])
    response = csrf_client.get("/api/v1/context/")
    assert response.json()["role"] == "staff"
    assert response.json()["id"] == str(identities["tenant_b"].pk)
    assert csrf_client.get("/api/v1/auth/me/").json()["active_tenant"]["role"] == "staff"


@pytest.mark.parametrize("kind", ["membership", "tenant", "user"])
def test_revoked_access_is_rechecked_on_next_request(kind, csrf_client, identities):
    login_client(csrf_client)
    select_company(csrf_client, identities["tenant_a"])
    if kind == "membership":
        identities["memberships"]["owner"].active = False
        identities["memberships"]["owner"].save()
    elif kind == "tenant":
        identities["tenant_a"].active = False
        identities["tenant_a"].save()
    else:
        identities["owner"].is_active = False
        identities["owner"].save()
    assert csrf_client.get("/api/v1/context/").status_code == 403
    assert "active_tenant_id" not in csrf_client.session


def test_tampered_session_tenant_is_not_trusted(csrf_client, identities):
    login_client(csrf_client)
    session = csrf_client.session
    session["active_tenant_id"] = str(identities["tenant_b"].pk)
    session.save()
    assert csrf_client.get("/api/v1/context/").status_code == 403
    assert csrf_client.get("/api/v1/auth/me/").json()["active_tenant"] is None


@pytest.mark.parametrize("role", ["staff", "manager"])
def test_only_owner_can_read_memberships(role, csrf_client, identities):
    login_client(csrf_client, identities[role].email)
    select_company(csrf_client, identities["tenant_a"])
    assert (
        csrf_client.get(f"/api/v1/tenants/{identities['tenant_a'].pk}/memberships/").status_code
        == 403
    )


def test_owner_membership_list_excludes_other_company(csrf_client, identities):
    login_client(csrf_client)
    select_company(csrf_client, identities["tenant_a"])
    response = csrf_client.get(f"/api/v1/tenants/{identities['tenant_a'].pk}/memberships/")
    assert response.status_code == 200
    assert response.json()["count"] == 3
    assert str(identities["other"].pk) not in str(response.json())
    assert "email" not in response.content.decode()


def test_role_change_takes_effect_immediately(csrf_client, identities):
    login_client(csrf_client)
    select_company(csrf_client, identities["tenant_a"])
    membership = identities["memberships"]["owner"]
    membership.role = "staff"
    membership.save()
    assert (
        csrf_client.get(f"/api/v1/tenants/{identities['tenant_a'].pk}/memberships/").status_code
        == 403
    )


def test_platform_admin_has_no_implicit_tenant_access(csrf_client, identities):
    login_client(csrf_client, identities["platform"].email)
    assert csrf_client.get("/api/v1/tenants/").json()["count"] == 0
    assert csrf_client.get(f"/api/v1/tenants/{identities['tenant_a'].pk}/").status_code == 404
    assert select_company(csrf_client, identities["tenant_a"]).status_code == 404


def test_platform_membership_access_is_audited(csrf_client, identities):
    Membership.objects.create(
        user=identities["platform"], tenant=identities["tenant_a"], role="owner"
    )
    login_client(csrf_client, identities["platform"].email)
    select_company(csrf_client, identities["tenant_a"])
    csrf_client.get(f"/api/v1/tenants/{identities['tenant_a'].pk}/")
    assert AuditEvent.objects.filter(
        actor=identities["platform"], action="platform_tenant_read", tenant=identities["tenant_a"]
    ).exists()


def test_relogin_clears_previous_tenant_context(csrf_client, identities):
    login_client(csrf_client)
    select_company(csrf_client, identities["tenant_a"])
    response = login_client(csrf_client, identities["other"].email)
    assert response.status_code == 200
    assert response.json()["active_tenant"] is None
    assert csrf_client.get("/api/v1/context/").status_code == 403


def test_tenant_fields_and_membership_constraints(identities):
    tenant = Tenant(name="Temporal", timezone="not/a/timezone")
    with pytest.raises(ValidationError):
        tenant.full_clean()
    with transaction.atomic(), pytest.raises(IntegrityError):
        Membership.objects.create(
            user=identities["owner"], tenant=identities["tenant_a"], role="manager"
        )
    with transaction.atomic(), pytest.raises(IntegrityError):
        Membership.objects.create(
            user=identities["owner"], tenant=identities["tenant_b"], role="admin"
        )


def test_password_reset_generic_response_and_private_email_link(csrf_client, identities):
    token = csrf_token(csrf_client)
    path = "/api/v1/auth/password-reset/"
    response = csrf_client.post(
        path, {"email": "owner@example.invalid"}, format="json", HTTP_X_CSRFTOKEN=token
    )
    unknown = csrf_client.post(
        path, {"email": "missing@example.invalid"}, format="json", HTTP_X_CSRFTOKEN=token
    )
    assert response.status_code == unknown.status_code == 200
    assert response.json() == unknown.json()
    assert len(mail.outbox) == 1
    link = next(line for line in mail.outbox[0].body.splitlines() if "/restablecer#" in line)
    assert not urlsplit(link).query
    params = parse_qs(urlsplit(link).fragment)
    assert params["uid"] and params["token"]


@pytest.mark.parametrize(
    "path", ["/api/v1/auth/password-reset/", "/api/v1/auth/password-reset/confirm/"]
)
def test_anonymous_password_reset_requires_csrf(path, csrf_client):
    assert csrf_client.post(path, {}, format="json").status_code == 403


def test_password_reset_single_use_invalidates_existing_session(csrf_client, identities):
    user = identities["owner"]
    login_client(csrf_client)
    user.refresh_from_db()
    token = default_token_generator.make_token(user)
    data = {
        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
        "token": token,
        "password": "New-test-passphrase-2026!",
    }
    response = csrf_client.post(
        "/api/v1/auth/password-reset/confirm/",
        data,
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token(csrf_client),
    )
    assert response.status_code == 200
    assert csrf_client.get("/api/v1/auth/me/").status_code == 403
    user.refresh_from_db()
    assert user.check_password(data["password"])
    assert (
        csrf_client.post(
            "/api/v1/auth/password-reset/confirm/",
            data,
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token(csrf_client),
        ).status_code
        == 400
    )


@pytest.mark.parametrize(
    "uid,token", [("invalid", "bad"), ("!!!", "bad"), ("bm90LWEtdXVpZA", "bad")]
)
def test_invalid_reset_tokens_fail_safely(uid, token, csrf_client):
    response = csrf_client.post(
        "/api/v1/auth/password-reset/confirm/",
        {"uid": uid, "token": token, "password": "New-test-passphrase-2026!"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token(csrf_client),
    )
    assert response.status_code == 400


def test_expired_token_and_weak_password_rejected(csrf_client, identities, settings):
    user = identities["owner"]
    token = default_token_generator.make_token(user)
    data = {"uid": urlsafe_base64_encode(force_bytes(user.pk)), "token": token, "password": "1234"}
    path = "/api/v1/auth/password-reset/confirm/"
    assert (
        csrf_client.post(
            path, data, format="json", HTTP_X_CSRFTOKEN=csrf_token(csrf_client)
        ).status_code
        == 400
    )
    data["password"] = "New-test-passphrase-2026!"
    settings.PASSWORD_RESET_TIMEOUT = -1
    assert (
        csrf_client.post(
            path, data, format="json", HTTP_X_CSRFTOKEN=csrf_token(csrf_client)
        ).status_code
        == 400
    )


def test_schema_is_authenticated_and_generated(csrf_client, identities):
    assert csrf_client.get("/api/v1/schema/").status_code == 403
    login_client(csrf_client)
    response = csrf_client.get("/api/v1/schema/?format=json")
    assert response.status_code == 200
    assert "/api/v1/auth/login/" in response.json()["paths"]


def test_create_account_command_uses_password_validation_and_audit():
    with patch(
        "apps.accounts.management.commands.create_account.getpass",
        return_value="Fictional-strong-passphrase-2026!",
    ):
        call_command("create_account", email="new@example.invalid", stdout=StringIO())
    user = User.objects.get(email="new@example.invalid")
    assert not user.is_superuser and not user.is_platform_admin
    assert AuditEvent.objects.filter(action="account_created_cli", actor=user).exists()


def test_create_tenant_and_membership_commands(identities):
    call_command(
        "create_tenant",
        name="Empresa ficticia C",
        owner_email=identities["owner"].email,
        stdout=StringIO(),
    )
    tenant = Tenant.objects.get(name="Empresa ficticia C")
    assert Membership.objects.get(tenant=tenant, user=identities["owner"]).role == "owner"
    call_command(
        "add_membership",
        user_email=identities["staff"].email,
        tenant_id=str(tenant.pk),
        role="staff",
        stdout=StringIO(),
    )
    with pytest.raises(CommandError):
        call_command(
            "add_membership",
            user_email=identities["staff"].email,
            tenant_id=str(tenant.pk),
            role="owner",
            stdout=StringIO(),
        )
    assert Membership.objects.get(tenant=tenant, user=identities["staff"]).role == "staff"
