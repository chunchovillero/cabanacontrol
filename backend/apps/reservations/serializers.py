import re
from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from apps.common.serializers import StrictInputMixin
from apps.guests.serializers import GuestListSerializer
from apps.payments.queries import received_for
from apps.properties.serializers import ExactMoneyField
from apps.reservations.models import AvailabilityBlock, Reservation


class ZonedDateTimeField(serializers.DateTimeField):
    def to_internal_value(self, value):
        if not isinstance(value, str) or not re.search(r"(?:Z|[+-]\d{2}:\d{2})$", value):
            raise serializers.ValidationError(
                "Incluye la zona horaria en la fecha y hora ISO 8601."
            )
        return super().to_internal_value(value)


class ReservationSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)
    guest = GuestListSerializer(source="primary_guest", read_only=True)
    hold_active = serializers.SerializerMethodField()
    received_amount = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    payment_state = serializers.SerializerMethodField()

    def received(self, obj):
        if not hasattr(obj, "received_amount"):
            obj.received_amount = received_for(obj)
        return obj.received_amount

    def get_received_amount(self, obj) -> str:
        return f"{self.received(obj):.2f}"

    def get_balance(self, obj) -> str:
        return f"{obj.total_amount - self.received(obj):.2f}"

    def get_payment_state(self, obj) -> str:
        balance = obj.total_amount - self.received(obj)
        return (
            "credit"
            if balance < 0
            else "paid"
            if balance == 0
            else "unpaid"
            if self.received(obj) == 0
            else "partial"
        )

    def get_hold_active(self, obj) -> bool:
        return (
            obj.status == "pending"
            and obj.hold_until is not None
            and obj.hold_until > timezone.now()
        )

    class Meta:
        model = Reservation
        fields = [
            "id",
            "property_id",
            "property_name",
            "primary_guest_id",
            "guest",
            "check_in",
            "check_out",
            "adults",
            "children",
            "status",
            "hold_until",
            "hold_active",
            "total_amount",
            "received_amount",
            "balance",
            "payment_state",
            "currency",
            "source",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ReservationDetailSerializer(ReservationSerializer):
    class Meta(ReservationSerializer.Meta):
        fields = [*ReservationSerializer.Meta.fields, "notes", "cancel_reason"]
        read_only_fields = fields


class ReservationWriteSerializer(StrictInputMixin, serializers.Serializer):
    property_id = serializers.UUIDField()
    primary_guest_id = serializers.UUIDField()
    check_in = serializers.DateField()
    check_out = serializers.DateField()
    adults = serializers.IntegerField(min_value=1, max_value=32767)
    children = serializers.IntegerField(min_value=0, max_value=32767)
    total_amount = ExactMoneyField(max_digits=14, decimal_places=2, min_value=Decimal("0"))
    source = serializers.ChoiceField(choices=Reservation.Source.choices)
    notes = serializers.CharField(max_length=2000, allow_blank=True, default="")
    hold_until = ZonedDateTimeField(allow_null=True, required=False)


class ReservationCreateSerializer(ReservationWriteSerializer):
    status = serializers.ChoiceField(choices=["draft", "pending", "confirmed"])


class TransitionSerializer(StrictInputMixin, serializers.Serializer):
    status = serializers.ChoiceField(choices=Reservation.Status.choices)
    reason = serializers.CharField(max_length=1000, allow_blank=True, default="")
    hold_until = ZonedDateTimeField(required=False, allow_null=True)


class CancelSerializer(StrictInputMixin, serializers.Serializer):
    reason = serializers.CharField(max_length=1000)


class ConfirmSerializer(StrictInputMixin, serializers.Serializer):
    pass


class BlockSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source="property.name", read_only=True)

    class Meta:
        model = AvailabilityBlock
        fields = [
            "id",
            "property_id",
            "property_name",
            "start_date",
            "end_date",
            "reason",
            "notes",
            "active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class BlockWriteSerializer(StrictInputMixin, serializers.Serializer):
    property_id = serializers.UUIDField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.ChoiceField(choices=AvailabilityBlock.Reason.choices)
    notes = serializers.CharField(max_length=2000, allow_blank=True, default="")
    active = serializers.BooleanField(default=True)


class AvailabilityQuerySerializer(StrictInputMixin, serializers.Serializer):
    page = serializers.IntegerField(min_value=1, required=False)
    property_id = serializers.UUIDField(required=False)
    guests = serializers.IntegerField(min_value=1, max_value=32767, required=False)

    # Nombres coinciden con los parámetros from/to del plan.
    def get_fields(self):
        fields = super().get_fields()
        fields["from"] = serializers.DateField()
        fields["to"] = serializers.DateField()
        return fields


class AvailabilityItemSerializer(serializers.Serializer):
    property_id = serializers.UUIDField()
    property_name = serializers.CharField()
    capacity = serializers.IntegerField()
    available = serializers.BooleanField()
