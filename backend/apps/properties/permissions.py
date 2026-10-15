from rest_framework.permissions import SAFE_METHODS

from apps.tenants.models import Membership
from apps.tenants.permissions import HasConsistentTenant


class PropertyPermission(HasConsistentTenant):
    message = "Solo el propietario o administrador pueden modificar cabañas."

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.method in SAFE_METHODS or request.membership.role in (
            Membership.Role.OWNER,
            Membership.Role.MANAGER,
        )

    def has_object_permission(self, request, view, obj):
        tenant_id = obj.property.tenant_id if hasattr(obj, "property") else obj.tenant_id
        return self.has_permission(request, view) and tenant_id == request.tenant.pk
