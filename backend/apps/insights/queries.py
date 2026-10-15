from datetime import datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db import connection, transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.insights.intervals import occupied_nights
from apps.payments.models import Payment
from apps.payments.queries import CHARGEABLE_STATES, with_balances
from apps.properties.models import Property
from apps.reservations.models import AvailabilityBlock, Reservation

OCCUPIED_STATES = ["confirmed", "checked_in", "checked_out"]


def property_scope(tenant, property_id=None):
    properties = Property.objects.filter(tenant=tenant)
    if property_id:
        get_object_or_404(properties, pk=property_id)
        properties = properties.filter(pk=property_id)
    return properties


def calendar_events(tenant, start, end, property_id=None):
    properties = property_scope(tenant, property_id)
    now = timezone.now()
    reservations = (
        Reservation.objects.filter(
            tenant=tenant, property__in=properties, check_in__lt=end, check_out__gt=start
        )
        .select_related("property")
        .order_by("check_in", "pk")
    )
    blocks = (
        AvailabilityBlock.objects.filter(
            tenant=tenant,
            property__in=properties,
            active=True,
            start_date__lt=end,
            end_date__gt=start,
        )
        .select_related("property")
        .order_by("start_date", "pk")
    )
    events = []
    for item in reservations:
        blocking = item.status in ["confirmed", "checked_in"] or (
            item.status == "pending" and item.hold_until is not None and item.hold_until > now
        )
        label = item.get_status_display()
        if item.status == "pending" and not blocking:
            label += " · Retención vencida"
        events.append(
            {
                "id": f"reservation:{item.pk}",
                "kind": "reservation",
                "entity_id": item.pk,
                "property_id": item.property_id,
                "property_name": item.property.name,
                "property_active": item.property.active,
                "title": f"{item.property.name} · {label}",
                "start": item.check_in,
                "end": item.check_out,
                "status": item.status,
                "blocks_inventory": blocking,
                "url": f"/reservas/{item.pk}",
            }
        )
    for item in blocks:
        events.append(
            {
                "id": f"block:{item.pk}",
                "kind": "block",
                "entity_id": item.pk,
                "property_id": item.property_id,
                "property_name": item.property.name,
                "property_active": item.property.active,
                "title": f"{item.property.name} · {item.get_reason_display()}",
                "start": item.start_date,
                "end": item.end_date,
                "status": item.reason,
                "blocks_inventory": True,
                "url": "/reservas/bloqueos",
            }
        )
    return {"timezone": tenant.timezone, "events": events}


def snapshot_dashboard(tenant, start, end, property_id=None):
    # Varias agregaciones deben leer el mismo estado de pagos/reservas.
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        return dashboard_metrics(tenant, start, end, property_id)


def snapshot_calendar(tenant, start, end, property_id=None):
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        return calendar_events(tenant, start, end, property_id)


def dashboard_metrics(tenant, start, end, property_id=None):
    now = timezone.now()
    zone = ZoneInfo(tenant.timezone)
    today = timezone.localdate(now, zone)
    properties = property_scope(tenant, property_id)
    active = properties.filter(active=True)
    reservation_scope = Reservation.objects.filter(tenant=tenant, property__in=properties)
    current = reservation_scope.filter(
        property__in=active, check_in__lte=today, check_out__gt=today
    )
    occupied_ids = set(
        current.filter(status__in=["confirmed", "checked_in"]).values_list("property_id", flat=True)
    )
    retained_ids = set(
        current.filter(status="pending", hold_until__gt=now).values_list("property_id", flat=True)
    )
    blocked_ids = set(
        AvailabilityBlock.objects.filter(
            tenant=tenant,
            property__in=active,
            active=True,
            start_date__lte=today,
            end_date__gt=today,
        ).values_list("property_id", flat=True)
    )
    active_count = active.count()
    period_reservations = reservation_scope.filter(
        property__in=active, status__in=OCCUPIED_STATES, check_in__lt=end, check_out__gt=start
    ).values_list("property_id", "check_in", "check_out")
    period_blocks = AvailabilityBlock.objects.filter(
        tenant=tenant, property__in=active, active=True, start_date__lt=end, end_date__gt=start
    ).values_list("property_id", "start_date", "end_date")
    nights = occupied_nights(list(period_reservations), start, end)
    capacity = active_count * (end - start).days
    percent = (
        (Decimal(nights) * 100 / capacity).quantize(Decimal("0.01"))
        if capacity
        else Decimal("0.00")
    )
    # paid_at se agrupa por fechas locales; el extremo superior es exclusivo.
    start_at = datetime.combine(start, time.min, zone)
    end_at = datetime.combine(end, time.min, zone)
    collected = (
        Payment.objects.filter(
            tenant=tenant,
            reservation__tenant=tenant,
            reservation__property__in=properties,
            status="recorded",
            paid_at__gte=start_at,
            paid_at__lt=end_at,
        )
        .values("currency")
        .annotate(total=Sum("amount"))
    )
    agreed_scope = reservation_scope.filter(
        status__in=OCCUPIED_STATES, check_in__gte=start, check_in__lt=end
    )
    agreed = agreed_scope.values("currency").annotate(total=Sum("total_amount"))
    balances = with_balances(reservation_scope.filter(check_in__gte=start, check_in__lt=end))
    outstanding = (
        balances.filter(status__in=CHARGEABLE_STATES, balance__gt=0)
        .values("currency")
        .annotate(total=Sum("balance"))
    )
    credit = balances.filter(balance__lt=0).values("currency").annotate(total=Sum("balance"))
    totals = {}
    for key, rows in (
        ("collected", collected),
        ("agreed", agreed),
        ("outstanding", outstanding),
        ("credit", credit),
    ):
        for row in rows:
            group = totals.setdefault(
                row["currency"],
                {
                    "currency": row["currency"],
                    "collected": "0.00",
                    "agreed": "0.00",
                    "outstanding": "0.00",
                    "credit": "0.00",
                },
            )
            amount = -row["total"] if key == "credit" else row["total"]
            group[key] = f"{amount:.2f}"
    if not totals:
        totals[tenant.currency] = {
            "currency": tenant.currency,
            "collected": "0.00",
            "agreed": "0.00",
            "outstanding": "0.00",
            "credit": "0.00",
        }
    return {
        "timezone": tenant.timezone,
        "from_date": start,
        "to_date": end,
        "today": {
            "date": today,
            "active_properties": active_count,
            "occupied": len(occupied_ids),
            "retained": len(retained_ids),
            "blocked": len(blocked_ids),
            "available": active_count - len(occupied_ids | retained_ids | blocked_ids),
            "arrivals": reservation_scope.filter(
                property__in=active, status__in=["confirmed", "checked_in"], check_in=today
            ).count(),
            "departures": reservation_scope.filter(
                property__in=active,
                status__in=["confirmed", "checked_in", "checked_out"],
                check_out=today,
            ).count(),
        },
        "occupied_nights": nights,
        "capacity_nights": capacity,
        "occupancy_percent": f"{percent:.2f}",
        "blocked_nights": occupied_nights(list(period_blocks), start, end),
        "money": [totals[key] for key in sorted(totals)],
    }
