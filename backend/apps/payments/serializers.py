from decimal import Decimal

from django.urls import reverse
from rest_framework import serializers

from apps.common.serializers import StrictInputMixin
from apps.payments.models import Payment
from apps.properties.serializers import ExactMoneyField
from apps.reservations.serializers import ZonedDateTimeField


class PaymentSerializer(serializers.ModelSerializer):
    receipt_url = serializers.SerializerMethodField()

    def get_receipt_url(self, obj) -> str | None:
        return (
            reverse("payment-receipt", kwargs={"payment_id": obj.pk}) if obj.receipt_file else None
        )

    class Meta:
        model = Payment
        fields = [
            "id",
            "reservation_id",
            "request_id",
            "amount",
            "currency",
            "paid_at",
            "method",
            "reference",
            "status",
            "receipt_url",
            "recorded_by_id",
            "voided_by_id",
            "void_reason",
            "voided_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class PaymentWriteSerializer(StrictInputMixin, serializers.Serializer):
    request_id = serializers.UUIDField()
    amount = ExactMoneyField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    paid_at = ZonedDateTimeField()
    method = serializers.ChoiceField(choices=Payment.Method.choices)
    reference = serializers.CharField(max_length=150, allow_blank=True, default="")


class PaymentVoidSerializer(StrictInputMixin, serializers.Serializer):
    reason = serializers.CharField(max_length=1000)


class ReceiptUploadSerializer(StrictInputMixin, serializers.Serializer):
    file = serializers.ImageField()
