from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.models import User
from apps.tenants.serializers import TenantSerializer


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=256)


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=100)
    token = serializers.CharField(max_length=100)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=256)

    def validate_password(self, value):
        try:
            validate_password(value, self.context.get("user"))
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value


class SessionSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    active_tenant = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "name", "is_platform_admin", "active_tenant"]

    def get_name(self, obj) -> str:
        return obj.get_full_name()

    @extend_schema_field(TenantSerializer(allow_null=True))
    def get_active_tenant(self, obj) -> dict | None:
        membership = getattr(self.context["request"], "membership", None)
        if membership is None:
            return None
        return TenantSerializer(membership.tenant, context={"membership": membership}).data


class CsrfSerializer(serializers.Serializer):
    csrf_token = serializers.CharField(read_only=True)


class MessageSerializer(serializers.Serializer):
    detail = serializers.CharField(read_only=True)
