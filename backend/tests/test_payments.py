from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from threading import Barrier
from uuid import uuid4

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, close_old_connections, transaction
from django.db.models.deletion import ProtectedError
from django.http import Http404
from django.utils import timezone
from PIL import Image
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.audit.models import AuditEvent
from apps.payments.models import Payment
from apps.payments.queries import received_for
from apps.payments.services import PaymentConflict, attach_receipt, record_payment, void_payment
from apps.reservations.queries import reservations_for_tenant
from apps.reservations.services import save_reservation, transition_reservation
from tests.test_reservations import enter, json_data, save, write
from tests.test_reservations import setup as reservation_setup  # noqa: F401

pytestmark = pytest.mark.django_db


@pytest.fixture
def booked(identities, request):
    fixture = request.getfixturevalue("reservation_setup")
    return save(identities, {**fixture[2], "status": "confirmed"})


@pytest.fixture
def data():
    return {
        "request_id": uuid4(),
        "amount": Decimal("50000.10"),
        "paid_at": timezone.now() - timedelta(minutes=1),
        "method": "transfer",
        "reference": "Referencia ficticia",
    }


def pay(identities, booked, data):
    return record_payment(
        actor=identities["staff"],
        tenant=identities["tenant_a"],
        reservation_id=booked.pk,
        data=data,
    )


def test_exact_sums_overpayment_and_void(identities, booked, data):
    first, _ = pay(identities, booked, data)
    second, _ = pay(
        identities, booked, {**data, "request_id": uuid4(), "amount": Decimal("100000.15")}
    )
    assert received_for(booked) == Decimal("150000.25")
    item = reservations_for_tenant(identities["tenant_a"]).get(pk=booked.pk)
    assert item.balance == 0 and item.payment_state == "paid"
    extra, _ = pay(identities, booked, {**data, "request_id": uuid4(), "amount": Decimal("0.10")})
    item = reservations_for_tenant(identities["tenant_a"]).get(pk=booked.pk)
    assert item.balance == Decimal("-0.10") and item.payment_state == "credit"
    void_payment(
        actor=identities["staff"],
        tenant=identities["tenant_a"],
        payment_id=extra.pk,
        reason="Corrección ficticia",
    )
    assert received_for(booked) == Decimal("150000.25")
    assert Payment.objects.count() == 3
    assert first.amount + second.amount == booked.total_amount


def test_request_retry_is_idempotent_and_mismatched_retry_conflicts(identities, booked, data):
    first, created = pay(identities, booked, data)
    repeated, created_again = pay(identities, booked, data)
    assert first.pk == repeated.pk and created and not created_again
    with pytest.raises(PaymentConflict):
        pay(identities, booked, {**data, "amount": Decimal("2.00")})
    assert Payment.objects.count() == 1
    assert AuditEvent.objects.filter(action="payment_recorded").count() == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("amount", 0),
        ("amount", -1),
        ("amount", 1.25),
        ("amount", "NaN"),
        ("amount", "0.001"),
        ("amount", None),
        ("request_id", "bad"),
        ("reference", None),
        ("method", "bad"),
        ("currency", "USD"),
        ("tenant_id", "bad"),
    ],
)
def test_invalid_values_rejected(identities, booked, data, field, value):
    with pytest.raises(ValidationError):
        pay(identities, booked, {**data, field: value})


@pytest.mark.parametrize("status", ["draft", "cancelled", "no_show"])
def test_disallowed_reservation_states(identities, booked, data, status):
    booked.status = status
    booked.save()
    with pytest.raises(ValidationError):
        pay(identities, booked, data)


@pytest.mark.parametrize("status", ["pending", "confirmed", "checked_in", "checked_out"])
def test_allowed_states_and_no_automatic_confirmation(identities, booked, data, status):
    booked.status = status
    booked.hold_until = timezone.now() + timedelta(hours=1) if status == "pending" else None
    booked.save()
    pay(identities, booked, data)
    booked.refresh_from_db()
    assert booked.status == status


