from decimal import Decimal

from django.db.models import Case, CharField, DecimalField, F, OuterRef, Subquery, Sum, Value, When
from django.db.models.functions import Coalesce

from apps.payments.models import Payment

CHARGEABLE_STATES = ["pending", "confirmed", "checked_in", "checked_out"]


def with_balances(queryset):
    field = DecimalField(max_digits=20, decimal_places=2)
    received = (
        Payment.objects.filter(
            tenant_id=OuterRef("tenant_id"), reservation_id=OuterRef("pk"), status="recorded"
        )
        .order_by()
        .values("reservation_id")
        .annotate(total=Sum("amount", output_field=field))
        .values("total")
    )
    return (
        queryset.annotate(
            received_amount=Coalesce(
                Subquery(received, output_field=field), Value(Decimal("0.00")), output_field=field
            )
        )
        .annotate(balance=F("total_amount") - F("received_amount"))
        .annotate(
            payment_state=Case(
                When(balance__lt=0, then=Value("credit")),
                When(balance=0, then=Value("paid")),
                When(received_amount=0, then=Value("unpaid")),
                default=Value("partial"),
                output_field=CharField(),
            )
        )
    )


def received_for(reservation):
    return Payment.objects.filter(
        tenant_id=reservation.tenant_id, reservation=reservation, status="recorded"
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
