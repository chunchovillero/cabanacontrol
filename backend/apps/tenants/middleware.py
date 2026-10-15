from uuid import UUID

from apps.audit.services import record_event
from apps.tenants.queries import authorized_memberships

ACTIVE_TENANT_KEY = "active_tenant_id"


class TenantContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = None
        request.membership = None
        if request.path == "/health/":
            return self.get_response(request)
        tenant_id = request.session.get(ACTIVE_TENANT_KEY)
        if tenant_id:
            try:
                tenant_id = UUID(str(tenant_id))
            except ValueError:
                tenant_id = None
            membership = authorized_memberships(request.user).filter(tenant_id=tenant_id).first()
            if membership:
                request.tenant = membership.tenant
                request.membership = membership
            else:
                request.session.pop(ACTIVE_TENANT_KEY, None)
        response = self.get_response(request)
        if request.path.startswith("/api/v1/"):
            response["Cache-Control"] = "no-store"
        if request.membership and request.user.is_authenticated and request.user.is_platform_admin:
            record_event(
                actor=request.user,
                tenant=request.tenant,
                entity="tenant",
                entity_id=request.tenant.pk,
                action="platform_context_access",
            )
        return response
