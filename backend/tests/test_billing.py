from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from io import StringIO
from threading import Barrier
from unittest.mock import patch

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, close_old_connections, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.billing.models import SubscriptionEvent, SubscriptionPlan, TenantSubscription
from apps.billing.services import CapacityExceeded, assign_plan, enable_limits, snapshot
from apps.properties.models import Property
from apps.properties.services import save_property
from apps.tenants.member_services import accept_invitation, change_membership, create_invitation
from apps.tenants.models import Membership
from tests.conftest import select_company
from tests.test_properties import DATA

pytestmark = pytest.mark.django_db


def assign(identities, code="trial", enable=True):
    tenant = identities["tenant_a"]
    if code == "trial":
        Membership.objects.filter(tenant=tenant).exclude(role="owner").update(active=False)
    sub = assign_plan(
        actor=identities["platform"], tenant=tenant, code=code, reason="Prueba ficticia"
    )
    if enable:
        enable_limits(actor=identities["platform"], tenant=tenant, reason="Uso revisado")
    return sub


def cabin(identities, code="CAB-1", **extra):
    return save_property(
        actor=identities["owner"],
        tenant=identities["tenant_a"],
        data={**DATA, "code": code, **extra},
    )


def test_unassigned_company_retains_operation_and_assignment_does_not_enable(identities):
    assert snapshot(identities["tenant_a"])["status"] == "unassigned"
    assert not TenantSubscription.objects.exists()
    assign(identities, enable=False)
    cabin(identities)
    cabin(identities, "CAB-2")
    with pytest.raises(ValidationError):
        enable_limits(
            actor=identities["platform"], tenant=identities["tenant_a"], reason="Revisión"
        )
    assert not TenantSubscription.objects.get().enforced


def test_trial_one_cabin_and_one_owner_and_no_renewal_after_expiry(identities):
    sub = assign(identities)
    assert sub.trial_ends_at - sub.trial_started_at == timedelta(days=14)
    first = cabin(identities)
    with pytest.raises(CapacityExceeded):
        cabin(identities, "CAB-2")
    inactive = cabin(identities, "INACTIVE", active=False)
    with pytest.raises(CapacityExceeded):
        save_property(
            actor=identities["owner"],
            tenant=identities["tenant_a"],
            instance=inactive,
            data={"active": True},
        )
    assert snapshot(identities["tenant_a"])["usage"] == {"properties": 1, "members": 1}
    TenantSubscription.objects.filter(pk=sub.pk).update(
        trial_started_at=timezone.now() - timedelta(days=15),
        trial_ends_at=timezone.now() - timedelta(days=1),
    )
    assert snapshot(identities["tenant_a"])["status"] == "expired"
    save_property(
        actor=identities["owner"],
        tenant=identities["tenant_a"],
        instance=first,
        data={"name": "Edición permitida"},
    )
    with pytest.raises(CapacityExceeded):
        cabin(identities, "CAB-3")
    with pytest.raises(ValidationError):
        assign_plan(
            actor=identities["platform"],
            tenant=identities["tenant_a"],
            code="trial",
            reason="Otra prueba",
        )
    assign_plan(
        actor=identities["platform"],
        tenant=identities["tenant_a"],
        code="initial",
        reason="Cambio manual",
    )
    with pytest.raises(ValidationError):
        assign_plan(
            actor=identities["platform"],
            tenant=identities["tenant_a"],
            code="trial",
            reason="Otra prueba",
        )


def test_trial_invitation_acceptance_rolls_back_new_account_and_reactivation(identities):
    assign(identities)
    invitation, token = create_invitation(
        actor=identities["owner"],
        tenant=identities["tenant_a"],
        email="new-billing@example.invalid",
        role="staff",
    )
    with pytest.raises(CapacityExceeded):
        accept_invitation(
            actor=AnonymousUser(),
            data={
                "token": token,
                "mode": "new",
                "first_name": "Ficticio",
                "password": "New-fictional-passphrase-2026!",
            },
        )
    assert not User.objects.filter(email=invitation.email).exists()
    invitation.refresh_from_db()
    assert invitation.state == "pending"
    member = identities["memberships"]["staff"]
    with pytest.raises(CapacityExceeded):
        change_membership(
            actor=identities["owner"],
            tenant=identities["tenant_a"],
            membership_id=member.pk,
            data={
                "role": "staff",
                "active": True,
                "expected_role": "staff",
                "expected_active": False,
            },
        )
    member.refresh_from_db()
    assert not member.active


def test_downgrade_preserves_resources_and_only_blocks_increases(identities):
    assign(identities, "growth")
    properties = [cabin(identities, f"CAB-{index}") for index in range(4)]
    assign_plan(
        actor=identities["platform"],
        tenant=identities["tenant_a"],
        code="initial",
        reason="Cambio revisado",
    )
    assert snapshot(identities["tenant_a"])["over_capacity"]
    assert Property.objects.filter(active=True).count() == 4
    assert Membership.objects.filter(tenant=identities["tenant_a"], active=True).count() == 3
    save_property(
        actor=identities["owner"],
        tenant=identities["tenant_a"],
        instance=properties[0],
        data={"name": "Nombre nuevo"},
    )
    with pytest.raises(CapacityExceeded):
        cabin(identities, "CAB-NEW")


