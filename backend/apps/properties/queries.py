from django.db.models import Prefetch

from apps.properties.models import Property, PropertyPhoto


def properties_for_tenant(tenant):
    if tenant is None:
        return Property.objects.none()
    return (
        Property.objects.filter(tenant=tenant)
        .select_related("tenant")
        .prefetch_related(
            Prefetch(
                "photos",
                queryset=PropertyPhoto.objects.filter(active=True),
                to_attr="active_photos",
            )
        )
    )
