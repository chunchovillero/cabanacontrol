from django.urls import path

from apps.properties.views import (
    PhotoDetailView,
    PhotoFileView,
    PhotoListView,
    PropertyDetailView,
    PropertyListView,
)

urlpatterns = [
    path("properties/", PropertyListView.as_view(), name="property-list"),
    path("properties/<uuid:property_id>/", PropertyDetailView.as_view(), name="property-detail"),
    path("properties/<uuid:property_id>/photos/", PhotoListView.as_view(), name="property-photos"),
    path(
        "properties/<uuid:property_id>/photos/<uuid:photo_id>/",
        PhotoDetailView.as_view(),
        name="property-photo-detail",
    ),
    path(
        "properties/<uuid:property_id>/photos/<uuid:photo_id>/file/",
        PhotoFileView.as_view(),
        name="property-photo-file",
    ),
]
