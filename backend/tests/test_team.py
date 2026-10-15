import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from hashlib import sha256
from threading import Barrier

import pytest
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.tenants.member_services import (
    MemberConflict,
    accept_invitation,
    change_membership,
    create_invitation,
    revoke_invitation,
)
from apps.tenants.models import Invitation, Membership
from tests.conftest import csrf_token, login_client, select_company

pytestmark = pytest.mark.django_db


def invite(identities, email="new@example.invalid", role="staff"):
    return create_invitation(
        actor=identities["owner"], tenant=identities["tenant_a"], email=email, role=role
    )


def accept(token, actor=None, mode="new", **extra):
    data = {"token": token, "mode": mode}
    if mode == "new":
        data.update(first_name="Persona invitada", password="Fresh-fictional-passphrase-2026!")
    data.update(extra)
    return accept_invitation(actor=actor or AnonymousUser(), data=data)


def test_new_account_is_created_only_with_valid_invitation_and_token_is_not_stored(identities):
    invitation, token = invite(identities)
    assert invitation.token_hash == sha256(token.encode()).hexdigest()
    assert len(token) == 43 and token not in str(invitation.__dict__)
    membership = accept(token)
    assert membership.role == "staff" and membership.tenant == identities["tenant_a"]
    assert membership.user.check_password("Fresh-fictional-passphrase-2026!")
    invitation.refresh_from_db()
    assert invitation.state == "accepted" and invitation.accepted_by == membership.user
    assert not membership.user.is_platform_admin and not membership.user.is_superuser
    assert not AuditEvent.objects.filter(after__icontains=token).exists()
    with pytest.raises(ValidationError):
        accept(token)
    assert User.objects.filter(email="new@example.invalid").count() == 1


