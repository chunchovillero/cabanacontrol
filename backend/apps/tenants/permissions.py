from rest_framework.exceptions import APIException
from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.tenants.models import Membership


class HasActiveTenant(BasePermission):
    message = "Selecciona una empresa autorizada para continuar."

    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.membership and request.tenant)


class TenantContextConflict(APIException):
    status_code = 409
    default_code = "tenant_context_changed"
    default_detail = "La empresa activa cambió. Recarga antes de continuar."


class HasConsistentTenant(HasActiveTenant):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        expected = request.headers.get("X-Tenant-Context")
        if expected and expected != str(request.tenant.pk):
            raise TenantContextConflict()
        if request.method not in SAFE_METHODS and not expected:
            raise TenantContextConflict()
        return True


class IsTenantOwner(HasActiveTenant):
    message = "Solo el propietario puede consultar las membresías de esta empresa."

    def has_permission(self, request, view):
        return (
            super().has_permission(request, view)
            and request.membership.role == Membership.Role.OWNER
        )

    def has_object_permission(self, request, view, obj):
        tenant_id = getattr(obj, "tenant_id", obj.pk)
        return self.has_permission(request, view) and str(tenant_id) == str(request.tenant.pk)
