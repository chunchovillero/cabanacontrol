from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from django.db import close_old_connections
from django.http import Http404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.inquiries.models import Inquiry
from apps.inquiries.services import InquiryConflict, convert, save_inquiry
from apps.reservations.models import AvailabilityBlock, Reservation
from apps.reservations.services import AvailabilityConflict
from tests.test_reservations import setup  # noqa: F401

pytestmark = pytest.mark.django_db(transaction=True)


def create(identities, **extra):
    return save_inquiry(
        actor=identities["staff"],
        tenant=identities["tenant_a"],
        data={"original_text": "Consulta ficticia", "channel": "phone", **extra},
    )


def conversion(identities, inquiry, data, **overrides):
    payload = {key: value for key, value in data.items() if key != "status"}
    return convert(
        actor=identities["staff"],
        tenant=identities["tenant_a"],
        inquiry_id=inquiry.pk,
        data={**payload, "revision": inquiry.revision, "reviewed": True, **overrides},
    )


def test_conversion_retries_are_idempotent_and_draft_does_not_hold(identities, setup):  # noqa: F811
    _, _, data = setup
    inquiry = create(identities)
    reservation = conversion(identities, inquiry, data)
    assert reservation.status == "draft"
    assert reservation.hold_until is None
    assert conversion(identities, inquiry, data).pk == reservation.pk
    assert Reservation.objects.count() == 1
    with pytest.raises(InquiryConflict):
        conversion(identities, inquiry, data, adults=1)


def test_conflict_no_draft_or_partial_conversion(identities, setup):  # noqa: F811
    _, _, data = setup
    inquiry = create(identities)
    AvailabilityBlock.objects.create(
        tenant=identities["tenant_a"],
        property_id=data["property_id"],
        start_date=data["check_in"],
        end_date=data["check_out"],
        reason="maintenance",
        created_by=identities["owner"],
    )
    with pytest.raises(AvailabilityConflict):
        conversion(identities, inquiry, data)
    inquiry.refresh_from_db()
    assert inquiry.status == "new"
    assert Reservation.objects.count() == 0


def test_expired_retains_original_and_cannot_convert(identities, setup):  # noqa: F811
    _, _, data = setup
    inquiry = create(identities)
    Inquiry.objects.filter(pk=inquiry.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
    with pytest.raises(InquiryConflict):
        conversion(identities, inquiry, data)
    assert Inquiry.objects.get(pk=inquiry.pk).original_text == "Consulta ficticia"


def test_stale_revision_and_review_required(identities, setup):  # noqa: F811
    _, _, data = setup
    inquiry = create(identities)
    save_inquiry(
        actor=identities["owner"],
        tenant=identities["tenant_a"],
        inquiry_id=inquiry.pk,
        data={"revision": 1, "response_text": "Respuesta manual"},
    )
    with pytest.raises(InquiryConflict):
        conversion(identities, inquiry, data)
    with pytest.raises(ValidationError):
        conversion(identities, inquiry, data, reviewed=False)


def test_foreign_guest_property_assignee_are_not_visible(identities, setup):  # noqa: F811
    properties, guests, data = setup
    with pytest.raises(Http404):
        create(identities, assignee_id=identities["memberships"]["other"].pk)
    with pytest.raises(Http404):
        create(identities, guest_id=guests["b"].pk)
    inquiry = create(identities)
    with pytest.raises(Http404):
        conversion(identities, inquiry, data, property_id=properties["b"].pk)
    with pytest.raises(Http404):
        conversion(identities, inquiry, data, primary_guest_id=guests["b"].pk)
    assert Reservation.objects.count() == 0


def test_double_conversion_concurrent_creates_one_draft(identities, setup):  # noqa: F811
    _, _, data = setup
    inquiry = create(identities)
    barrier = Barrier(2)

    def worker():
        close_old_connections()
        try:
            barrier.wait(timeout=5)
            return conversion(identities, inquiry, data).pk
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = list(executor.map(lambda _: worker(), range(2)))
    assert first == second
    assert Reservation.objects.count() == 1
