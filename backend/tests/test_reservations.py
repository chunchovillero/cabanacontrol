from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch

import pytest
from django.db import IntegrityError, close_old_connections, transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.audit.models import AuditEvent
from apps.guests.models import Guest
from apps.properties.models import Property
from apps.properties.services import save_property
from apps.reservations.models import AvailabilityBlock, Reservation
from apps.reservations.queries import blocking_reservations
from apps.reservations.services import (
    AvailabilityConflict,
    local_today,
    save_block,
    save_reservation,
    transition_reservation,
)
from tests.conftest import csrf_token, login_client, select_company

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(identities):
    properties, guests = {}, {}
    for key in ("a", "b"):
        properties[key] = Property.objects.create(
            tenant=identities[f"tenant_{key}"],
            created_by=identities["owner" if key == "a" else "other"],
            name="Cabaña ficticia",
            code="CAB",
            capacity=4,
            base_rate="50000.00",
            check_in_time="15:00",
            check_out_time="11:00",
        )
        guests[key] = Guest.objects.create(
            tenant=identities[f"tenant_{key}"],
            created_by=identities["owner" if key == "a" else "other"],
            first_name="Persona ficticia",
            last_name="De prueba",
            document_type="passport",
            document_number="FAKE-ONLY",
            notes="Nota restringida ficticia",
        )
    start = local_today(identities["tenant_a"]) + timedelta(days=30)
    data = dict(
        property_id=properties["a"].pk,
        primary_guest_id=guests["a"].pk,
        check_in=start,
        check_out=start + timedelta(days=3),
        adults=2,
        children=1,
        total_amount=Decimal("150000.25"),
        source="direct",
        status="draft",
        notes="Nota operativa",
    )
    return properties, guests, data


def save(identities, data, **kwargs):
    return save_reservation(
        actor=identities["owner"], tenant=identities["tenant_a"], data=data, **kwargs
    )


def move(identities, instance, status, **kwargs):
    return transition_reservation(
        actor=identities["owner"],
        tenant=identities["tenant_a"],
        instance=instance,
        status=status,
        **kwargs,
    )


def block(identities, data, **kwargs):
    return save_block(
        actor=identities["owner"],
        tenant=identities["tenant_a"],
        data=dict(
            property_id=data["property_id"],
            start_date=data["check_in"],
            end_date=data["check_out"],
            reason="maintenance",
            **kwargs,
        ),
    )


def enter(client, identities, who="owner"):
    assert login_client(client, identities[who].email).status_code == 200
    assert select_company(client, identities["tenant_a"]).status_code == 200


def write(client, tenant, url, data, method="post"):
    return getattr(client, method)(
        url,
        data,
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token(client),
        HTTP_X_TENANT_CONTEXT=str(tenant.pk),
    )


def json_data(data):
    return {
        key: (
            value.isoformat()
            if hasattr(value, "isoformat")
            else str(value)
            if key.endswith("_id") or key == "total_amount"
            else value
        )
        for key, value in data.items()
    }


@pytest.mark.parametrize("status", ["confirmed", "pending"])
def test_overlap_and_same_day_turnover(identities, setup, status):
    _, _, data = setup
    hold = {"hold_until": timezone.now() + timedelta(hours=3)} if status == "pending" else {}
    reservation = save(identities, {**data, "status": status, **hold})
    with pytest.raises(AvailabilityConflict):
        save(identities, {**data, "status": "confirmed"})
    after = save(
        identities,
        {
            **data,
            "status": "confirmed",
            "check_in": data["check_out"],
            "check_out": data["check_out"] + timedelta(days=1),
        },
    )
    assert after.check_in == reservation.check_out


def test_expired_hold_frees_inventory_and_confirmation_rechecks(identities, setup):
    _, _, data = setup
    held = save(
        identities,
        {**data, "status": "pending", "hold_until": timezone.now() + timedelta(minutes=10)},
    )
    Reservation.objects.filter(pk=held.pk).update(hold_until=timezone.now() - timedelta(seconds=1))
    save(identities, {**data, "status": "confirmed"})
    with pytest.raises(AvailabilityConflict):
        move(identities, held, "confirmed")
    held.refresh_from_db()
    assert held.status == "pending"


