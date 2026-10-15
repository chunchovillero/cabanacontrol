from decimal import Decimal

from rest_framework import serializers

from apps.assistant.models import TenantAISettings
from apps.common.serializers import StrictInputMixin


class SettingsSerializer(StrictInputMixin, serializers.ModelSerializer):
    daily_requests = serializers.IntegerField(min_value=1, max_value=1000)
    daily_tokens = serializers.IntegerField(min_value=1200, max_value=10000000)
    daily_audio_seconds = serializers.IntegerField(min_value=1, max_value=36000)
    daily_budget_usd = serializers.DecimalField(
        max_digits=10, decimal_places=4, min_value=Decimal("0.0001")
    )

    class Meta:
        model = TenantAISettings
        fields = [
            "enabled",
            "voice_enabled",
            "daily_requests",
            "daily_tokens",
            "daily_audio_seconds",
            "daily_budget_usd",
        ]


class MessageSerializer(StrictInputMixin, serializers.Serializer):
    text = serializers.CharField(max_length=4000, trim_whitespace=True)
    reviewed = serializers.BooleanField()
    context = serializers.CharField(max_length=12000, required=False, allow_blank=True)

    def validate_text(self, value):
        from apps.reservations.services import clean_text

        return clean_text(value, 4000, "text", required=True)

    def validate_reviewed(self, value):
        if not value:
            raise serializers.ValidationError("Revisa el texto antes de enviarlo al proveedor.")
        return value


class MessageResultSerializer(serializers.Serializer):
    results = serializers.ListField(child=serializers.DictField())
    context = serializers.CharField()


class CapabilitiesSerializer(serializers.Serializer):
    simulated = serializers.BooleanField()
    ready = serializers.BooleanField()
    enabled = serializers.BooleanField()
    voice_enabled = serializers.BooleanField()
    settings = SettingsSerializer()


class TranscriptionSerializer(StrictInputMixin, serializers.Serializer):
    audio = serializers.FileField()
    reviewed = serializers.BooleanField()

    def validate_reviewed(self, value):
        return MessageSerializer().validate_reviewed(value)


class TranscriptionResultSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=4000)


class PrepareMessageSerializer(StrictInputMixin, serializers.Serializer):
    property_id = serializers.UUIDField()
    check_in = serializers.DateField()
    check_out = serializers.DateField()
    guests = serializers.IntegerField(min_value=1, max_value=32767)
