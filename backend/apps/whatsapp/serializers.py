from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from apps.common.serializers import StrictInputMixin
from apps.whatsapp.models import (
    Connection,
    ConsentRecord,
    Conversation,
    Message,
    OutboxJob,
    Template,
)


class ConnectionSerializer(serializers.ModelSerializer):
    token_configured = serializers.SerializerMethodField()

    def get_token_configured(self, obj) -> bool:
        return bool(obj.access_token_ciphertext)

    class Meta:
        model = Connection
        fields = [
            "id",
            "business_id",
            "phone_number_id",
            "display_phone",
            "enabled",
            "revision",
            "token_configured",
        ]
        read_only_fields = fields


class ConnectionWriteSerializer(StrictInputMixin, serializers.Serializer):
    business_id = serializers.CharField(max_length=40, required=False)
    phone_number_id = serializers.CharField(max_length=40, required=False)
    display_phone = serializers.CharField(max_length=20, required=False)
    access_token = serializers.CharField(max_length=2048, required=False, write_only=True)
    enabled = serializers.BooleanField(required=False)
    revision = serializers.IntegerField(min_value=1, required=False)

    def validate_access_token(self, value):
        from apps.reservations.services import clean_text

        return clean_text(value, 2048, "access_token", required=True)


@extend_schema_serializer(component_name="WhatsAppCapabilities")
class CapabilitiesSerializer(serializers.Serializer):
    ready = serializers.BooleanField()
    enabled = serializers.BooleanField()
    simulated = serializers.BooleanField()


class ConversationSerializer(serializers.ModelSerializer):
    consent_granted = serializers.SerializerMethodField()
    expired = serializers.SerializerMethodField()

    def get_consent_granted(self, obj) -> bool:
        record = ConsentRecord.objects.filter(conversation=obj).first()
        return bool(record and record.granted)

    def get_expired(self, obj) -> bool:
        from django.utils import timezone

        return obj.expires_at <= timezone.now()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "contact_phone",
            "last_inbound_at",
            "revision",
            "expires_at",
            "consent_granted",
            "expired",
        ]
        read_only_fields = fields


@extend_schema_serializer(component_name="WhatsAppMessage")
class MessageSerializer(serializers.ModelSerializer):
    inquiry_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = Message
        fields = [
            "id",
            "conversation_id",
            "direction",
            "text",
            "status",
            "occurred_at",
            "expires_at",
            "inquiry_id",
        ]
        read_only_fields = fields


class SendSerializer(StrictInputMixin, serializers.Serializer):
    conversation_id = serializers.UUIDField()
    text = serializers.CharField(max_length=4000)
    revision = serializers.IntegerField(min_value=1)
    request_id = serializers.UUIDField()
    reviewed = serializers.BooleanField()
    template_id = serializers.UUIDField(required=False, allow_null=True, default=None)


class ConsentSerializer(StrictInputMixin, serializers.Serializer):
    conversation_id = serializers.UUIDField()
    revision = serializers.IntegerField(min_value=1)
    granted = serializers.BooleanField()
    source = serializers.CharField(max_length=150)


@extend_schema_serializer(many=False)
class MessagePageSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = MessageSerializer(many=True)
    conversation = ConversationSerializer()


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutboxJob
        fields = ["id", "message_id", "state", "attempts", "last_error_code", "created_at"]
        read_only_fields = fields


class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = ["id", "name", "language", "body", "approved", "enabled", "purpose", "verified_at"]
        read_only_fields = fields


class TemplateWriteSerializer(StrictInputMixin, serializers.Serializer):
    name = serializers.RegexField(r"^[a-z0-9_]{1,100}$")
    language = serializers.RegexField(r"^[a-z]{2}(?:_[A-Z]{2})?$")
    body = serializers.CharField(max_length=4000)
    approved = serializers.BooleanField()
    enabled = serializers.BooleanField()
    reviewed = serializers.BooleanField()


class PrepareSerializer(StrictInputMixin, serializers.Serializer):
    conversation_id = serializers.UUIDField()


class PreparedSerializer(serializers.Serializer):
    text = serializers.CharField()
    revision = serializers.IntegerField()
