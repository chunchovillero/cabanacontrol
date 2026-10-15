from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time, timedelta
from threading import Barrier
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from django.db import close_old_connections
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.audit.models import AuditEvent
from apps.operations.models import HousekeepingTask
from apps.operations.services import CHECKLIST, checkout_task
from apps.reservations.models import Reservation
from apps.reservations.services import local_today, transition_reservation
from tests.test_reservations import enter, save, write
from tests.test_reservations import setup as reservation_setup  # noqa: F401

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def task_setup(request, identities):
    properties, guests, data = request.getfixturevalue("reservation_setup")
    due = timezone.now() + timedelta(hours=1)
    return (
        properties,
        guests,
        data,
        {
            "property_id": str(properties["a"].pk),
            "due_at": due.isoformat(),
            "notes": "Nota ficticia operativa",
        },
    )


def test_staff_task_checklist_assignment_completion_and_history(
    csrf_client, identities, task_setup
):
    enter(csrf_client, identities, "staff")
    data = {**task_setup[3], "assigned_to_id": str(identities["memberships"]["staff"].pk)}
    response = write(csrf_client, identities["tenant_a"], "/api/v1/housekeeping/", data)
    assert response.status_code == 201
    task = response.json()
    url = f"/api/v1/housekeeping/{task['id']}/"
    assert (
        write(
            csrf_client, identities["tenant_a"], url, {"status": "completed"}, "patch"
        ).status_code
        == 400
    )
    assert (
        write(
            csrf_client,
            identities["tenant_a"],
            url,
            {"status": "in_progress", "bathroom": True},
            "patch",
        ).status_code
        == 200
    )
    response = write(
        csrf_client,
        identities["tenant_a"],
        url,
        {"status": "completed", **dict.fromkeys(CHECKLIST, True)},
        "patch",
    )
    assert response.status_code == 200 and response.json()["completed_at"]
    assert (
        write(
            csrf_client, identities["tenant_a"], url, {"notes": "Editar cerrado"}, "patch"
        ).status_code
        == 400
    )
    assert csrf_client.delete(url).status_code in [403, 405]
    assert HousekeepingTask.objects.count() == 1
    audit = AuditEvent.objects.filter(entity="housekeeping_task").last()
    assert "Nota ficticia" not in str(audit.after)


def test_task_cancellation_preserves_record_and_requires_reason(
    csrf_client, identities, task_setup
):
    enter(csrf_client, identities)
    response = write(csrf_client, identities["tenant_a"], "/api/v1/housekeeping/", task_setup[3])
    url = f"/api/v1/housekeeping/{response.json()['id']}/"
    assert (
        write(
            csrf_client, identities["tenant_a"], url, {"status": "cancelled"}, "patch"
        ).status_code
        == 400
    )
    response = write(
        csrf_client,
        identities["tenant_a"],
        url,
        {"status": "cancelled", "cancel_reason": "Motivo ficticio privado"},
        "patch",
    )
    assert (
        response.status_code == 200
        and response.json()["cancel_reason"] == "Motivo ficticio privado"
    )
    assert response.json()["completed_at"] is None
    assert HousekeepingTask.objects.count() == 1
    assert "Motivo ficticio" not in str(
        AuditEvent.objects.filter(entity="housekeeping_task").last().after
    )


def test_task_tenant_context_csrf_and_foreign_assignee(csrf_client, identities, task_setup):
    assert csrf_client.get("/api/v1/housekeeping/").status_code == 403
    enter(csrf_client, identities, "staff")
    url = "/api/v1/housekeeping/"
    tenant = identities["tenant_a"]
    assert csrf_client.post(url, task_setup[3], format="json").status_code == 403
    response = write(
        csrf_client,
        tenant,
        url,
        {**task_setup[3], "assigned_to_id": str(identities["memberships"]["other"].pk)},
    )
    assert response.status_code == 404
    assert (
        write(
            csrf_client, tenant, url, {**task_setup[3], "property_id": str(task_setup[0]["b"].pk)}
        ).status_code
        == 404
    )
    assert (
        write(csrf_client, tenant, url, {**task_setup[3], "tenant_id": str(tenant.pk)}).status_code
        == 400
    )
    response = write(csrf_client, tenant, url, task_setup[3])
    detail = f"{url}{response.json()['id']}/"
    assert (
        csrf_client.get(detail, HTTP_X_TENANT_CONTEXT=str(identities["tenant_b"].pk)).status_code
        == 409
    )
    other = HousekeepingTask.objects.create(
        tenant=identities["tenant_b"],
        property=task_setup[0]["b"],
        created_by=identities["other"],
        due_at=timezone.now(),
    )
    assert csrf_client.get(f"{url}{other.pk}/").status_code == 404
    assert (
        write(
            csrf_client, tenant, f"{url}{other.pk}/", {"status": "in_progress"}, "patch"
        ).status_code
        == 404
    )
    assert csrf_client.get(url).json()["count"] == 1
    assignees = csrf_client.get("/api/v1/housekeeping/assignees/").json()["results"]
    assert str(identities["memberships"]["other"].pk) not in {item["id"] for item in assignees}
    assert "email" not in str(assignees)


