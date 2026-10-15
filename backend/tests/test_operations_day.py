from datetime import timedelta

import pytest
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.properties.models import Property
from apps.reservations.models import Reservation
from apps.reservations.services import save_block
from tests.test_reservations import enter, save
from tests.test_reservations import setup as reservation_setup  # noqa: F401

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def day_setup(request):
    return request.getfixturevalue("reservation_setup")


def test_daily_lists_counts_exclusive_dates_and_privacy(csrf_client, identities, day_setup):
    data = day_setup[2]
    day = data["check_in"]
    hold = save(
        identities, {**data, "status": "pending", "hold_until": timezone.now() + timedelta(hours=1)}
    )
    Reservation.objects.filter(pk=hold.pk).update(hold_until=timezone.now() - timedelta(seconds=1))
    arrival = save(identities, {**data, "status": "confirmed"})
    departure = save(
        identities,
        {**data, "status": "confirmed", "check_in": day - timedelta(days=2), "check_out": day},
    )
    old = save(
        identities,
        {**data, "check_in": day - timedelta(days=5), "check_out": day - timedelta(days=3)},
    )
    Reservation.objects.filter(pk=old.pk).update(status="checked_in")
    enter(csrf_client, identities, "staff")
    result = csrf_client.get("/api/v1/operations/day/", {"date": str(day)}).json()
    assert result["counts"] == {
        "arrivals": 1,
        "departures": 1,
        "overdue_stays": 1,
        "expired_holds": 1,
        "maintenance": 0,
        "cleaning": 0,
    }
    assert result["results"][0]["id"] == str(arrival.pk)
    assert "Persona ficticia" not in str(result) and "FAKE-ONLY" not in str(result)
    for kind, item in (("departures", departure), ("overdue_stays", old), ("expired_holds", hold)):
        row = csrf_client.get("/api/v1/operations/day/", {"date": str(day), "kind": kind}).json()
        assert row["count"] == 1 and row["results"][0]["id"] == str(item.pk)


def test_day_isolation_validation_context_and_empty_pagination(csrf_client, identities, day_setup):
    url = "/api/v1/operations/day/"
    assert csrf_client.get(url).status_code == 403
    enter(csrf_client, identities)
    params = {"date": str(day_setup[2]["check_in"])}
    assert csrf_client.get(url, params).status_code == 200
    assert (
        csrf_client.get(url, {**params, "property_id": str(day_setup[0]["b"].pk)}).status_code
        == 404
    )
    assert csrf_client.get(url, {**params, "page": 2}).status_code == 404
    assert csrf_client.get(url, {**params, "date": "invalid"}).status_code == 400
    assert csrf_client.get(url, {**params, "kind": "invalid"}).status_code == 400
    assert (
        csrf_client.get(url, {**params, "tenant_id": str(identities["tenant_b"].pk)}).status_code
        == 400
    )
    assert (
        csrf_client.get(
            url, params, HTTP_X_TENANT_CONTEXT=str(identities["tenant_b"].pk)
        ).status_code
        == 409
    )


def test_maintenance_blocks_and_audits_before_after_dates(csrf_client, identities, day_setup):
    data = day_setup[2]
    block = save_block(
        actor=identities["owner"],
        tenant=identities["tenant_a"],
        data={
            "property_id": data["property_id"],
            "start_date": data["check_in"],
            "end_date": data["check_out"],
            "reason": "maintenance",
            "notes": "Nota ficticia",
        },
    )
    block = save_block(
        actor=identities["owner"],
        tenant=identities["tenant_a"],
        instance=block,
        data={"end_date": data["check_out"] + timedelta(days=1)},
    )
    audit = AuditEvent.objects.get(action="availability_block_updated")
    assert audit.before["end_date"] == str(data["check_out"])
    assert audit.after["end_date"] == str(block.end_date)
    assert "Nota ficticia" not in str(audit.after)
    enter(csrf_client, identities, "staff")
    result = csrf_client.get(
        "/api/v1/operations/day/", {"date": str(data["check_in"]), "kind": "maintenance"}
    ).json()
    assert result["count"] == 1 and result["results"][0]["url"] == "/reservas/bloqueos"
    result = csrf_client.get(
        "/api/v1/operations/day/", {"date": str(block.end_date), "kind": "maintenance"}
    ).json()
    assert result["count"] == 0


def test_day_preserves_inactive_history(csrf_client, identities, day_setup):
    data = day_setup[2]
    save(identities, {**data, "status": "confirmed"})
    Property.objects.filter(pk=data["property_id"]).update(active=False)
    enter(csrf_client, identities)
    result = csrf_client.get("/api/v1/operations/day/", {"date": str(data["check_in"])}).json()
    assert result["results"][0]["property_active"] is False
