from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.services import CATALOG, snapshot
from apps.tenants.permissions import HasConsistentTenant, IsTenantOwner


class PlanSerializer(serializers.Serializer):
    code = serializers.CharField()
    version = serializers.IntegerField()
    name = serializers.CharField()
    property_limit = serializers.IntegerField()
    member_limit = serializers.IntegerField()


class UsageSerializer(serializers.Serializer):
    properties = serializers.IntegerField()
    members = serializers.IntegerField()


class SubscriptionSerializer(serializers.Serializer):
    status = serializers.CharField()
    enforced = serializers.BooleanField()
    plan = PlanSerializer(allow_null=True)
    usage = UsageSerializer()
    trial_ends_at = serializers.DateTimeField(allow_null=True)
    over_capacity = serializers.BooleanField()


class PlanUsageSerializer(serializers.Serializer):
    subscription = SubscriptionSerializer()
    catalog = PlanSerializer(many=True)


class PlanUsageView(APIView):
    permission_classes = [HasConsistentTenant, IsTenantOwner]

    @extend_schema(responses=PlanUsageSerializer)
    def get(self, request):
        catalog = [
            {
                "code": code,
                "version": 1,
                "name": name,
                "property_limit": properties,
                "member_limit": members,
            }
            for code, (name, properties, members) in CATALOG.items()
            if code != "trial"
        ]
        return Response(
            PlanUsageSerializer({"subscription": snapshot(request.tenant), "catalog": catalog}).data
        )
