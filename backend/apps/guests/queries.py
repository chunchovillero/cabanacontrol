from apps.guests.models import Guest


def guests_for_tenant(tenant):
    if tenant is None:
        return Guest.objects.none()
    return Guest.objects.filter(tenant=tenant)
