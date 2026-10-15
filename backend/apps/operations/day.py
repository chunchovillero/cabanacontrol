from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.db import connection, transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound

from apps.insights.queries import property_scope
from apps.operations.models import HousekeepingTask
from apps.reservations.models import AvailabilityBlock, Reservation


def daily_snapshot(tenant, day, kind, page, property_id=None):
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        properties = property_scope(tenant, property_id)
        reservations = Reservation.objects.filter(tenant=tenant, property__in=properties)
        scopes = {
            "cleaning": HousekeepingTask.objects.filter(
                tenant=tenant,
                property__in=properties,
                status__in=["pending", "in_progress"],
                due_at__lt=datetime.combine(
                    day + timedelta(days=1), time.min, ZoneInfo(tenant.timezone)
                ),
            ),
            "arrivals": reservations.filter(check_in=day, status__in=["confirmed", "checked_in"]),
            "departures": reservations.filter(
                check_out=day, status__in=["confirmed", "checked_in", "checked_out"]
            ),
            "overdue_stays": reservations.filter(check_out__lt=day, status="checked_in"),
            "expired_holds": reservations.filter(status="pending", hold_until__lte=timezone.now()),
            "maintenance": AvailabilityBlock.objects.filter(
                tenant=tenant,
                property__in=properties,
                active=True,
                reason="maintenance",
                start_date__lte=day,
                end_date__gt=day,
            ),
        }
        counts = {key: scope.count() for key, scope in scopes.items()}
        count = counts[kind]
        offset = (page - 1) * 25
        if offset >= count and page != 1:
            raise NotFound("Página inexistente.")
        rows = scopes[kind].select_related("property").order_by("pk")[offset : offset + 25]
        events = []
        for row in rows:
            block = kind == "maintenance"
            cleaning = kind == "cleaning"
            due_date = row.due_at.astimezone(ZoneInfo(tenant.timezone)).date() if cleaning else None
            events.append(
                {
                    "id": str(row.pk),
                    "property_name": row.property.name,
                    "property_active": row.property.active,
                    "start": due_date if cleaning else (row.start_date if block else row.check_in),
                    "end": due_date if cleaning else (row.end_date if block else row.check_out),
                    "status": row.reason if block else row.status,
                    "url": f"/limpieza/{row.pk}"
                    if cleaning
                    else ("/reservas/bloqueos" if block else f"/reservas/{row.pk}"),
                }
            )
        return {
            "date": day,
            "timezone": tenant.timezone,
            "kind": kind,
            "counts": counts,
            "count": count,
            "page": page,
            "next": offset + 25 < count,
            "previous": page > 1,
            "results": events,
        }
