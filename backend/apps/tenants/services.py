from django.shortcuts import get_object_or_404

from apps.audit.services import record_event
from apps.tenants.middleware import ACTIVE_TENANT_KEY
from apps.tenants.queries import authorized_memberships


def select_tenant(request, tenant_id):
    membership = get_object_or_404(authorized_memberships(request.user), tenant_id=tenant_id)
    request.session[ACTIVE_TENANT_KEY] = str(membership.tenant_id)
    request.tenant = membership.tenant
    request.membership = membership
    record_event(
        actor=request.user,
        tenant=request.tenant,
        entity="tenant",
        entity_id=tenant_id,
        action="tenant_selected",
    )
    return membership