def test_price_reduction_makes_credit_and_cancel_keeps_payments(identities, booked, data):
    payment, _ = pay(identities, booked, data)
    save_reservation(
        actor=identities["owner"],
        tenant=identities["tenant_a"],
        instance=booked,
        data={"total_amount": "10000.00"},
    )
    item = reservations_for_tenant(identities["tenant_a"]).get(pk=booked.pk)
    assert item.balance == Decimal("-40000.10")
    transition_reservation(
        actor=identities["owner"],
        tenant=identities["tenant_a"],
        instance=booked,
        status="cancelled",
        reason="Cambio ficticio",
    )
    assert received_for(booked) == payment.amount
    repeated, created = pay(identities, booked, data)
    assert repeated.pk == payment.pk and not created
    void_payment(
        actor=identities["staff"],
        tenant=identities["tenant_a"],
        payment_id=payment.pk,
        reason="Corrección ficticia",
    )
    assert received_for(booked) == 0


def test_void_requires_reason_preserves_original_and_audit_privacy(identities, booked, data):
    payment, _ = pay(identities, booked, data)
    with pytest.raises(ValidationError):
        void_payment(
            actor=identities["staff"],
            tenant=identities["tenant_a"],
            payment_id=payment.pk,
            reason="",
        )
    for _ in range(2):
        void_payment(
            actor=identities["staff"],
            tenant=identities["tenant_a"],
            payment_id=payment.pk,
            reason="Motivo ficticio restringido",
        )
    with pytest.raises(PaymentConflict):
        void_payment(
            actor=identities["staff"],
            tenant=identities["tenant_a"],
            payment_id=payment.pk,
            reason="Otro motivo",
        )
    assert AuditEvent.objects.filter(action="payment_voided").count() == 1
    events = str(list(AuditEvent.objects.filter(entity="payment").values("before", "after")))
    assert "Motivo ficticio restringido" not in events and data["reference"] not in events
    with pytest.raises(ProtectedError):
        booked.delete()


def test_staff_api_balances_filters_idempotency_and_csrf(csrf_client, identities, booked, data):
    enter(csrf_client, identities, "staff")
    url = f"/api/v1/reservations/{booked.pk}/payments/"
    body = {**json_data(data), "amount": str(data["amount"])}
    first = write(csrf_client, identities["tenant_a"], url, body)
    assert first.status_code == 201, first.json()
    assert write(csrf_client, identities["tenant_a"], url, body).status_code == 200
    details = csrf_client.get(f"/api/v1/reservations/{booked.pk}/").json()
    assert details["received_amount"] == "50000.10" and details["balance"] == "100000.15"
    assert csrf_client.get("/api/v1/reservations/", {"debt": "true"}).json()["count"] == 1
    assert (
        csrf_client.post(
            url, body, format="json", HTTP_X_TENANT_CONTEXT=str(identities["tenant_a"].pk)
        ).status_code
        == 403
    )
    assert write(csrf_client, identities["tenant_b"], url, body).status_code == 409
    assert (
        write(
            csrf_client,
            identities["tenant_a"],
            f"/api/v1/payments/{first.json()['id']}/void/",
            {"reason": "Error ficticio"},
        ).status_code
        == 200
    )
    assert csrf_client.get(f"/api/v1/reservations/{booked.pk}/").json()["received_amount"] == "0.00"
    transition_reservation(
        actor=identities["owner"],
        tenant=identities["tenant_a"],
        instance=booked,
        status="cancelled",
        reason="Cambio ficticio",
    )
    assert csrf_client.get("/api/v1/reservations/", {"debt": "true"}).json()["count"] == 0


def test_other_tenant_and_revoked_access_are_rejected(csrf_client, identities, booked, data):
    payment, _ = pay(identities, booked, data)
    enter(csrf_client, identities)
    from tests.conftest import login_client, select_company

    csrf_client.logout()
    assert login_client(csrf_client, identities["other"].email).status_code == 200
    assert select_company(csrf_client, identities["tenant_b"]).status_code == 200
    assert csrf_client.get(f"/api/v1/reservations/{booked.pk}/payments/").status_code == 404
    assert csrf_client.get(f"/api/v1/payments/{payment.pk}/receipt/").status_code == 404
    assert (
        write(
            csrf_client,
            identities["tenant_b"],
            f"/api/v1/payments/{payment.pk}/void/",
            {"reason": "x"},
        ).status_code
        == 404
    )
    with pytest.raises(Http404):
        record_payment(
            actor=identities["other"],
            tenant=identities["tenant_b"],
            reservation_id=booked.pk,
            data=data,
        )
    identities["memberships"]["staff"].active = False
    identities["memberships"]["staff"].save()
    with pytest.raises(PermissionDenied):
        pay(identities, booked, data)


