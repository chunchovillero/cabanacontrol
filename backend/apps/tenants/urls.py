from django.urls import path

from apps.tenants.configuration import CompanySettingsView
from apps.tenants.member_views import (
    InvitationAcceptView,
    InvitationPreviewView,
    InvitationRevokeView,
    InvitationsView,
    MembershipChangeView,
    TeamMembershipsView,
)
from apps.tenants.views import (
    MembershipListView,
    TenantContextView,
    TenantDetailView,
    TenantListView,
    TenantSelectView,
)

urlpatterns = [
    path("company-settings/", CompanySettingsView.as_view(), name="company-settings"),
    path("team/memberships/", TeamMembershipsView.as_view(), name="team-memberships"),
    path("invitations/preview/", InvitationPreviewView.as_view(), name="invitation-preview"),
    path("invitations/accept/", InvitationAcceptView.as_view(), name="invitation-accept"),
    path("team/invitations/", InvitationsView.as_view(), name="invitation-list"),
    path(
        "team/invitations/<uuid:invitation_id>/revoke/",
        InvitationRevokeView.as_view(),
        name="invitation-revoke",
    ),
    path(
        "team/memberships/<uuid:membership_id>/",
        MembershipChangeView.as_view(),
        name="membership-change",
    ),
    path("tenants/", TenantListView.as_view(), name="tenant-list"),
    path("tenants/<uuid:tenant_id>/", TenantDetailView.as_view(), name="tenant-detail"),
    path("tenants/<uuid:tenant_id>/select/", TenantSelectView.as_view(), name="tenant-select"),
    path(
        "tenants/<uuid:tenant_id>/memberships/",
        MembershipListView.as_view(),
        name="tenant-memberships",
    ),
    path("context/", TenantContextView.as_view(), name="tenant-context"),
]
