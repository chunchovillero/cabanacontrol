from rest_framework import serializers

from apps.insights.serializers import DashboardResultSerializer, PeriodQuerySerializer
from apps.reservations.models import Reservation


class ReportQuerySerializer(PeriodQuerySerializer):
    kind = serializers.ChoiceField(
        choices=["summary", "reservations", "payments"], default="summary"
    )
    status = serializers.ChoiceField(choices=Reservation.Status.choices, required=False)
    page = serializers.IntegerField(min_value=1, max_value=10000, default=1)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if "status" in attrs and attrs["kind"] != "reservations":
            raise serializers.ValidationError(
                "El filtro de estado corresponde solo al detalle de reservas."
            )
        if attrs["kind"] == "summary" and attrs.get("page", 1) != 1:
            raise serializers.ValidationError("El resumen no tiene páginas.")
        return attrs


class ReportExportQuerySerializer(ReportQuerySerializer):
    def get_fields(self):
        fields = super().get_fields()
        fields.pop("page")
        return fields


class ReportSummarySerializer(DashboardResultSerializer):
    cancelled_count = serializers.IntegerField()
    property_id = serializers.UUIDField(allow_null=True)
    property_name = serializers.CharField()


class ReportReservationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    property_id = serializers.UUIDField()
    property_name = serializers.CharField()
    property_active = serializers.BooleanField()
    check_in = serializers.DateField()
    check_out = serializers.DateField()
    status = serializers.CharField()
    status_label = serializers.CharField()
    currency = serializers.CharField()
    total_amount = serializers.CharField()
    received_amount = serializers.CharField()
    balance = serializers.CharField()


class ReportPaymentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    reservation_id = serializers.UUIDField()
    property_id = serializers.UUIDField()
    property_name = serializers.CharField()
    paid_at = serializers.CharField()
    currency = serializers.CharField()
    amount = serializers.CharField()
    method = serializers.CharField()
    method_label = serializers.CharField()


class ReportReservationPageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    next = serializers.BooleanField()
    previous = serializers.BooleanField()
    results = ReportReservationSerializer(many=True)


class ReportPaymentPageSerializer(ReportReservationPageSerializer):
    results = ReportPaymentSerializer(many=True)
