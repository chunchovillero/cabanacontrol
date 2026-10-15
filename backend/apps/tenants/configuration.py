from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.profile import SettingsConflict, StrictInput
from apps.audit.services import record_event
from apps.tenants.member_services import owner_lock
from apps.tenants.models import Tenant
from apps.tenants.permissions import HasConsistentTenant, IsTenantOwner


class CompanySettingsSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=150)
    legal_name = serializers.CharField(max_length=200, allow_blank=True)
    contact_email = serializers.EmailField(max_length=254, allow_blank=True)
    contact_phone = serializers.CharField(max_length=30, allow_blank=True)
    timezone = serializers.CharField(read_only=True)
    currency = serializers.CharField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class CompanySettingsInput(StrictInput):
    name = serializers.CharField(max_length=150)
    legal_name = serializers.CharField(max_length=200, allow_blank=True)
    contact_email = serializers.EmailField(max_length=254, allow_blank=True)
    contact_phone = serializers.RegexField(r"^[+0-9() .-]*$", max_length=30, allow_blank=True)
    expected_updated_at = serializers.DateTimeField()


class CompanySettingsView(APIView):
    permission_classes = [HasConsistentTenant, IsTenantOwner]

    @extend_schema(responses=CompanySettingsSerializer)
    def get(self, request):
        return Response(CompanySettingsSerializer(request.tenant).data)

    @extend_schema(request=CompanySettingsInput, responses=CompanySettingsSerializer)
    @transaction.atomic
    def patch(self, request):
        serializer = CompanySettingsInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        owner_lock(request.user, request.tenant)
        tenant = Tenant.objects.get(pk=request.tenant.pk)
        if tenant.updated_at != data.pop("expected_updated_at"):
            raise SettingsConflict()
        changed = [key for key, value in data.items() if getattr(tenant, key) != value]
        if changed:
            for key in changed:
                setattr(tenant, key, data[key])
            tenant.save(update_fields=[*changed, "updated_at"])
            record_event(
                actor=request.user,
                tenant=tenant,
                entity="tenant",
                entity_id=tenant.pk,
                action="company_settings_updated",
                after={"fields": changed},
            )
        return Response(CompanySettingsSerializer(tenant).data)