def test_cancel_frees_dates_preserves_history(identities, setup):
    _, _, data = setup
    reservation = save(identities, {**data, "status": "confirmed"})
    move(identities, reservation, "cancelled", reason="Motivo ficticio")
    assert save(identities, {**data, "status": "confirmed"})
    reservation.refresh_from_db()
    assert reservation.cancel_reason == "Motivo ficticio"
    with pytest.raises(ValidationError):
        save(identities, {"notes": "x"}, instance=reservation)
    with pytest.raises(ProtectedError):
        setup[0]["a"].delete()
    with pytest.raises(ProtectedError):
        setup[1]["a"].delete()


def test_blocks_conflict_both_directions_and_can_be_released(identities, setup):
    _, _, data = setup
    item = block(identities, data)
    with pytest.raises(AvailabilityConflict):
        save(identities, {**data, "status": "confirmed"})
    with pytest.raises(AvailabilityConflict):
        block(identities, data)
    save_block(
        actor=identities["owner"],
        tenant=identities["tenant_a"],
        instance=item,
        data={"active": False},
    )
    save(identities, {**data, "status": "confirmed"})
    with pytest.raises(AvailabilityConflict):
        save_block(
            actor=identities["owner"],
            tenant=identities["tenant_a"],
            instance=item,
            data={"active": True},
        )
    assert AvailabilityBlock.objects.count() == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("adults", 0),
        ("adults", True),
        ("children", -1),
        ("children", 4),
        ("total_amount", 1.25),
        ("total_amount", "NaN"),
        ("total_amount", "-1"),
        ("total_amount", "1.234"),
        ("notes", None),
        ("currency", "USD"),
        ("tenant_id", "x"),
        ("status", "checked_out"),
    ],
)
def test_invalid_domain_values(identities, setup, field, value):
    with pytest.raises(ValidationError):
        save(identities, {**setup[2], field: value})


def test_past_dates_and_pending_expiration_validation(identities, setup):
    data = setup[2]
    yesterday = local_today(identities["tenant_a"]) - timedelta(days=1)
    with pytest.raises(ValidationError):
        save(identities, {**data, "check_in": yesterday})
    for hold in (None, timezone.now() - timedelta(seconds=1), timezone.now().replace(tzinfo=None)):
        with pytest.raises(ValidationError):
            save(identities, {**data, "status": "pending", "hold_until": hold})


def test_transitions_and_occupancy_dates(identities, setup):
    data = setup[2]
    item = save(identities, data)
    with pytest.raises(ValidationError):
        move(identities, item, "checked_out")
    item = move(identities, item, "pending", hold_until=timezone.now() + timedelta(hours=1))
    item = move(identities, item, "confirmed")
    with pytest.raises(ValidationError):
        move(identities, item, "checked_in")
    with patch("apps.reservations.services.local_today", return_value=data["check_in"]):
        item = move(identities, item, "checked_in")
    with pytest.raises(ValidationError):
        save(identities, {"children": 0}, instance=item)
    with patch("apps.reservations.services.local_today", return_value=data["check_out"]):
        item = move(identities, item, "checked_out")
    assert not blocking_reservations(
        identities["tenant_a"], item.property_id, item.check_in, item.check_out
    ).exists()


def test_api_staff_privacy_csrf_and_context(csrf_client, identities, setup):
    data = json_data(setup[2])
    enter(csrf_client, identities, "staff")
    response = write(csrf_client, identities["tenant_a"], "/api/v1/reservations/", data)
    assert response.status_code == 201, response.json()
    item = response.json()
    assert set(item["guest"]) == {
        "id",
        "first_name",
        "last_name",
        "document_type",
        "document_masked",
        "active",
    }
    assert "FAKE-ONLY" not in str(item)
    assert "Nota restringida" not in str(item)
    url = f"/api/v1/reservations/{item['id']}/"
    assert (
        write(
            csrf_client, identities["tenant_a"], url, {"total_amount": "200000.75"}, "patch"
        ).status_code
        == 200
    )
    assert write(csrf_client, identities["tenant_a"], url + "confirm/", {}).status_code == 200
    assert (
        write(
            csrf_client, identities["tenant_a"], url + "cancel/", {"reason": "Cambio ficticio"}
        ).status_code
        == 200
    )
    assert (
        write(csrf_client, identities["tenant_a"], "/api/v1/availability-blocks/", {}).status_code
        == 403
    )
    assert (
        csrf_client.post(
            "/api/v1/reservations/",
            data,
            format="json",
            HTTP_X_TENANT_CONTEXT=str(identities["tenant_a"].pk),
        ).status_code
        == 403
    )
    assert (
        csrf_client.post(
            "/api/v1/reservations/", data, format="json", HTTP_X_CSRFTOKEN=csrf_token(csrf_client)
        ).status_code
        == 409
    )
    assert (
        write(csrf_client, identities["tenant_b"], "/api/v1/reservations/", data).status_code == 409
    )
    assert (
        csrf_client.delete(
            url,
            HTTP_X_CSRFTOKEN=csrf_token(csrf_client),
            HTTP_X_TENANT_CONTEXT=str(identities["tenant_a"].pk),
        ).status_code
        == 405
    )


