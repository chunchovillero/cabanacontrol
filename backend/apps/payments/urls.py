from django.urls import path

from apps.payments.views import PaymentListView, PaymentReceiptView, PaymentVoidView

urlpatterns = [
    path(
        "reservations/<uuid:reservation_id>/payments/",
        PaymentListView.as_view(),
        name="payment-list",
    ),
    path("payments/<uuid:payment_id>/void/", PaymentVoidView.as_view(), name="payment-void"),
    path(
        "payments/<uuid:payment_id>/receipt/", PaymentReceiptView.as_view(), name="payment-receipt"
    ),
]
