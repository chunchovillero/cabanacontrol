from django.urls import path

from apps.reservations.views import (
    AvailabilityView,
    BlockDetailView,
    BlockListView,
    ReservationCancelView,
    ReservationConfirmView,
    ReservationDetailView,
    ReservationListView,
    ReservationTransitionView,
)

urlpatterns = [
    path("reservations/", ReservationListView.as_view(), name="reservation-list"),
    path(
        "reservations/<uuid:reservation_id>/",
        ReservationDetailView.as_view(),
        name="reservation-detail",
    ),
    path(
        "reservations/<uuid:reservation_id>/confirm/",
        ReservationConfirmView.as_view(),
        name="reservation-confirm",
    ),
    path(
        "reservations/<uuid:reservation_id>/cancel/",
        ReservationCancelView.as_view(),
        name="reservation-cancel",
    ),
    path(
        "reservations/<uuid:reservation_id>/status/",
        ReservationTransitionView.as_view(),
        name="reservation-status",
    ),
    path("availability/", AvailabilityView.as_view(), name="availability"),
    path("availability-blocks/", BlockListView.as_view(), name="block-list"),
    path("availability-blocks/<uuid:block_id>/", BlockDetailView.as_view(), name="block-detail"),
]
