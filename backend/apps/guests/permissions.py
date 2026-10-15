from rest_framework.permissions import SAFE_METHODS

from apps.tenants.models import Membership
from apps.tenants.permissions import HasConsistentTenant


def can_manage_guests(request):
    return request.membership.role in (Membership.Role.OWNER, Membership.Role.MANAGER)


class GuestPermission(HasConsistentTenant):
    message = "Solo el propietario o administrador pueden modificar huéspedes."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in SAFE_METHODS or getattr(view, "read_only_search", False):
            return True
        return can_manage_guests(request)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view) and obj.tenant_id == request.tenant.pk
