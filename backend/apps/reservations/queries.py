from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from apps.payments.queries import with_balances
from apps.properties.models import Property
from apps.reservations.models import AvailabilityBlock, Reservation


def availability_for_tenant(tenant, start, end, guests=1):
    return (
        Property.objects.filter(tenant=tenant, active=True)
        .annotate(
            reservation_busy=Exists(blocking_reservations(tenant, OuterRef("pk"), start, end)),
            block_busy=Exists(blocking_blocks(tenant, OuterRef("pk"), start, end)),
        )
        .annotate(
            available=~Q(reservation_busy=True) & ~Q(block_busy=True) & Q(capacity__gte=guests)
        )
        .order_by("name", "pk")
    )


def reservations_for_tenant(tenant):
    if tenant is None:
        return Reservation.objects.none()
    return with_balances(
        Reservation.objects.filter(tenant=tenant).select_related("property", "primary_guest")
    )


def blocking_reservations(tenant, property_id, start, end, *, exclude=None, now=None):
    now = now or timezone.now()
    query = Reservation.objects.filter(
        Q(status__in=["confirmed", "checked_in"]) | Q(status="pending", hold_until__gt=now),
        tenant=tenant,
        property_id=property_id,
        check_in__lt=end,
        check_out__gt=start,
    )
    if exclude is not None:
        query = query.exclude(pk=exclude)
    return query


def blocking_blocks(tenant, property_id, start, end, *, exclude=None):
    query = AvailabilityBlock.objects.filter(
        tenant=tenant,
        property_id=property_id,
        active=True,
        start_date__lt=end,
        end_date__gt=start,
    )
    if exclude is not None:
        query = query.exclude(pk=exclude)
    return query
