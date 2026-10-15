from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import record_event
from apps.tenants.models import Membership
from apps.tenants.permissions import HasActiveTenant, IsTenantOwner
from apps.tenants.queries import authorized_memberships
from apps.tenants.serializers import MembershipSerializer, TenantSerializer
from apps.tenants.services import select_tenant


class TenantListView(GenericAPIView):
    serializer_class = TenantSerializer

    @extend_schema(responses=TenantSerializer(many=True))
    def get(self, request):
        if request.user.is_platform_admin:
            record_event(actor=request.user, entity="tenant", action="platform_tenants_listed")
        memberships = self.paginate_queryset(
            authorized_memberships(request.user).order_by("tenant__name", "tenant_id")
        )
        data = [
            TenantSerializer(item.tenant, context={"membership": item}).data for item in memberships
        ]
        return self.get_paginated_response(data)


class TenantDetailView(APIView):
    @extend_schema(responses=TenantSerializer)
    def get(self, request, tenant_id):
        membership = get_object_or_404(authorized_memberships(request.user), tenant_id=tenant_id)
        if request.user.is_platform_admin:
            record_event(
                actor=request.user,
                tenant=membership.tenant,
                entity="tenant",
                entity_id=tenant_id,
                action="platform_tenant_read",
            )
        return Response(
            TenantSerializer(membership.tenant, context={"membership": membership}).data
        )


class TenantSelectView(APIView):
    @extend_schema(request=None, responses=TenantSerializer)
    def post(self, request, tenant_id):
        membership = select_tenant(request, tenant_id)
        return Response(
            TenantSerializer(membership.tenant, context={"membership": membership}).data
        )


class TenantContextView(APIView):
    permission_classes = [IsAuthenticated, HasActiveTenant]

    @extend_schema(responses=TenantSerializer)
    def get(self, request):
        return Response(
            TenantSerializer(request.tenant, context={"membership": request.membership}).data
        )


class MembershipListView(GenericAPIView):
    serializer_class = MembershipSerializer
    permission_classes = [IsAuthenticated, IsTenantOwner]

    @extend_schema(responses=MembershipSerializer(many=True))
    def get(self, request, tenant_id):
        membership = get_object_or_404(authorized_memberships(request.user), tenant_id=tenant_id)
        self.check_object_permissions(request, membership.tenant)
        records = (
            Membership.objects.filter(tenant=request.tenant)
            .select_related("user")
            .order_by("created_at", "id")
        )
        if request.user.is_platform_admin:
            record_event(
                actor=request.user,
                tenant=request.tenant,
                entity="membership",
                action="platform_memberships_read",
            )
        page = self.paginate_queryset(records)
        return self.get_paginated_response(MembershipSerializer(page, many=True).data)
