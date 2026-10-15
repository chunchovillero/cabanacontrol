from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.throttling import consume_limit, limit_auth_request
from apps.tenants.member_serializers import (
    InvitationAcceptedSerializer,
    InvitationAcceptInput,
    InvitationCreatedSerializer,
    InvitationCreateInput,
    InvitationPreviewSerializer,
    InvitationSerializer,
    InvitationTokenInput,
    MembershipChangeInput,
    TeamMemberSerializer,
)
from apps.tenants.member_services import (
    accept_invitation,
    change_membership,
    create_invitation,
    lookup_token,
    revoke_invitation,
)
from apps.tenants.models import Invitation, Membership
from apps.tenants.permissions import HasConsistentTenant, IsTenantOwner


class OwnerView(GenericAPIView):
    permission_classes = [HasConsistentTenant, IsTenantOwner]


class TeamMembershipsView(OwnerView):
    serializer_class = TeamMemberSerializer

    def get(self, request):
        records = (
            Membership.objects.filter(tenant=request.tenant)
            .select_related("user")
            .order_by("created_at", "id")
        )
        page = self.paginate_queryset(records)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)


class InvitationsView(OwnerView):
    serializer_class = InvitationSerializer

    def get(self, request):
        records = Invitation.objects.filter(tenant=request.tenant)
        page = self.paginate_queryset(records)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    @extend_schema(request=InvitationCreateInput, responses={201: InvitationCreatedSerializer})
    def post(self, request):
        serializer = InvitationCreateInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        consume_limit("invite:user:hour", str(request.user.pk), 10, window_seconds=3600)
        consume_limit("invite:tenant:day", str(request.tenant.pk), 50, window_seconds=86400)
        invitation, token = create_invitation(
            actor=request.user, tenant=request.tenant, **serializer.validated_data
        )
        return Response(
            {
                "invitation": InvitationSerializer(invitation).data,
                "link": f"{settings.PUBLIC_APP_URL}/invitacion#token={token}",
            },
            status=201,
        )


class InvitationRevokeView(OwnerView):
    @extend_schema(request=None, responses=InvitationSerializer)
    def post(self, request, invitation_id):
        invitation = revoke_invitation(
            actor=request.user, tenant=request.tenant, invitation_id=invitation_id
        )
        return Response(InvitationSerializer(invitation).data)


class MembershipChangeView(OwnerView):
    @extend_schema(request=MembershipChangeInput, responses=TeamMemberSerializer)
    def patch(self, request, membership_id):
        serializer = MembershipChangeInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = change_membership(
            actor=request.user,
            tenant=request.tenant,
            membership_id=membership_id,
            data=serializer.validated_data,
        )
        return Response(TeamMemberSerializer(membership).data)


@method_decorator(csrf_protect, name="dispatch")
class InvitationPreviewView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = InvitationTokenInput

    @extend_schema(responses=InvitationPreviewSerializer)
    def post(self, request):
        limit_auth_request(request, "invitation_preview")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invitation = lookup_token(serializer.validated_data["token"])
        local, domain = invitation.email.rsplit("@", 1)
        return Response(
            {
                "company_name": invitation.tenant.name,
                "role": invitation.role,
                "email_hint": f"{local[:1]}***@{domain}",
                "expires_at": invitation.expires_at,
            }
        )


@method_decorator(csrf_protect, name="dispatch")
class InvitationAcceptView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = InvitationAcceptInput

    @extend_schema(responses=InvitationAcceptedSerializer)
    def post(self, request):
        limit_auth_request(request, "invitation_accept")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        accept_invitation(actor=request.user, data=serializer.validated_data)
        return Response(
            {"detail": "Invitación aceptada. Inicia sesión y selecciona la empresa en Empresas."}
        )
