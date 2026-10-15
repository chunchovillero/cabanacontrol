from rest_framework.permissions import SAFE_METHODS

from apps.tenants.permissions import HasConsistentTenant


class ReservationPermission(HasConsistentTenant):
    """Todos los miembros activos pueden operar reservas, según decisión del propietario."""


class BlockPermission(HasConsistentTenant):
    message = "Solo propietarios y administradores pueden gestionar bloqueos."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and (
            request.method in SAFE_METHODS or request.membership.role in ["owner", "manager"]
        )
