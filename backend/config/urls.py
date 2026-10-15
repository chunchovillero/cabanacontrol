from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView

from apps.whatsapp.webhooks import webhook
from config.health import health

urlpatterns = [
    path("health/", health, name="health"),
    path("webhooks/whatsapp/", webhook),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.tenants.urls")),
    path("api/v1/", include("apps.billing.urls")),
    path("api/v1/", include("apps.properties.urls")),
    path("api/v1/", include("apps.guests.urls")),
    path("api/v1/", include("apps.reservations.urls")),
    path("api/v1/", include("apps.payments.urls")),
    path("api/v1/", include("apps.insights.urls")),
    path("api/v1/", include("apps.operations.urls")),
    path("api/v1/", include("apps.assistant.urls")),
    path("api/v1/", include("apps.whatsapp.urls")),
    path("api/v1/", include("apps.inquiries.urls")),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
]