def image_upload():
    stream = BytesIO()
    Image.new("RGB", (2, 2)).save(stream, format="PNG")
    return SimpleUploadedFile("fictional-proof.png", stream.getvalue(), content_type="image/png")


def test_private_receipt_preserved_after_void(
    csrf_client, identities, booked, data, settings, tmp_path
):
    settings.MEDIA_ROOT = tmp_path
    payment, _ = pay(identities, booked, data)
    enter(csrf_client, identities, "staff")
    from tests.conftest import csrf_token

    url = f"/api/v1/payments/{payment.pk}/receipt/"
    result = csrf_client.post(
        url,
        {"file": image_upload()},
        format="multipart",
        HTTP_X_CSRFTOKEN=csrf_token(csrf_client),
        HTTP_X_TENANT_CONTEXT=str(identities["tenant_a"].pk),
    )
    assert result.status_code == 200, result.json()
    response = csrf_client.get(url)
    assert response.status_code == 200 and response["Cache-Control"] == "no-store"
    assert "attachment" in response["Content-Disposition"]
    assert b"".join(response.streaming_content).startswith(b"\x89PNG")
    payment.refresh_from_db()
    path = payment.receipt_file.path
    assert "fictional-proof" not in path
    with pytest.raises(PaymentConflict):
        attach_receipt(
            actor=identities["staff"],
            tenant=identities["tenant_a"],
            payment_id=payment.pk,
            upload=image_upload(),
        )
    void_payment(
        actor=identities["staff"],
        tenant=identities["tenant_a"],
        payment_id=payment.pk,
        reason="Corrección ficticia",
    )
    assert csrf_client.get(url).status_code == 200
    assert payment.receipt_file.storage.exists(payment.receipt_file.name)


def test_invalid_receipt_has_no_recorded_file(identities, booked, data):
    payment, _ = pay(identities, booked, data)
    for content in (b"<svg></svg>", b"%PDF-fake", b"not-an-image"):
        with pytest.raises(ValidationError):
            attach_receipt(
                actor=identities["staff"],
                tenant=identities["tenant_a"],
                payment_id=payment.pk,
                upload=SimpleUploadedFile("fake.png", content, content_type="image/png"),
            )
    payment.refresh_from_db()
    assert not payment.receipt_file


def test_database_payment_constraints(identities, booked, data):
    payment, _ = pay(identities, booked, data)
    for changes in ({"amount": 0}, {"amount": -1}, {"status": "voided"}, {"method": "bad"}):
        with transaction.atomic(), pytest.raises(IntegrityError):
            Payment.objects.filter(pk=payment.pk).update(**changes)


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("same_request", [True, False])
def test_concurrent_payments_preserve_exact_balance(identities, booked, data, same_request):
    barrier = Barrier(2)

    def attempt(index):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return pay(
                identities,
                booked,
                {**data, "request_id": data["request_id"] if same_request else uuid4()},
            )[0].pk
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        ids = list(executor.map(attempt, range(2)))
    assert Payment.objects.count() == (1 if same_request else 2)
    assert received_for(booked) == data["amount"] * (1 if same_request else 2)
    assert (ids[0] == ids[1]) is same_request


@pytest.mark.parametrize("kind", ["future", "naive", "missing"])
def test_invalid_payment_timestamps(identities, booked, data, kind):
    value = (
        timezone.now() + timedelta(hours=1)
        if kind == "future"
        else timezone.now().replace(tzinfo=None)
        if kind == "naive"
        else None
    )
    with pytest.raises(ValidationError):
        pay(identities, booked, {**data, "paid_at": value})


@pytest.mark.django_db(transaction=True)
def test_concurrent_void_is_idempotent_and_balance_is_exact(identities, booked, data):
    payment, _ = pay(identities, booked, data)
    barrier = Barrier(2)

    def attempt(_):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return void_payment(
                actor=identities["staff"],
                tenant=identities["tenant_a"],
                payment_id=payment.pk,
                reason="Corrección ficticia",
            ).pk
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert list(executor.map(attempt, range(2))) == [payment.pk, payment.pk]
    assert Payment.objects.count() == 1
    assert received_for(booked) == Decimal("0.00")
    assert AuditEvent.objects.filter(action="payment_voided").count() == 1