def test_cross_tenant_objects_are_404(csrf_client, identities, setup):
    props, guests, data = setup
    enter(csrf_client, identities)
    for changed in ({"property_id": str(props["b"].pk)}, {"primary_guest_id": str(guests["b"].pk)}):
        assert (
            write(
                csrf_client,
                identities["tenant_a"],
                "/api/v1/reservations/",
                {**json_data(data), **changed},
            ).status_code
            == 404
        )
    other = save_reservation(
        actor=identities["other"],
        tenant=identities["tenant_b"],
        data={**data, "property_id": props["b"].pk, "primary_guest_id": guests["b"].pk},
    )
    url = f"/api/v1/reservations/{other.pk}/"
    assert csrf_client.get(url).status_code == 404
    assert write(csrf_client, identities["tenant_a"], url + "confirm/", {}).status_code == 404
    assert csrf_client.get("/api/v1/reservations/").json()["count"] == 0
    assert (
        csrf_client.get(
            "/api/v1/availability/",
            {
                "property_id": str(props["b"].pk),
                "from": str(data["check_in"]),
                "to": str(data["check_out"]),
            },
        ).status_code
        == 404
    )


def test_availability_and_api_filters(csrf_client, identities, setup):
    _, _, data = setup
    enter(csrf_client, identities)
    params = {"from": str(data["check_in"]), "to": str(data["check_out"]), "guests": 4}
    assert (
        csrf_client.get("/api/v1/availability/", params).json()["results"][0]["available"] is True
    )
    assert (
        csrf_client.get("/api/v1/availability/", {**params, "guests": 5}).json()["results"][0][
            "available"
        ]
        is False
    )
    save(identities, {**data, "status": "confirmed"})
    assert (
        csrf_client.get("/api/v1/availability/", params).json()["results"][0]["available"] is False
    )
    assert csrf_client.get("/api/v1/reservations/", {"status": "draft"}).json()["count"] == 0
    assert csrf_client.get("/api/v1/reservations/", {"status": "confirmed"}).json()["count"] == 1
    assert (
        csrf_client.get("/api/v1/availability/", {**params, "from": params["to"]}).status_code
        == 400
    )
    assert csrf_client.get("/api/v1/availability/", {**params, "page": 1}).status_code == 200


def test_inactive_objects_and_revoked_membership(identities, setup):
    props, guests, data = setup
    props["a"].active = False
    props["a"].save()
    with pytest.raises(ValidationError):
        save(identities, data)
    props["a"].active = True
    props["a"].save()
    guests["a"].active = False
    guests["a"].save()
    with pytest.raises(ValidationError):
        save(identities, data)
    identities["memberships"]["owner"].active = False
    identities["memberships"]["owner"].save()
    with pytest.raises(PermissionDenied):
        save(identities, data)


def test_database_constraints_and_audit_without_personal_text(identities, setup):
    item = save(identities, setup[2])
    for changes in (
        {"check_out": item.check_in},
        {"adults": 0},
        {"status": "pending"},
        {"total_amount": "-1"},
    ):
        with transaction.atomic(), pytest.raises(IntegrityError):
            Reservation.objects.filter(pk=item.pk).update(**changes)
    events = str(list(AuditEvent.objects.filter(entity="reservation").values("before", "after")))
    assert "Persona ficticia" not in events
    assert "FAKE-ONLY" not in events
    assert "Nota operativa" not in events


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("opponent", ["reservation", "pending", "block"])
def test_concurrent_inventory_operations(identities, setup, opponent):
    data = setup[2]
    barrier = Barrier(2)

    def attempt(kind):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            if kind == "block":
                block(identities, data)
            else:
                save(
                    identities,
                    {
                        **data,
                        "status": "pending" if kind == "pending" else "confirmed",
                        **(
                            {"hold_until": timezone.now() + timedelta(hours=1)}
                            if kind == "pending"
                            else {}
                        ),
                    },
                )
            return True
        except AvailabilityConflict:
            return False
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        accepted = list(executor.map(attempt, ["reservation", opponent]))
    assert sum(accepted) == 1
    assert Reservation.objects.count() + AvailabilityBlock.objects.count() == 1


