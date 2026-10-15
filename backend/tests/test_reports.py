import csv
from datetime import datetime, time, timedelta
from io import StringIO
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from apps.audit.models import AuditEvent
from apps.payments.models import Payment
from apps.reservations.models import Reservation
from tests.test_insights import period as report_period  # noqa: F401
from tests.test_reservations import enter, save
from tests.test_reservations import setup as reservation_setup  # noqa: F401

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def period(request):
    return request.getfixturevalue("report_period")


def filters(start, end, kind="summary", **kwargs):
    return {"from": str(start), "to": str(end), "kind": kind, **kwargs}


def csv_rows(response):
    return list(csv.reader(StringIO(response.content.decode("utf-8-sig")), delimiter=";"))


def test_summary_matches_dashboard_and_cancelled_cohort(csrf_client, identities, period):
    setup, start, end = period
    save(identities, {**setup[2], "status": "confirmed"})
    cancelled = save(identities, setup[2])
    Reservation.objects.filter(pk=cancelled.pk).update(status="cancelled", cancel_reason="Ficticio")
    save(identities, {**setup[2], "check_in": end, "check_out": end + timedelta(days=2)})
    enter(csrf_client, identities)
    params = filters(start, end)
    dashboard = csrf_client.get("/api/v1/dashboard/", {"from": str(start), "to": str(end)}).json()
    result = csrf_client.get("/api/v1/reports/", params)
    assert result.status_code == 200 and "no-store" in result["Cache-Control"]
    assert result.json() == {
        **dashboard,
        "cancelled_count": 1,
        "property_id": None,
        "property_name": "Todas las cabañas",
    }
    response = csrf_client.get(
        "/api/v1/reports/export/", params, HTTP_X_TENANT_CONTEXT=str(identities["tenant_a"].pk)
    )
    assert response.status_code == 200
    row = csv_rows(response)[1]
    assert row[3:7] == [
        dashboard["money"][0][key] for key in ("collected", "agreed", "outstanding", "credit")
    ]
    assert row[11] == "1" and row[-1] == "Todas las cabañas"


def test_detail_pagination_complete_export_privacy_and_audit(csrf_client, identities, period):
    setup, start, end = period
    for _ in range(26):
        save(identities, setup[2])
    enter(csrf_client, identities, "staff")
    params = filters(start, end, "reservations")
    first = csrf_client.get("/api/v1/reports/", params).json()
    second = csrf_client.get("/api/v1/reports/", {**params, "page": 2}).json()
    assert first["count"] == 26 and len(first["results"]) == 25 and first["next"]
    assert len(second["results"]) == 1 and second["previous"] and not second["next"]
    ids = {row["id"] for row in first["results"] + second["results"]}
    assert len(ids) == 26
    assert csrf_client.get("/api/v1/reports/", {**params, "page": 3}).status_code == 404
    response = csrf_client.get(
        "/api/v1/reports/export/", params, HTTP_X_TENANT_CONTEXT=str(identities["tenant_a"].pk)
    )
    rows = csv_rows(response)
    assert response.status_code == 200 and len(rows) == 27
    assert {row[0] for row in rows[1:]} == ids
    assert response["X-Content-Type-Options"] == "nosniff"
    assert "no-store" in response["Cache-Control"]
    assert response["Content-Disposition"].startswith(
        'attachment; filename="cabanacontrol-reservations-'
    )
    assert "Persona ficticia" not in response.content.decode("utf-8")
    assert "Nota" not in response.content.decode("utf-8")
    assert "FAKE-ONLY" not in response.content.decode("utf-8")
    event = AuditEvent.objects.get(action="report.export")
    assert event.tenant_id == identities["tenant_a"].pk and event.actor_id == identities["staff"].pk
    assert event.after["rows"] == 26 and "guest" not in str(event.after)