@pytest.mark.parametrize(
    "invalid", ["revoked", "expired", "altered", "company_inactive", "inviter_revoked"]
)
def test_unavailable_invitations_never_create_accounts(identities, invalid):
    invitation, token = invite(identities)
    if invalid == "revoked":
        revoke_invitation(
            actor=identities["owner"], tenant=identities["tenant_a"], invitation_id=invitation.pk
        )
    elif invalid == "expired":
        Invitation.objects.filter(pk=invitation.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
    elif invalid == "altered":
        token = "a" * 43
    elif invalid == "company_inactive":
        identities["tenant_a"].active = False
        identities["tenant_a"].save()
    else:
        identities["memberships"]["owner"].active = False
        identities["memberships"]["owner"].save()
    with pytest.raises(ValidationError):
        accept(token)
    assert not User.objects.filter(email="new@example.invalid").exists()


def test_existing_account_requires_own_session_and_keeps_password_and_other_company(identities):
    invitation, token = invite(identities, "other@example.invalid", "manager")
    original_password = identities["other"].password
    with pytest.raises(MemberConflict):
        accept(token)
    with pytest.raises(PermissionDenied):
        accept(token, actor=identities["staff"], mode="existing")
    with pytest.raises(PermissionDenied):
        accept(token, mode="existing")
    membership = accept(token, actor=identities["other"], mode="existing")
    identities["other"].refresh_from_db()
    assert identities["other"].password == original_password
    assert membership.role == "manager"
    assert Membership.objects.get(user=identities["other"], tenant=identities["tenant_b"]).active


def test_weak_password_rolls_back_account_and_invitation_remains_available(identities):
    invitation, token = invite(identities)
    with pytest.raises(ValidationError):
        accept(token, password="123")
    assert not User.objects.filter(email="new@example.invalid").exists()
    invitation.refresh_from_db()
    assert invitation.state == "pending"
    accept(token)


def test_change_revoke_and_reactivate_is_tenant_scoped_and_protects_owners(identities):
    member = identities["memberships"]["staff"]
    data = {"role": "manager", "active": False, "expected_role": "staff", "expected_active": True}
    changed = change_membership(
        actor=identities["owner"], tenant=identities["tenant_a"], membership_id=member.pk, data=data
    )
    assert not changed.active
    assert identities["staff"].is_active
    with pytest.raises(MemberConflict):
        change_membership(
            actor=identities["owner"],
            tenant=identities["tenant_a"],
            membership_id=member.pk,
            data=data,
        )
    for name in ("owner",):
        with pytest.raises(PermissionDenied):
            change_membership(
                actor=identities["owner"],
                tenant=identities["tenant_a"],
                membership_id=identities["memberships"][name].pk,
                data=data,
            )
    invitation, token = invite(identities, "staff@example.invalid", "staff")
    accept(token, actor=identities["staff"], mode="existing")
    changed.refresh_from_db()
    assert changed.active and changed.role == "staff"


@pytest.mark.parametrize("who", ["staff", "manager", "other", "platform"])
def test_only_actual_owner_can_invite(identities, who):
    with pytest.raises(PermissionDenied):
        create_invitation(
            actor=identities[who],
            tenant=identities["tenant_a"],
            email="new@example.invalid",
            role="staff",
        )


def test_expired_invite_can_be_replaced_but_duplicate_pending_is_rejected(identities):
    invitation, token = invite(identities)
    with pytest.raises(ValidationError):
        invite(identities)
    Invitation.objects.filter(pk=invitation.pk).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    newer, replacement = invite(identities)
    assert replacement != token and newer.pk != invitation.pk
    invitation.refresh_from_db()
    assert invitation.state == "expired"


def test_api_enforces_csrf_context_scope_and_masks_public_preview(identities, csrf_client):
    login_client(csrf_client)
    select_company(csrf_client, identities["tenant_a"])
    payload = {"email": "new@example.invalid", "role": "staff"}
    endpoint = "/api/v1/team/invitations/"
    assert csrf_client.post(endpoint, payload, format="json").status_code == 403
    assert (
        csrf_client.post(
            endpoint, payload, format="json", HTTP_X_CSRFTOKEN=csrf_token(csrf_client)
        ).status_code
        == 409
    )
    headers = {
        "HTTP_X_CSRFTOKEN": csrf_token(csrf_client),
        "HTTP_X_TENANT_CONTEXT": str(identities["tenant_a"].pk),
    }
    assert (
        csrf_client.post(
            endpoint, {**payload, "role": "owner"}, format="json", **headers
        ).status_code
        == 400
    )
    assert (
        csrf_client.post(
            endpoint,
            {**payload, "tenant_id": str(identities["tenant_b"].pk)},
            format="json",
            **headers,
        ).status_code
        == 400
    )
    response = csrf_client.post(endpoint, payload, format="json", **headers)
    assert response.status_code == 201
    token = response.json()["link"].split("#token=")[1]
    assert token not in csrf_client.get(endpoint).content.decode()
    public = APIClient(enforce_csrf_checks=True)
    assert (
        public.post("/api/v1/invitations/preview/", {"token": token}, format="json").status_code
        == 403
    )
    preview = public.post(
        "/api/v1/invitations/preview/",
        {"token": token},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token(public),
    )
    assert preview.status_code == 200
    assert preview.json()["email_hint"] == "n***@example.invalid"
    assert "new@example.invalid" not in preview.content.decode()
    foreign, _ = create_invitation(
        actor=identities["other"],
        tenant=identities["tenant_b"],
        email="foreign@example.invalid",
        role="staff",
    )
    assert (
        csrf_client.post(
            f"{endpoint}{foreign.pk}/revoke/", {}, format="json", **headers
        ).status_code
        == 404
    )
    assert (
        csrf_client.patch(
            f"/api/v1/team/memberships/{identities['memberships']['other'].pk}/",
            {"role": "staff", "active": False, "expected_role": "owner", "expected_active": True},
            format="json",
            **headers,
        ).status_code
        == 404
    )


def test_revocation_denies_next_request_but_preserves_other_company(identities, csrf_client):
    Membership.objects.create(user=identities["staff"], tenant=identities["tenant_b"], role="staff")
    login_client(csrf_client, email="staff@example.invalid")
    select_company(csrf_client, identities["tenant_a"])
    assert csrf_client.get("/api/v1/properties/").status_code == 200

    change_membership(
        actor=identities["owner"],
        tenant=identities["tenant_a"],
        membership_id=identities["memberships"]["staff"].pk,
        data={"role": "staff", "active": False, "expected_role": "staff", "expected_active": True},
    )
    assert csrf_client.get("/api/v1/properties/").status_code == 403
    assert select_company(csrf_client, identities["tenant_b"]).status_code == 200
    assert csrf_client.get("/api/v1/properties/").status_code == 200


def test_invitation_quota_and_strict_acceptance_inputs(identities, csrf_client):
    login_client(csrf_client)
    select_company(csrf_client, identities["tenant_a"])
    headers = {
        "HTTP_X_CSRFTOKEN": csrf_token(csrf_client),
        "HTTP_X_TENANT_CONTEXT": str(identities["tenant_a"].pk),
    }
    for index in range(10):
        response = csrf_client.post(
            "/api/v1/team/invitations/",
            {"email": f"quota-{index}@example.invalid", "role": "staff"},
            format="json",
            **headers,
        )
        assert response.status_code == 201
    assert (
        csrf_client.post(
            "/api/v1/team/invitations/",
            {"email": "quota-last@example.invalid", "role": "staff"},
            format="json",
            **headers,
        ).status_code
        == 429
    )
    public = APIClient(enforce_csrf_checks=True)
    token = response.json()["link"].split("#token=")[1]
    csrf = {"HTTP_X_CSRFTOKEN": csrf_token(public)}
    data = {
        "token": token,
        "mode": "new",
        "first_name": "Persona",
        "password": "Fresh-fictional-passphrase-2026!",
    }
    assert (
        public.post(
            "/api/v1/invitations/accept/", {**data, "role": "owner"}, format="json", **csrf
        ).status_code
        == 400
    )
    assert (
        public.post(
            "/api/v1/invitations/accept/",
            json.dumps({**data, "first_name": "\ud800"}),
            content_type="application/json",
            **csrf,
        ).status_code
        == 400
    )
    assert (
        public.post("/api/v1/invitations/accept/", data, format="json", **csrf).status_code == 200
    )
    assert (
        public.post("/api/v1/invitations/accept/", data, format="json", **csrf).status_code == 400
    )


def test_pending_invitation_cap(identities):
    for index in range(25):
        invite(identities, f"pending-{index}@example.invalid")
    with pytest.raises(ValidationError):
        invite(identities, "pending-extra@example.invalid")
    assert Invitation.objects.filter(state="pending").count() == 25


@pytest.mark.django_db(transaction=True)
def test_simultaneous_accepts_create_exactly_one_account_membership(identities):
    invitation, token = invite(identities)
    barrier = Barrier(2)

    def worker():
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            accept(token)
            return "accepted"
        except ValidationError:
            return "unavailable"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: worker(), range(2)))
    assert sorted(outcomes) == ["accepted", "unavailable"]
    assert User.objects.filter(email="new@example.invalid").count() == 1
    assert (
        Membership.objects.filter(
            user__email="new@example.invalid", tenant=identities["tenant_a"]
        ).count()
        == 1
    )


