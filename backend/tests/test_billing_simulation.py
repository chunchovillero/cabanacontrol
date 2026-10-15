from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from io import StringIO
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.core.management import call_command
from django.db import IntegrityError, close_old_connections, transaction
from django.http import Http404
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.accounts.profile import SettingsConflict
from apps.billing.models import (
    CheckoutAttempt,
    PlanPrice,
    SaaSCharge,
    SimulatedContract,
    SimulationCompany,
    TenantSubscription,
)
from apps.billing.services import assign_plan, enable_limits
from apps.billing.simulation import (
    TERMS,
    accept_quote,
    manage_intent,
    month_end,
    prepare_company,
    prorate,
    quote,
    renew_due,
    simulate_result,
)
from apps.payments.models import Payment
from tests.conftest import csrf_token, login_client, select_company
from tests.test_billing import assign

pytestmark = pytest.mark.django_db
START = datetime(2026, 1, 31, 12, tzinfo=UTC)


@pytest.fixture(autouse=True)
def simulation_settings(settings):
    settings.DEBUG = True
    settings.BILLING_SIMULATION_ENABLED = True


@pytest.fixture
def company(identities):
    assign(identities)
    prepare_company(
        actor=identities["platform"], tenant=identities["tenant_a"], reason="Empresa ficticia"
    )
    return identities


def make_quote(company, code="initial", expected=0):
    return quote(
        actor=company["owner"], tenant=company["tenant_a"], code=code, expected_revision=expected
    )


def accept(company, attempt, key=None):
    return accept_quote(
        actor=company["owner"],
        tenant=company["tenant_a"],
        attempt_id=attempt.pk,
        key=key or uuid4(),
        terms=TERMS,
    )


def result(company, attempt, value="approved", event_id=None):
    return simulate_result(
        actor=company["owner"],
        tenant=company["tenant_a"],
        attempt_id=attempt.pk,
        event_id=event_id or uuid4(),
        result=value,
    )


def purchase(company, code="initial"):
    with patch("apps.billing.simulation.timezone.now", return_value=START):
        attempt = make_quote(company, code)
        accept(company, attempt)
        result(company, attempt)
    return SimulatedContract.objects.get(tenant=company["tenant_a"])


def intent(company, contract, operation, **extra):
    return manage_intent(
        actor=company["owner"],
        tenant=company["tenant_a"],
        operation=operation,
        expected_revision=contract.revision,
        **extra,
    )


@pytest.mark.parametrize("flag", ["DEBUG", "BILLING_SIMULATION_ENABLED"])
def test_disabled_environment_rejects_all_simulation(company, settings, flag):
    setattr(settings, flag, False)
    with pytest.raises(PermissionDenied):
        make_quote(company)
    with pytest.raises(PermissionDenied):
        prepare_company(
            actor=company["platform"], tenant=company["tenant_a"], reason="No permitido"
        )


def test_unmarked_company_and_owner_preparation_rejected(identities):
    assign(identities)
    with pytest.raises(PermissionDenied):
        make_quote(identities)
    with pytest.raises(PermissionDenied):
        prepare_company(actor=identities["owner"], tenant=identities["tenant_a"], reason="No")
    assert not SimulationCompany.objects.exists()


def test_purchase_consented_idempotent_and_guest_payments_untouched(company):
    guest_count = Payment.objects.count()
    attempt = make_quote(company)
    key = uuid4()
    accepted = accept(company, attempt, key)
    assert accepted.state == "pending" and not SaaSCharge.objects.exists()
    assert accept(company, attempt, key).pk == attempt.pk
    event_id = uuid4()
    result(company, attempt, event_id=event_id)
    result(company, attempt, event_id=event_id)
    result(company, attempt)
    assert SaaSCharge.objects.count() == 1
    assert SaaSCharge.objects.get().amount == Decimal("4500")
    assert Payment.objects.count() == guest_count
    contract = SimulatedContract.objects.get()
    assert contract.consent_by == company["owner"] and contract.terms_version == TERMS
    assert TenantSubscription.objects.get().plan.code == "initial"
    with pytest.raises(SettingsConflict):
        result(company, attempt, "rejected", event_id=event_id)


def test_pending_uncertain_rejected_never_grant_capacity(company):
    attempt = make_quote(company, "operator")
    accept(company, attempt)
    for state in ["uncertain", "pending"]:
        result(company, attempt, state)
        with pytest.raises(SettingsConflict):
            make_quote(company)
    result(company, attempt, "rejected")
    result(company, attempt, "approved")
    assert not SimulatedContract.objects.exists()
    assert TenantSubscription.objects.get().plan.code == "trial"
    assert not SaaSCharge.objects.exists()
    assert make_quote(company).state == "quoted"


