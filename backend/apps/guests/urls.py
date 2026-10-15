from django.urls import path

from apps.guests.views import GuestDetailView, GuestListView, GuestSearchView

urlpatterns = [
    path("guests/", GuestListView.as_view(), name="guest-list"),
    path("guests/search/", GuestSearchView.as_view(), name="guest-search"),
    path("guests/<uuid:guest_id>/", GuestDetailView.as_view(), name="guest-detail"),
]