def test_payments_local_bounds_voids_and_cancelled_reservations(csrf_client, identities, period):
    setup, start, end = period
    item = save(identities, setup[2])
    Reservation.objects.filter(pk=item.pk).update(status="cancelled", cancel_reason="Ficticio")
    zone = ZoneInfo(identities["tenant_a"].timezone)
    boundary = datetime.combine(start, time.min, zone)
    for amount, paid_at, status in (
        ("40.10", boundary, "recorded"),
        ("10.00", boundary - timedelta(seconds=1), "recorded"),
        ("20.00", datetime.combine(end, time.min, zone), "recorded"),
        ("30.00", boundary, "voided"),
    ):
        Payment.objects.create(
            tenant=identities["tenant_a"],
            reservation=item,
            request_id=uuid4(),
            amount=amount,
            currency="CLP",
            paid_at=paid_at,
            status=status,
            method="cash",
            recorded_by=identities["owner"],
            voided_by=identities["owner"] if status == "voided" else None,
            voided_at=boundary if status == "voided" else None,
            void_reason="Ficticio" if status == "voided" else "",
        )
    enter(csrf_client, identities)
    params = filters(start, end, "payments")
    response = csrf_client.get("/api/v1/reports/", params)
    assert response.status_code == 200
    result = response.json()
    assert result["count"] == 1 and result["results"][0]["amount"] == "40.10"
    assert result["results"][0]["paid_at"] == boundary.isoformat()
    response = csrf_client.get(
        "/api/v1/reports/export/", params, HTTP_X_TENANT_CONTEXT=str(identities["tenant_a"].pk)
    )
    assert csv_rows(response)[1][6] == "40.10"


@pytest.mark.parametrize("who", ["owner", "manager", "staff"])
def test_roles_filters_and_tenant_isolation(csrf_client, identities, period, who):
    setup, start, end = period
    item = save(identities, setup[2])
    enter(csrf_client, identities, who)
    params = filters(start, end, "reservations", property_id=str(setup[0]["a"].pk))
    for url in ("/api/v1/reports/", "/api/v1/reports/export/"):
        context = {"HTTP_X_TENANT_CONTEXT": str(identities["tenant_a"].pk)}
        assert csrf_client.get(url, params, **context).status_code == 200
        assert (
            csrf_client.get(
                url, {**params, "property_id": str(setup[0]["b"].pk)}, **context
            ).status_code
            == 404
        )
        assert (
            csrf_client.get(
                url, {**params, "tenant_id": str(identities["tenant_b"].pk)}, **context
            ).status_code
            == 400
        )
        assert (
            csrf_client.get(
                url, params, HTTP_X_TENANT_CONTEXT=str(identities["tenant_b"].pk)
            ).status_code
            == 409
        )
        assert csrf_client.get(url, {**params, "to": str(start)}, **context).status_code == 400
    cancelled = csrf_client.get("/api/v1/reports/", {**params, "status": "cancelled"}).json()
    assert cancelled["count"] == 0
    assert csrf_client.get("/api/v1/reports/", params).json()["results"][0]["id"] == str(item.pk)
    assert csrf_client.get("/api/v1/reports/export/", params).status_code == 409


def test_invalid_queries_anonymous_empty_and_export_limit(
    csrf_client, identities, period, monkeypatch
):
    setup, start, end = period
    params = filters(start, end, "reservations")
    assert csrf_client.get("/api/v1/reports/", params).status_code == 403
    assert csrf_client.get("/api/v1/reports/export/", params).status_code == 403
    enter(csrf_client, identities)
    assert csrf_client.get("/api/v1/reports/", params).json()["count"] == 0
    for extra in (
        {"kind": "invalid"},
        {"status": "invalid"},
        {"page": 0},
        {"to": str(start + timedelta(days=367))},
        {"kind": "summary", "status": "cancelled"},
    ):
        assert csrf_client.get("/api/v1/reports/", {**params, **extra}).status_code == 400
    context = {"HTTP_X_TENANT_CONTEXT": str(identities["tenant_a"].pk)}
    assert (
        csrf_client.get("/api/v1/reports/export/", {**params, "page": 1}, **context).status_code
        == 400
    )
    assert len(csv_rows(csrf_client.get("/api/v1/reports/export/", params, **context))) == 1
    save(identities, setup[2])
    monkeypatch.setattr("apps.insights.reports.EXPORT_LIMIT", 0)
    assert csrf_client.get("/api/v1/reports/export/", params, **context).status_code == 400
    assert AuditEvent.objects.filter(action="report.export").count() == 1


def test_export_neutralizes_property_name_and_keeps_inactive_history(
    csrf_client, identities, period
):
    setup, start, end = period
    save(identities, setup[2])
    prop = setup[0]["a"]
    prop.name = ' =SUM(1);"ficticio"'
    prop.active = False
    prop.save()
    enter(csrf_client, identities)
    params = filters(start, end, "reservations", property_id=str(prop.pk))
    response = csrf_client.get(
        "/api/v1/reports/export/", params, HTTP_X_TENANT_CONTEXT=str(identities["tenant_a"].pk)
    )
    assert csv_rows(response)[1][2] == "'" + prop.name
    assert (
        csrf_client.get("/api/v1/reports/", params).json()["results"][0]["property_active"] is False
    )
