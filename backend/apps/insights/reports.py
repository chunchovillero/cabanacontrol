import csv
from datetime import datetime, time
from io import StringIO
from zoneinfo import ZoneInfo

from django.db import connection, transaction
from rest_framework.exceptions import NotFound, ValidationError

from apps.insights.queries import dashboard_metrics, property_scope
from apps.payments.models import Payment
from apps.payments.queries import with_balances
from apps.reservations.models import Reservation

PAGE_SIZE = 25
EXPORT_LIMIT = 5000


def safe_csv_cell(value):
    text = str(value)
    # CSV quoting alone does not stop spreadsheet formula evaluation.
    probe = text
    while probe and (probe[0].isspace() or probe[0] in "\ufeff\x00"):
        probe = probe[1:]
    if any(char in text[: len(text) - len(probe)] for char in "\t\r\n") or probe.startswith(
        ("=", "+", "-", "@", "＝", "＋", "－", "＠")
    ):
        return "'" + text
    return text


def csv_document(headers, rows):
    output = StringIO(newline="")
    output.write("\ufeff")
    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow([safe_csv_cell(cell) for cell in row])
    return output.getvalue()


def report_queryset(tenant, data):
    properties = property_scope(tenant, data.get("property_id"))
    start, end = data["from"], data["to"]
    if data["kind"] == "reservations":
        rows = with_balances(
            Reservation.objects.filter(
                tenant=tenant, property__in=properties, check_in__gte=start, check_in__lt=end
            )
        ).select_related("property")
        if data.get("status"):
            rows = rows.filter(status=data["status"])
        return rows.order_by("check_in", "pk")
    zone = ZoneInfo(tenant.timezone)
    return (
        Payment.objects.filter(
            tenant=tenant,
            reservation__tenant=tenant,
            reservation__property__in=properties,
            status="recorded",
            paid_at__gte=datetime.combine(start, time.min, zone),
            paid_at__lt=datetime.combine(end, time.min, zone),
        )
        .select_related("reservation__property")
        .order_by("paid_at", "pk")
    )


def report_row(item, kind, zone):
    if kind == "reservations":
        return {
            "id": str(item.pk),
            "property_id": str(item.property_id),
            "property_name": item.property.name,
            "property_active": item.property.active,
            "check_in": item.check_in.isoformat(),
            "check_out": item.check_out.isoformat(),
            "status": item.status,
            "status_label": item.get_status_display(),
            "currency": item.currency,
            "total_amount": f"{item.total_amount:.2f}",
            "received_amount": f"{item.received_amount:.2f}",
            "balance": f"{item.balance:.2f}",
        }
    return {
        "id": str(item.pk),
        "reservation_id": str(item.reservation_id),
        "property_id": str(item.reservation.property_id),
        "property_name": item.reservation.property.name,
        "paid_at": item.paid_at.astimezone(zone).isoformat(),
        "currency": item.currency,
        "amount": f"{item.amount:.2f}",
        "method": item.method,
        "method_label": item.get_method_display(),
    }


def snapshot_report(tenant, data, *, export=False):
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        if data["kind"] == "summary":
            result = dashboard_metrics(tenant, data["from"], data["to"], data.get("property_id"))
            properties = property_scope(tenant, data.get("property_id"))
            selected_property = properties.first() if data.get("property_id") else None
            result["property_id"] = str(selected_property.pk) if selected_property else None
            result["property_name"] = (
                selected_property.name if selected_property else "Todas las cabañas"
            )
            result["cancelled_count"] = Reservation.objects.filter(
                tenant=tenant,
                property__in=properties,
                status="cancelled",
                check_in__gte=data["from"],
                check_in__lt=data["to"],
            ).count()
            return result
        rows = report_queryset(tenant, data)
        count = rows.count()
        page = data.get("page", 1)
        if export:
            if count > EXPORT_LIMIT:
                raise ValidationError(
                    "La exportación supera 5.000 filas. Reduce el periodo o filtra una cabaña."
                )
            selected = rows[:EXPORT_LIMIT]
        else:
            offset = (page - 1) * PAGE_SIZE
            if offset >= count and page != 1:
                raise NotFound("Página inexistente.")
            selected = rows[offset : offset + PAGE_SIZE]
        return {
            "count": count,
            "page": page,
            "next": not export and page * PAGE_SIZE < count,
            "previous": not export and page > 1,
            "results": [
                report_row(item, data["kind"], ZoneInfo(tenant.timezone)) for item in selected
            ],
        }


def report_csv(result, kind):
    if kind == "summary":
        headers = [
            "Desde",
            "Hasta exclusiva",
            "Moneda",
            "Cobrado",
            "Pactado",
            "Deuda",
            "Saldo a favor",
            "Noches reservadas",
            "Noches base de cabañas activas",
            "Ocupación porcentaje",
            "Noches bloqueadas",
            "Reservas canceladas por entrada",
            "Cabaña ID",
            "Cabaña",
        ]
        return csv_document(
            headers,
            [
                [
                    result["from_date"],
                    result["to_date"],
                    row["currency"],
                    row["collected"],
                    row["agreed"],
                    row["outstanding"],
                    row["credit"],
                    result["occupied_nights"],
                    result["capacity_nights"],
                    result["occupancy_percent"],
                    result["blocked_nights"],
                    result["cancelled_count"],
                    result["property_id"] or "",
                    result["property_name"],
                ]
                for row in result["money"]
            ],
        )
    if kind == "reservations":
        keys = [
            "id",
            "property_id",
            "property_name",
            "check_in",
            "check_out",
            "status_label",
            "currency",
            "total_amount",
            "received_amount",
            "balance",
        ]
        headers = [
            "Reserva ID",
            "Cabaña ID",
            "Cabaña",
            "Entrada",
            "Salida exclusiva",
            "Estado",
            "Moneda",
            "Precio pactado",
            "Recibido válido actual",
            "Saldo actual",
        ]
    else:
        keys = [
            "id",
            "reservation_id",
            "property_id",
            "property_name",
            "paid_at",
            "currency",
            "amount",
            "method_label",
        ]
        headers = [
            "Pago ID",
            "Reserva ID",
            "Cabaña ID",
            "Cabaña",
            "Fecha recibida local",
            "Moneda",
            "Monto",
            "Método",
        ]
    return csv_document(headers, [[row[key] for key in keys] for row in result["results"]])