def test_prorated_upgrade_and_calendar_anchor(company):
    contract = purchase(company)
    old_end = contract.period_end
    assert old_end == datetime(2026, 2, 28, 12, tzinfo=UTC)
    middle = contract.period_start + (old_end - contract.period_start) / 2
    with patch("apps.billing.simulation.timezone.now", return_value=middle):
        attempt = make_quote(company, "growth", contract.revision)
        assert attempt.amount == Decimal("2700")
        assert attempt.prior_price.amount == 4500 and attempt.target_end == old_end
        accept(company, attempt)
        result(company, attempt)
    contract.refresh_from_db()
    assert contract.price.amount == Decimal("9900") and contract.period_end == old_end
    assert contract.anchor == START
    assert month_end(START, 2) == datetime(2026, 3, 31, 12, tzinfo=UTC)
    assert month_end(datetime(2024, 1, 31, tzinfo=UTC), 1).day == 29


def test_round_half_up_and_zero_charge_upgrade(company):
    assert (
        prorate(
            Decimal(0),
            Decimal(1),
            START,
            START + timedelta(seconds=2),
            START + timedelta(seconds=1),
        )
        == 1
    )
    contract = purchase(company)
    with patch(
        "apps.billing.simulation.timezone.now",
        return_value=contract.period_end - timedelta(microseconds=1),
    ):
        attempt = make_quote(company, "growth", contract.revision)
        assert attempt.amount == 0
        accept(company, attempt)
        result(company, attempt)
    assert SaaSCharge.objects.count() == 1
    assert SimulatedContract.objects.get().price.plan.code == "growth"


def test_quote_expiry_wrong_terms_and_stale_revision(company):
    attempt = make_quote(company)
    with pytest.raises(ValidationError):
        accept_quote(
            actor=company["owner"],
            tenant=company["tenant_a"],
            attempt_id=attempt.pk,
            key=uuid4(),
            terms="wrong",
        )
    with patch("apps.billing.simulation.timezone.now", return_value=attempt.expires_at):
        with pytest.raises(SettingsConflict):
            accept(company, attempt)
    assert not SimulatedContract.objects.exists()


def test_manual_projection_change_requires_reconciliation(company):
    attempt = make_quote(company)
    accept(company, attempt)
    sub = TenantSubscription.objects.get()
    sub.save(update_fields=["updated_at"])
    assert result(company, attempt).state == "obsolete"
    assert not SaaSCharge.objects.exists()


def test_downgrade_renewal_idempotency_and_no_early_capacity_change(company):
    contract = purchase(company, "growth")
    with patch("apps.billing.simulation.timezone.now", return_value=START + timedelta(days=2)):
        contract = intent(company, contract, "downgrade", code="initial", terms=TERMS)
    assert TenantSubscription.objects.get().plan.code == "growth"
    with patch("apps.billing.simulation.timezone.now", return_value=contract.period_end):
        attempt = renew_due(actor=company["platform"], tenant=company["tenant_a"])
        assert attempt.amount == 4500
        assert renew_due(actor=company["platform"], tenant=company["tenant_a"]).pk == attempt.pk
        result(company, attempt)
    contract.refresh_from_db()
    assert contract.price.plan.code == "initial" and contract.next_price is None
    assert contract.period_index == 2 and contract.period_end == month_end(START, 2)
    assert SaaSCharge.objects.count() == 2


def test_cancel_finalize_keeps_capacity_and_resume_requires_consent(company):
    contract = purchase(company)
    with patch("apps.billing.simulation.timezone.now", return_value=START + timedelta(days=1)):
        contract = intent(company, contract, "cancel")
        with pytest.raises(ValidationError):
            intent(company, contract, "resume")
    with patch("apps.billing.simulation.timezone.now", return_value=contract.period_end):
        assert renew_due(actor=company["platform"], tenant=company["tenant_a"]) is None
    contract.refresh_from_db()
    assert contract.finalized and TenantSubscription.objects.get().plan.code == "initial"
    assert SaaSCharge.objects.count() == 1


def test_api_context_csrf_unknown_fields_false_consent_and_no_return_activation(company):
    client = APIClient(enforce_csrf_checks=True)
    login_client(client)
    select_company(client, company["tenant_a"])
    base = "/api/v1/billing/simulation/"
    headers = {
        "HTTP_X_CSRFTOKEN": csrf_token(client),
        "HTTP_X_TENANT_CONTEXT": str(company["tenant_a"].pk),
    }
    assert (
        client.post(
            base + "quotes/", {"code": "initial", "expected_revision": 0}, format="json"
        ).status_code
        == 403
    )
    assert (
        client.post(
            base + "quotes/",
            {"code": "initial", "expected_revision": 0, "amount": "1"},
            format="json",
            **headers,
        ).status_code
        == 400
    )
    response = client.post(
        base + "quotes/", {"code": "initial", "expected_revision": 0}, format="json", **headers
    )
    assert response.status_code == 201
    url = base + f"attempts/{response.json()['id']}/accept/"
    assert (
        client.post(
            url, {"key": str(uuid4()), "terms": TERMS, "consent": False}, format="json", **headers
        ).status_code
        == 400
    )
    assert client.get(base + "?approved=true").status_code == 200
    assert not SimulatedContract.objects.exists()
    assert client.get(base, HTTP_X_TENANT_CONTEXT=str(company["tenant_b"].pk)).status_code == 409
    client.force_login(company["staff"])
    assert client.get(base).status_code == 403