def test_capacity_reduction_preserves_existing_reservations(identities, setup):
    item = save(identities, {**setup[2], "status": "confirmed"})
    with pytest.raises(ValidationError):
        save_property(
            actor=identities["owner"],
            tenant=identities["tenant_a"],
            instance=setup[0]["a"],
            data={"capacity": 2},
        )
    move(identities, item, "cancelled", reason="Motivo ficticio")
    assert (
        save_property(
            actor=identities["owner"],
            tenant=identities["tenant_a"],
            instance=setup[0]["a"],
            data={"capacity": 2},
        ).capacity
        == 2
    )


def test_company_local_today_not_server_utc_day(identities):
    with patch(
        "apps.reservations.services.timezone.now",
        return_value=datetime(2026, 10, 14, 1, tzinfo=UTC),
    ):
        assert str(local_today(identities["tenant_a"])) == "2026-10-13"


def test_pending_api_requires_explicit_timezone_and_duplicate_hold_conflicts(
    csrf_client, identities, setup
):
    enter(csrf_client, identities)
    data = {**json_data(setup[2]), "status": "pending"}
    until = timezone.now() + timedelta(hours=1)
    assert (
        write(
            csrf_client,
            identities["tenant_a"],
            "/api/v1/reservations/",
            {**data, "hold_until": until.replace(tzinfo=None).isoformat()},
        ).status_code
        == 400
    )
    created = write(
        csrf_client,
        identities["tenant_a"],
        "/api/v1/reservations/",
        {**data, "hold_until": until.isoformat()},
    )
    assert created.status_code == 201
    assert created.json()["hold_active"] is True
    response = write(
        csrf_client,
        identities["tenant_a"],
        "/api/v1/reservations/",
        {**data, "hold_until": until.isoformat()},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "availability_conflict"


def test_blocks_api_isolation_and_release(csrf_client, identities, setup):
    enter(csrf_client, identities)
    data = {
        "property_id": str(setup[0]["a"].pk),
        "start_date": str(setup[2]["check_in"]),
        "end_date": str(setup[2]["check_out"]),
        "reason": "owner_use",
    }
    response = write(csrf_client, identities["tenant_a"], "/api/v1/availability-blocks/", data)
    assert response.status_code == 201
    url = f"/api/v1/availability-blocks/{response.json()['id']}/"
    assert (
        write(csrf_client, identities["tenant_a"], url, {"active": False}, "patch").status_code
        == 200
    )
    assert (
        write(
            csrf_client,
            identities["tenant_a"],
            url,
            {"property_id": str(setup[0]["b"].pk)},
            "patch",
        ).status_code
        == 404
    )
    assert AvailabilityBlock.objects.get(pk=response.json()["id"]).active is False
    assert select_company(csrf_client, identities["tenant_b"]).status_code == 404


def test_expired_hold_can_confirm_if_still_available(identities, setup):
    data = setup[2]
    item = save(
        identities,
        {**data, "status": "pending", "hold_until": timezone.now() + timedelta(minutes=5)},
    )
    Reservation.objects.filter(pk=item.pk).update(hold_until=timezone.now() - timedelta(seconds=1))
    assert move(identities, item, "confirmed").hold_until is None


def test_edit_rechecks_conflicts_and_does_not_overwrite_price(identities, setup):
    data = setup[2]
    first = save(identities, {**data, "status": "confirmed"})
    second = save(
        identities,
        {
            **data,
            "status": "confirmed",
            "check_in": data["check_out"],
            "check_out": data["check_out"] + timedelta(days=2),
        },
    )
    with pytest.raises(AvailabilityConflict):
        save(identities, {"check_in": first.check_in}, instance=second)
    second.refresh_from_db()
    assert second.check_in == first.check_out
    assert save(identities, {"notes": "Cambio ficticio"}, instance=first).total_amount == Decimal(
        "150000.25"
    )


@pytest.mark.django_db(transaction=True)
def test_concurrent_confirmations_of_drafts(identities, setup):
    items = [save(identities, setup[2]), save(identities, setup[2])]
    barrier = Barrier(2)

    def confirm(item):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            move(identities, item, "confirmed")
            return True
        except AvailabilityConflict:
            return False
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sum(executor.map(confirm, items)) == 1
    assert Reservation.objects.filter(status="confirmed").count() == 1
    assert Reservation.objects.filter(status="draft").count() == 1