def checked_in_fixture(identities, task_setup):
    today = local_today(identities["tenant_a"])
    item = save(identities, task_setup[2])
    Reservation.objects.filter(pk=item.pk).update(
        status="checked_in", check_in=today - timedelta(days=2), check_out=today
    )
    item.refresh_from_db()
    return item


def test_checkout_creates_one_task_due_today_without_blocking(identities, task_setup):
    item = checked_in_fixture(identities, task_setup)
    item = transition_reservation(
        actor=identities["staff"],
        tenant=identities["tenant_a"],
        instance=item,
        status="checked_out",
    )
    task = HousekeepingTask.objects.get(reservation=item)
    due = task.due_at.astimezone(ZoneInfo(identities["tenant_a"].timezone))
    assert due.date() == local_today(identities["tenant_a"]) and due.time() == time(23, 59, 59)
    assert task.source == "checkout" and not task.assigned_to_id
    assert checkout_task(identities["staff"], identities["tenant_a"], item).pk == task.pk
    assert HousekeepingTask.objects.count() == 1
    with pytest.raises(ValidationError):
        transition_reservation(
            actor=identities["staff"],
            tenant=identities["tenant_a"],
            instance=item,
            status="checked_out",
        )
    from apps.reservations.queries import blocking_reservations

    assert not blocking_reservations(
        identities["tenant_a"], item.property_id, item.check_out, item.check_out + timedelta(days=1)
    ).exists()


def test_checkout_and_task_are_atomic(identities, task_setup):
    item = checked_in_fixture(identities, task_setup)
    with (
        patch("apps.operations.services.checkout_task", side_effect=RuntimeError("Fallo ficticio")),
        pytest.raises(RuntimeError),
    ):
        transition_reservation(
            actor=identities["owner"],
            tenant=identities["tenant_a"],
            instance=item,
            status="checked_out",
        )
    item.refresh_from_db()
    assert item.status == "checked_in" and not HousekeepingTask.objects.exists()
    assert not AuditEvent.objects.filter(action="reservation_checked_out").exists()


def test_simultaneous_checkout_creates_single_task(identities, task_setup):
    item = checked_in_fixture(identities, task_setup)
    barrier = Barrier(2)

    def attempt():
        close_old_connections()
        barrier.wait(timeout=10)
        try:
            transition_reservation(
                actor=identities["owner"],
                tenant=identities["tenant_a"],
                instance=item,
                status="checked_out",
            )
            return "ok"
        except ValidationError:
            return "closed"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(lambda _: attempt(), range(2)))
    assert sorted(result) == ["closed", "ok"]
    assert HousekeepingTask.objects.filter(reservation=item).count() == 1


def test_cleaning_alert_due_and_closed_filter(csrf_client, identities, task_setup):
    enter(csrf_client, identities)
    today = local_today(identities["tenant_a"])
    zone = ZoneInfo(identities["tenant_a"].timezone)
    due = datetime.combine(today, time(23, 59), zone)
    task = HousekeepingTask.objects.create(
        tenant=identities["tenant_a"],
        property=task_setup[0]["a"],
        due_at=due,
        created_by=identities["owner"],
    )
    response = csrf_client.get("/api/v1/operations/day/", {"date": str(today), "kind": "cleaning"})
    assert response.status_code == 200
    assert (
        response.json()["count"] == 1
        and response.json()["results"][0]["url"] == f"/limpieza/{task.pk}"
    )
    assert (
        write(
            csrf_client,
            identities["tenant_a"],
            f"/api/v1/housekeeping/{task.pk}/",
            {"status": "completed", **dict.fromkeys(CHECKLIST, True)},
            "patch",
        ).status_code
        == 200
    )
    assert (
        csrf_client.get("/api/v1/operations/day/", {"date": str(today), "kind": "cleaning"}).json()[
            "count"
        ]
        == 0
    )


def test_whatsapp_draft_private_audited_and_tenant_scoped(csrf_client, identities, task_setup):
    item = save(identities, task_setup[2])
    enter(csrf_client, identities, "staff")
    url = f"/api/v1/reservations/{item.pk}/whatsapp-draft/"
    response = csrf_client.get(url)
    assert response.status_code == 200 and set(response.json()) == {"phone", "message"}
    text = response.json()["message"]
    assert "Borrador" in text and "150000" not in text and "FAKE-ONLY" not in text
    assert "Nota" not in text and "Persona ficticia" not in text
    assert (
        csrf_client.get(url, HTTP_X_TENANT_CONTEXT=str(identities["tenant_b"].pk)).status_code
        == 409
    )
    assert AuditEvent.objects.get(action="whatsapp_draft_viewed").after == {}
    other = Reservation.objects.create(
        tenant=identities["tenant_b"],
        property=task_setup[0]["b"],
        primary_guest=task_setup[1]["b"],
        check_in=item.check_in,
        check_out=item.check_out,
        adults=1,
        children=0,
        status="draft",
        total_amount="0",
        currency="CLP",
        source="direct",
        created_by=identities["other"],
    )
    assert csrf_client.get(f"/api/v1/reservations/{other.pk}/whatsapp-draft/").status_code == 404
