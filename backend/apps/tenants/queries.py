from apps.tenants.models import Membership


def authorized_memberships(user):
    if not user.is_authenticated or not user.is_active:
        return Membership.objects.none()
    return Membership.objects.filter(user=user, active=True, tenant__active=True).select_related(
        "tenant"
    )
