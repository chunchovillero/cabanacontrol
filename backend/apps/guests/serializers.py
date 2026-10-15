from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.common.serializers import StrictInputMixin
from apps.guests.models import Guest
from apps.guests.permissions import can_manage_guests
from apps.guests.validators import mask_document, normalize_document, normalize_phone


class GuestListSerializer(serializers.ModelSerializer):
    document_masked = serializers.SerializerMethodField()

    class Meta:
        model = Guest
        fields = ["id", "first_name", "last_name", "document_type", "document_masked", "active"]
        read_only_fields = fields

    def get_document_masked(self, obj) -> str:
        return mask_document(obj.document_number)


class GuestDetailSerializer(GuestListSerializer):
    document_number = serializers.SerializerMethodField()
    notes = serializers.SerializerMethodField()

    class Meta(GuestListSerializer.Meta):
        fields = [
            *GuestListSerializer.Meta.fields,
            "document_number",
            "phone",
            "email",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_document_number(self, obj) -> str | None:
        return obj.document_number if can_manage_guests(self.context["request"]) else None

    def get_notes(self, obj) -> str | None:
        return obj.notes if can_manage_guests(self.context["request"]) else None


class GuestWriteSerializer(StrictInputMixin, serializers.ModelSerializer):
    class Meta:
        model = Guest
        fields = [
            "first_name",
            "last_name",
            "document_type",
            "document_number",
            "phone",
            "email",
            "notes",
            "active",
        ]
        validators = []  # RUT normalizado y colisiones se validan en el servicio/BD.

    def validate(self, attrs):
        kind = attrs.get("document_type", self.instance.document_type if self.instance else None)
        number = attrs.get(
            "document_number", self.instance.document_number if self.instance else ""
        )
        try:
            normalized = normalize_document(kind, number)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"document_number": exc.messages}) from exc
        if "document_type" in attrs or "document_number" in attrs:
            attrs["document_number"] = normalized
        return attrs

    def validate_phone(self, value):
        try:
            return normalize_phone(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc

    def validate_email(self, value):
        return value.strip().lower()


class GuestSearchSerializer(StrictInputMixin, serializers.Serializer):
    query = serializers.CharField(max_length=150, allow_blank=True, default="")
    active = serializers.BooleanField(required=False)
    page = serializers.IntegerField(min_value=1, default=1)


class GuestSearchResultSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    page = serializers.IntegerField()
    has_next = serializers.BooleanField()
    has_previous = serializers.BooleanField()
    results = GuestListSerializer(many=True)