def test_cli_checks_capacity_and_requires_platform_actor_for_assignment(identities):
    assign(identities)
    with pytest.raises(CommandError):
        call_command(
            "add_membership",
            user_email=identities["other"].email,
            tenant_id=str(identities["tenant_a"].pk),
            role="staff",
            stdout=StringIO(),
        )
    with pytest.raises(CommandError):
        call_command(
            "manage_subscription",
            "assign",
            tenant_id=str(identities["tenant_a"].pk),
            actor_email=identities["owner"].email,
            plan="operator",
            reason="Intento",
            stdout=StringIO(),
        )
    output = StringIO()
    call_command(
        "manage_subscription", "review", tenant_id=str(identities["tenant_a"].pk), stdout=output
    )
    assert (
        '"members": 1' in output.getvalue() and identities["owner"].email not in output.getvalue()
    )
    inventory = StringIO()
    call_command("manage_subscription", "review", stdout=inventory)
    assert str(identities["tenant_a"].pk) in inventory.getvalue()
    assert str(identities["tenant_b"].pk) in inventory.getvalue()
    assert identities["owner"].email not in inventory.getvalue()
    call_command(
        "manage_subscription",
        "assign",
        tenant_id=str(identities["tenant_a"].pk),
        actor_email=identities["platform"].email,
        plan="initial",
        reason="Asignación revisada",
        stdout=StringIO(),
    )
    assert TenantSubscription.objects.get().plan.code == "initial"


def test_plan_versions_immutable_in_postgresql(identities):
    sub = assign(identities)
    with pytest.raises(IntegrityError), transaction.atomic():
        SubscriptionPlan.objects.filter(pk=sub.plan_id).update(member_limit=99)
    sub.plan.refresh_from_db()
    assert sub.plan.member_limit == 1
    assert SubscriptionEvent.objects.count() == 2


def test_trial_boundary_and_incomplete_dates_rejected_by_database(identities):
    sub = assign(identities)
    with patch("apps.billing.services.timezone.now", return_value=sub.trial_ends_at):
        assert snapshot(identities["tenant_a"])["status"] == "expired"
    with patch(
        "apps.billing.services.timezone.now",
        return_value=sub.trial_ends_at - timedelta(microseconds=1),
    ):
        assert snapshot(identities["tenant_a"])["status"] == "trial"
    with pytest.raises(IntegrityError), transaction.atomic():
        TenantSubscription.objects.filter(pk=sub.pk).update(trial_ends_at=None)


def test_enable_requires_assignment_and_is_idempotent(identities):
    with pytest.raises(ValidationError):
        enable_limits(
            actor=identities["platform"], tenant=identities["tenant_a"], reason="Uso revisado"
        )
    assign(identities)
    before = SubscriptionEvent.objects.count()
    call_command(
        "manage_subscription",
        "enable",
        tenant_id=str(identities["tenant_a"].pk),
        actor_email=identities["platform"].email,
        reason="Uso revisado",
        stdout=StringIO(),
    )
    assert SubscriptionEvent.objects.count() == before


@pytest.mark.parametrize("role", ["staff", "manager", "platform"])
def test_only_owner_reads_subscription_without_platform_bypass(identities, role):
    client = APIClient()
    client.force_login(identities[role])
    if role != "platform":
        select_company(client, identities["tenant_a"])
    assert client.get("/api/v1/billing/plan/").status_code == 403
    with pytest.raises(PermissionDenied):
        assign_plan(
            actor=identities["staff"],
            tenant=identities["tenant_a"],
            code="initial",
            reason="No autorizado",
        )


def test_plan_api_context_read_only_and_separate_companies(identities):
    assign(identities)
    client = APIClient()
    client.force_login(identities["owner"])
    select_company(client, identities["tenant_a"])
    response = client.get("/api/v1/billing/plan/")
    assert response.status_code == 200
    assert response.json()["subscription"]["plan"]["member_limit"] == 1
    assert len(response.json()["catalog"]) == 3
    assert (
        client.get(
            "/api/v1/billing/plan/", HTTP_X_TENANT_CONTEXT=str(identities["tenant_b"].pk)
        ).status_code
        == 409
    )
    assert (
        client.patch(
            "/api/v1/billing/plan/",
            {"plan": "operator"},
            format="json",
            HTTP_X_TENANT_CONTEXT=str(identities["tenant_a"].pk),
        ).status_code
        == 405
    )
    client.force_login(identities["other"])
    select_company(client, identities["tenant_b"])
    assert client.get("/api/v1/billing/plan/").json()["subscription"]["status"] == "unassigned"


@pytest.mark.django_db(transaction=True)
def test_last_property_slot_concurrent_creations(identities):
    assign(identities)
    barrier = Barrier(2)

    def worker(index):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            cabin(identities, f"RACE-{index}")
            return "created"
        except CapacityExceeded:
            return "limited"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(worker, range(2))) == ["created", "limited"]
    assert Property.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_last_member_slot_concurrent_invitation_acceptance(identities):
    Membership.objects.filter(tenant=identities["tenant_a"]).exclude(role="owner").update(
        active=False
    )
    assign(identities, "initial")
    tokens = [
        create_invitation(
            actor=identities["owner"],
            tenant=identities["tenant_a"],
            email=f"race-{index}@example.invalid",
            role="staff",
        )[1]
        for index in range(2)
    ]
    barrier = Barrier(2)

    def worker(token):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            accept_invitation(
                actor=AnonymousUser(),
                data={
                    "token": token,
                    "mode": "new",
                    "first_name": "Persona",
                    "password": "Race-fictional-passphrase-2026!",
                },
            )
            return "created"
        except CapacityExceeded:
            return "limited"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(worker, tokens)) == ["created", "limited"]
    assert User.objects.filter(email__startswith="race-").count() == 1
    assert Membership.objects.filter(tenant=identities["tenant_a"], active=True).count() == 2