@pytest.mark.django_db(transaction=True)
def test_accept_and_revoke_cannot_both_succeed(identities):
    invitation, token = invite(identities)
    barrier = Barrier(2)

    def worker(operation):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            if operation == "accept":
                accept(token)
            else:
                revoke_invitation(
                    actor=identities["owner"],
                    tenant=identities["tenant_a"],
                    invitation_id=invitation.pk,
                )
            return operation
        except (ValidationError, MemberConflict):
            return "blocked"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(worker, ["accept", "revoke"]))
    assert outcomes.count("blocked") == 1
    invitation.refresh_from_db()
    assert invitation.state in ("accepted", "revoked")
    assert User.objects.filter(email="new@example.invalid").exists() == (
        invitation.state == "accepted"
    )


def test_deactivation_revokes_pending_reactivation_link(identities):
    member = identities["memberships"]["staff"]
    member.active = False
    member.save(update_fields=["active"])
    invitation, token = invite(identities, "staff@example.invalid")
    change_membership(
        actor=identities["owner"],
        tenant=identities["tenant_a"],
        membership_id=member.pk,
        data={
            "role": "manager",
            "active": False,
            "expected_role": "staff",
            "expected_active": False,
        },
    )
    with pytest.raises(ValidationError):
        accept(token, actor=identities["staff"], mode="existing")
    invitation.refresh_from_db()
    assert invitation.state == "revoked"
