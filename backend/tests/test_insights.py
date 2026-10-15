from datetime import datetime, time, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.utils import timezone

from apps.insights.queries import dashboard_metrics
from apps.payments.models import Payment
from apps.reservations.models import AvailabilityBlock, Reservation
from tests.test_reservations import enter, save, write
from tests.test_reservations import setup as reservation_setup  # noqa: F401

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def period(request):
    setup = request.getfixturevalue("reservation_setup")
    start = setup[2]["check_in"]
    return setup, start, start + timedelta(days=10)


def test_calendar_exclusive_dates_privacy_and_hold(csrf_client, identities, period):
    setup, start, end = period
    item = save(
        identities,
        {**setup[2], "status": "pending", "hold_until": timezone.now() + timedelta(hours=1)},
    )
    enter(csrf_client, identities)
    params = {"from": str(start), "to": str(end)}
    response = csrf_client.get("/api/v1/calendar/", params)
    assert response.status_code == 200
    event = response.json()["events"][0]
    assert event["start"] == str(start) and event["end"] == str(item.check_out)
    assert event["blocks_inventory"] is True
    assert "document" not in str(event) and "Persona ficticia" not in str(event)
    assert "Nota" not in str(event)
    Reservation.objects.filter(pk=item.pk).update(hold_until=timezone.now() - timedelta(seconds=1))
    assert (
        csrf_client.get("/api/v1/calendar/", params).json()["events"][0]["blocks_inventory"]
        is False
    )
    assert (
        csrf_client.get("/api/v1/calendar/", {"from": str(item.check_out), "to": str(end)}).json()[
            "events"
        ]
        == []
    )


def test_calendar_keeps_inactive_history_and_active_blocks(csrf_client, identities, period):
    setup, start, end = period
    save(identities, setup[2])
    AvailabilityBlock.objects.create(
        tenant=identities["tenant_a"],
        property=setup[0]["a"],
        start_date=start,
        end_date=start + timedelta(days=1),
        reason="maintenance",
        created_by=identities["owner"],
    )
    setup[0]["a"].active = False
    setup[0]["a"].save()
    enter(csrf_client, identities)
    result = csrf_client.get("/api/v1/calendar/", {"from": str(start), "to": str(end)}).json()[
        "events"
    ]
    assert len(result) == 2 and all(event["property_active"] is False for event in result)
    assert {event["kind"] for event in result} == {"block", "reservation"}


@pytest.mark.parametrize("endpoint", ["calendar", "dashboard"])
def test_isolation_context_validation_and_readonly(csrf_client, identities, period, endpoint):
    setup, start, end = period
    url = f"/api/v1/{endpoint}/"
    assert csrf_client.get(url).status_code == 403
    enter(csrf_client, identities, "staff")
    params = {"from": str(start), "to": str(end)}
    assert csrf_client.get(url, {**params, "property_id": str(setup[0]["b"].pk)}).status_code == 404
    assert (
        csrf_client.get(
            url, params, HTTP_X_TENANT_CONTEXT=str(identities["tenant_b"].pk)
        ).status_code
        == 409
    )
    assert (
        csrf_client.get(url, {**params, "tenant_id": str(identities["tenant_b"].pk)}).status_code
        == 400
    )
    assert csrf_client.get(url, {**params, "to": str(start)}).status_code == 400
    assert (
        csrf_client.get(url, {**params, "to": str(start + timedelta(days=367))}).status_code == 400
    )
    assert csrf_client.get(url, params).status_code == 200
    assert write(csrf_client, identities["tenant_a"], url, params).status_code == 405


def test_dashboard_money_separate_cohorts_and_no_credit_offset(identities, period):
    setup, start, end = period
    booked = save(identities, {**setup[2], "status": "confirmed", "total_amount": "100.25"})
    extra = save(identities, {**setup[2], "status": "draft", "total_amount": "50.00"})
    extra.status = "cancelled"
    extra.save()
    paid_at = timezone.make_aware(datetime.combine(start, time(12)))
    for reservation, amount in ((booked, "40.10"), (extra, "60.00")):
        Payment.objects.create(
            tenant=identities["tenant_a"],
            reservation=reservation,
            request_id=uuid4(),
            amount=amount,
            currency="CLP",
            paid_at=paid_at,
            method="transfer",
            recorded_by=identities["owner"],
        )
    result = dashboard_metrics(identities["tenant_a"], start, end)
    assert result["money"] == [
        {
            "currency": "CLP",
            "collected": "100.10",
            "agreed": "100.25",
            "outstanding": "60.15",
            "credit": "10.00",
        }
    ]
    assert result["occupied_nights"] == 3 and result["capacity_nights"] == 10
    assert result["occupancy_percent"] == "30.00"


def test_dashboard_today_matches_inventory_and_local_day(identities, period):
    setup, start, end = period
    save(identities, {**setup[2], "status": "confirmed"})
    with patch(
        "apps.insights.queries.timezone.now",
        return_value=timezone.make_aware(datetime.combine(start, time(12))),
    ):
        result = dashboard_metrics(identities["tenant_a"], start, end)
    assert result["today"]["occupied"] == 1
    assert result["today"]["available"] == 0
    assert result["today"]["arrivals"] == 1


def test_dashboard_groups_currencies_and_zero_denominator(identities, period):
    setup, start, end = period
    item = save(identities, {**setup[2], "status": "confirmed"})
    Reservation.objects.filter(pk=item.pk).update(currency="USD")
    setup[0]["a"].active = False
    setup[0]["a"].save()
    result = dashboard_metrics(identities["tenant_a"], start, end)
    assert result["capacity_nights"] == 0 and result["occupancy_percent"] == "0.00"
    assert result["money"][0]["currency"] == "USD"
    assert Decimal(result["money"][0]["agreed"]) == item.total_amount