def test_price_versions_immutable_and_commands_do_not_create_cargos(company):
    with pytest.raises(IntegrityError), transaction.atomic():
        PlanPrice.objects.all().update(amount=1)
    call_command(
        "billing_simulation",
        "prepare",
        tenant_id=str(company["tenant_a"].pk),
        actor_email=company["platform"].email,
        reason="Solo prueba",
        stdout=StringIO(),
    )
    call_command(
        "billing_simulation",
        "renew",
        tenant_id=str(company["tenant_a"].pk),
        actor_email=company["platform"].email,
        stdout=StringIO(),
    )
    assert not SaaSCharge.objects.exists()


def test_rejected_renewal_needs_explicit_retry_and_then_only_one_period(company):
    contract = purchase(company)
    with patch("apps.billing.simulation.timezone.now", return_value=contract.period_end):
        failed = renew_due(actor=company["platform"], tenant=company["tenant_a"])
        result(company, failed, "rejected")
        assert renew_due(actor=company["platform"], tenant=company["tenant_a"]).pk == failed.pk
        retry = renew_due(actor=company["platform"], tenant=company["tenant_a"], retry=True)
        assert retry.pk != failed.pk and retry.retry_number == 1
        assert (
            renew_due(actor=company["platform"], tenant=company["tenant_a"], retry=True).pk
            == retry.pk
        )
        result(company, retry)
        result(company, failed)
    assert SaaSCharge.objects.count() == 2
    assert SimulatedContract.objects.get().period_index == 2


def test_resume_requires_correct_renewal_plan_and_stale_intents_rejected(company):
    contract = purchase(company, "growth")
    with patch("apps.billing.simulation.timezone.now", return_value=START + timedelta(days=1)):
        contract = intent(company, contract, "cancel")
        with pytest.raises(SettingsConflict):
            intent(company, contract, "resume", code="initial", terms=TERMS)
        old_revision = contract.revision
        contract = intent(company, contract, "resume", code="growth", terms=TERMS)
        assert not contract.cancel_at_end
        with pytest.raises(SettingsConflict):
            manage_intent(
                actor=company["owner"],
                tenant=company["tenant_a"],
                operation="cancel",
                expected_revision=old_revision,
            )


def test_late_upgrade_cannot_change_next_period(company):
    contract = purchase(company)
    with patch(
        "apps.billing.simulation.timezone.now",
        return_value=contract.period_end - timedelta(minutes=5),
    ):
        attempt = make_quote(company, "growth", contract.revision)
        accept(company, attempt)
    with patch("apps.billing.simulation.timezone.now", return_value=contract.period_end):
        assert result(company, attempt).state == "obsolete"
    assert SaaSCharge.objects.count() == 1
    assert TenantSubscription.objects.get().plan.code == "initial"


def test_idempotency_key_cannot_confirm_another_quote(company):
    first = make_quote(company)
    second = make_quote(company, "growth")
    key = uuid4()
    accept(company, first, key)
    with pytest.raises(SettingsConflict):
        accept(company, second, key)
    assert CheckoutAttempt.objects.filter(state="pending").count() == 1
    assert not SaaSCharge.objects.exists()


def test_foreign_attempt_is_not_visible_to_another_prepared_owner(company):
    attempt = make_quote(company)
    other_tenant = company["tenant_b"]
    assign_plan(actor=company["platform"], tenant=other_tenant, code="initial", reason="Ficticio")
    enable_limits(actor=company["platform"], tenant=other_tenant, reason="Uso revisado")
    prepare_company(actor=company["platform"], tenant=other_tenant, reason="Solo prueba")
    with pytest.raises(Http404):
        accept_quote(
            actor=company["other"],
            tenant=other_tenant,
            attempt_id=attempt.pk,
            key=uuid4(),
            terms=TERMS,
        )
    with pytest.raises(Http404):
        simulate_result(
            actor=company["other"],
            tenant=other_tenant,
            attempt_id=attempt.pk,
            event_id=uuid4(),
            result="approved",
        )
    assert not SaaSCharge.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_confirmation_and_approval_create_one_charge(company):
    attempt = make_quote(company)
    key = uuid4()
    barrier = Barrier(2)

    def worker(_):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            accept(company, attempt, key)
            result(company, attempt)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(worker, range(2)))
    assert SaaSCharge.objects.count() == 1 and SimulatedContract.objects.count() == 1
