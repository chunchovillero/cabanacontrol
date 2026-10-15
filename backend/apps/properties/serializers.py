import re
from decimal import Decimal

from django.urls import reverse
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.common.serializers import StrictInputMixin
from apps.properties.models import Property, PropertyPhoto


class ExactMoneyField(serializers.DecimalField):
    def to_internal_value(self, data):
        if isinstance(data, float):
            raise serializers.ValidationError(
                "Envía el importe como texto decimal, sin números de punto flotante."
            )
        return super().to_internal_value(data)


class PropertyPhotoSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = PropertyPhoto
        fields = ["id", "url", "alt", "order", "active"]

    def get_url(self, obj) -> str:
        return reverse(
            "property-photo-file", kwargs={"property_id": obj.property_id, "photo_id": obj.pk}
        )


class PropertySerializer(serializers.ModelSerializer):
    currency = serializers.CharField(source="tenant.currency", read_only=True)
    photos = serializers.SerializerMethodField()

    @extend_schema_field(PropertyPhotoSerializer(many=True))
    def get_photos(self, obj):
        photos = getattr(obj, "active_photos", None)
        if photos is None:
            photos = obj.photos.filter(active=True)
        return PropertyPhotoSerializer(photos, many=True).data

    class Meta:
        model = Property
        fields = [
            "id",
            "name",
            "code",
            "description",
            "capacity",
            "address",
            "base_rate",
            "currency",
            "check_in_time",
            "check_out_time",
            "active",
            "photos",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class PropertyWriteSerializer(StrictInputMixin, serializers.ModelSerializer):
    code = serializers.CharField(max_length=30)
    base_rate = ExactMoneyField(max_digits=14, decimal_places=2, min_value=Decimal("0"))

    class Meta:
        model = Property
        fields = [
            "name",
            "code",
            "description",
            "capacity",
            "address",
            "base_rate",
            "check_in_time",
            "check_out_time",
            "active",
        ]

    def validate_code(self, value):
        value = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9_-]+", value):
            raise serializers.ValidationError(
                "Usa letras, números, guion o guion bajo para el código."
            )
        queryset = Property.objects.filter(tenant=self.context["request"].tenant, code=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError(
                "Ya existe una cabaña con ese código en esta empresa."
            )
        return value

    def validate_check_in_time(self, value):
        if value.tzinfo is not None:
            raise serializers.ValidationError("Ingresa un horario local, sin zona horaria.")
        return value

    validate_check_out_time = validate_check_in_time


class PhotoUploadSerializer(StrictInputMixin, serializers.Serializer):
    file = serializers.FileField()
    alt = serializers.CharField(max_length=200)
    order = serializers.IntegerField(min_value=0, max_value=32767, default=0)


class PhotoWriteSerializer(StrictInputMixin, serializers.ModelSerializer):
    class Meta:
        model = PropertyPhoto
        fields = ["alt", "order", "active"]
