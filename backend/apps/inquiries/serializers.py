from django.utils import timezone
from rest_framework import serializers

from apps.common.serializers import StrictInputMixin
from apps.inquiries.models import Inquiry
from apps.reservations.serializers import ReservationWriteSerializer


class InquirySerializer(serializers.ModelSerializer):
    expired = serializers.SerializerMethodField()
    expiry_warning = serializers.SerializerMethodField()

    def get_expired(self, obj) -> bool:
        return obj.expires_at <= timezone.now() or obj.archived_at is not None

    def get_expiry_warning(self, obj) -> bool:
        return (obj.expires_at - timezone.now()).total_seconds() <= 7 * 86400

    class Meta:
        model = Inquiry
        fields = [
            "id",
            "channel",
            "original_text",
            "review_text",
            "extraction",
            "response_text",
            "status",
            "assignee_id",
            "guest_id",
            "revision",
            "converted_reservation_id",
            "created_at",
            "updated_at",
            "expires_at",
            "archived_at",
            "expired",
            "expiry_warning",
        ]
        read_only_fields = fields


class InquiryWriteSerializer(StrictInputMixin, serializers.Serializer):
    channel = serializers.ChoiceField(choices=Inquiry.Channel.choices)
    original_text = serializers.CharField(max_length=4000)
    review_text = serializers.CharField(max_length=4000, allow_blank=True, required=False)
    response_text = serializers.CharField(max_length=4000, allow_blank=True, required=False)
    status = serializers.ChoiceField(
        choices=["new", "responded", "waiting_customer", "discarded"], required=False
    )
    assignee_id = serializers.UUIDField(allow_null=True, required=False)
    guest_id = serializers.UUIDField(allow_null=True, required=False)

    def validate_original_text(self, value):
        from apps.reservations.services import clean_text

        return clean_text(value, 4000, "original_text", required=True)


class InquiryUpdateSerializer(InquiryWriteSerializer):
    revision = serializers.IntegerField(min_value=1)


class AnalyzeSerializer(StrictInputMixin, serializers.Serializer):
    revision = serializers.IntegerField(min_value=1)
    text = serializers.CharField(max_length=4000)
    reviewed = serializers.BooleanField()

    def validate_text(self, value):
        from apps.assistant.serializers import MessageSerializer

        return MessageSerializer().validate_text(value)


class ConvertSerializer(ReservationWriteSerializer):
    revision = serializers.IntegerField(min_value=1)
    reviewed = serializers.BooleanField()

    def validate_hold_until(self, value):
        if value is not None:
            raise serializers.ValidationError("Un borrador no retiene disponibilidad.")
        return value
