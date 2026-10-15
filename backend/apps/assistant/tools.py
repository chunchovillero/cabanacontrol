from datetime import datetime, time
from zoneinfo import ZoneInfo

from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from apps.payments.models import Payment
from apps.payments.queries import CHARGEABLE_STATES
from apps.reservations.intervals import validate_interval
from apps.reservations.models import Reservation
from apps.reservations.queries import availability_for_tenant, reservations_for_tenant
from apps.reservations.services import local_today


def page_result(query, page, render):
    count = query.count()
    offset = (page - 1) * 25
    return {
        "total": count,
        "page": page,
        "has_more": offset + 25 < count,
        "items": [render(item) for item in query[offset : offset + 25]],
    }


def interval(start, end):
    validate_interval(start, end)
    if (end - start).days > 366:
        raise ValidationError("El rango máximo es de 366 días.")


def available(tenant, args):
    interval(args.check_in, args.check_out)
    if args.check_in < local_today(tenant):
        raise ValidationError("Consulta disponibilidad desde hoy.")
    query = availability_for_tenant(tenant, args.check_in, args.check_out, args.guests)
    if args.property_id:
        get_object_or_404(query, pk=args.property_id)
        query = query.filter(pk=args.property_id)
    return query.filter(available=True)


def execute(tenant, name, args):
    if name == "clarify":
        labels = {
            "year": "Indica el año de las fechas.",
            "dates": "Indica entrada y salida con fecha completa.",
            "guests": "Indica cuántas personas se alojarán.",
            "property": "Selecciona una cabaña de tu empresa.",
            "current_balances": "Solo hay saldos actuales, no saldos históricos.",
            "unsupported": "Esta operación requiere el formulario y revisión humana.",
        }
        return {"messages": [labels[key] for key in args.missing]}
    if name == "search_available_properties":
        return {
            "check_in": str(args.check_in),
            "check_out": str(args.check_out),
            "guests": args.guests,
            "price_notice": "Precio por confirmar",
            **page_result(
                available(tenant, args),
                args.page,
                lambda prop: {
                    "id": str(prop.pk),
                    "name": prop.name,
                    "capacity": prop.capacity,
                    "url": f"/cabanas/{prop.pk}",
                },
            ),
        }
    if name == "prepare_whatsapp_message":
        prop = available(tenant, args).first()
        if not prop:
            return {"message": "La cabaña no está disponible para esas fechas."}
        return {
            "message": (
                f"Tenemos disponibilidad en {prop.name} desde {args.check_in} "
                f"hasta {args.check_out} para {args.guests} personas. Precio por confirmar. "
                "La disponibilidad debe verificarse al confirmar la reserva."
            )
        }
    if name == "list_arrivals":
        query = (
            Reservation.objects.filter(
                tenant=tenant, check_in=args.date, status__in=["confirmed", "checked_in"]
            )
            .select_related("property", "primary_guest")
            .order_by("pk")
        )
        return {
            "date": str(args.date),
            **page_result(
                query,
                args.page,
                lambda row: {
                    "id": str(row.pk),
                    "property": row.property.name,
                    "guest": f"{row.primary_guest.first_name} {row.primary_guest.last_name}",
                    "url": f"/reservas/{row.pk}",
                },
            ),
        }
    if name == "list_outstanding_balances":
        if args.as_of_date != local_today(tenant):
            return {"messages": ["Solo hay saldos actuales, no saldos históricos."]}
        query = (
            reservations_for_tenant(tenant)
            .filter(status__in=CHARGEABLE_STATES, balance__gt=0)
            .order_by("pk")
        )
        return {
            "date": str(args.as_of_date),
            **page_result(
                query,
                args.page,
                lambda row: {
                    "id": str(row.pk),
                    "property": row.property.name,
                    "amount": f"{row.balance:.2f}",
                    "currency": row.currency,
                    "url": f"/reservas/{row.pk}",
                },
            ),
        }
    if name == "summarize_collections":
        interval(args.start_date, args.end_date)
        zone = ZoneInfo(tenant.timezone)
        query = (
            Payment.objects.filter(
                tenant=tenant,
                reservation__tenant=tenant,
                status="recorded",
                paid_at__gte=datetime.combine(args.start_date, time.min, zone),
                paid_at__lt=datetime.combine(args.end_date, time.min, zone),
            )
            .values("currency")
            .annotate(total=Sum("amount"))
            .order_by("currency")
        )
        return {
            "start_date": str(args.start_date),
            "end_date": str(args.end_date),
            **page_result(
                query,
                args.page,
                lambda row: {"currency": row["currency"], "amount": f"{row['total']:.2f}"},
            ),
        }
    raise ValidationError("Herramienta no permitida.")
