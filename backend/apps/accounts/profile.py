from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.audit.services import record_event


class SettingsConflict(APIException):
    status_code = 409
    default_detail = "Los datos cambiaron. Recarga antes de guardar nuevamente."
    default_code = "settings_changed"


class StrictInput(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) - set(self.fields):
            raise serializers.ValidationError({"non_field_errors": ["Campos no permitidos."]})
        return super().to_internal_value(data)

    def validate(self, data):
        for key, value in data.items():
            if isinstance(value, str) and any(
                ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value
            ):
                raise serializers.ValidationError({key: "Caracteres no permitidos."})
        return data


class ProfileSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, allow_blank=True)
    email = serializers.EmailField(read_only=True)


class ProfileInput(StrictInput):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, allow_blank=True)
    expected_first_name = serializers.CharField(max_length=150, allow_blank=True)
    expected_last_name = serializers.CharField(max_length=150, allow_blank=True)


class ProfileView(APIView):
    @extend_schema(responses=ProfileSerializer)
    def get(self, request):
        return Response(ProfileSerializer(request.user).data)

    @extend_schema(request=ProfileInput, responses=ProfileSerializer)
    @transaction.atomic
    def patch(self, request):
        serializer = ProfileInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = User.objects.select_for_update().get(pk=request.user.pk)
        if (user.first_name, user.last_name) != (
            data["expected_first_name"],
            data["expected_last_name"],
        ):
            raise SettingsConflict()
        changed = [key for key in ("first_name", "last_name") if getattr(user, key) != data[key]]
        if changed:
            for key in changed:
                setattr(user, key, data[key])
            user.save(update_fields=changed)
            record_event(actor=user, entity="user", entity_id=user.pk, action="profile_updated")
        return Response(ProfileSerializer(user).data)
