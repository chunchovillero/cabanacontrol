from django.http import FileResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import generics
from rest_framework.exceptions import NotFound
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import record_event
from apps.payments.models import Payment
from apps.payments.serializers import (
    PaymentSerializer,
    PaymentVoidSerializer,
    PaymentWriteSerializer,
    ReceiptUploadSerializer,
)
from apps.payments.services import attach_receipt, record_payment, void_payment
from apps.reservations.models import Reservation
from apps.reservations.permissions import ReservationPermission
from apps.reservations.views import WRITE_CONTEXT


class PaymentListView(generics.ListCreateAPIView):
    permission_classes = [ReservationPermission]
    serializer_class = PaymentSerializer

    def get_queryset(self):
        reservation = get_object_or_404(
            Reservation,
            tenant=getattr(self.request, "tenant", None),
            pk=self.kwargs["reservation_id"],
        )
        return Payment.objects.filter(tenant=self.request.tenant, reservation=reservation)

    @extend_schema(
        request=PaymentWriteSerializer,
        responses={201: PaymentSerializer, 200: PaymentSerializer},
        parameters=[WRITE_CONTEXT],
    )
    def post(self, request, reservation_id):
        serializer = PaymentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment, created = record_payment(
            actor=request.user,
            tenant=request.tenant,
            reservation_id=reservation_id,
            data=serializer.validated_data,
        )
        return Response(PaymentSerializer(payment).data, status=201 if created else 200)


class PaymentVoidView(APIView):
    permission_classes = [ReservationPermission]

    @extend_schema(
        request=PaymentVoidSerializer, responses=PaymentSerializer, parameters=[WRITE_CONTEXT]
    )
    def post(self, request, payment_id):
        serializer = PaymentVoidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = void_payment(
            actor=request.user,
            tenant=request.tenant,
            payment_id=payment_id,
            **serializer.validated_data,
        )
        return Response(PaymentSerializer(payment).data)


class PaymentReceiptView(APIView):
    permission_classes = [ReservationPermission]
    parser_classes = [MultiPartParser]

    @extend_schema(
        responses={
            (200, "image/png"): OpenApiTypes.BINARY,
            (200, "image/jpeg"): OpenApiTypes.BINARY,
            (200, "image/webp"): OpenApiTypes.BINARY,
        }
    )
    def get(self, request, payment_id):
        payment = get_object_or_404(Payment, tenant=request.tenant, pk=payment_id)
        if not payment.receipt_file:
            raise NotFound("Comprobante no disponible.")
        try:
            file = payment.receipt_file.open("rb")
        except FileNotFoundError as exc:
            raise NotFound("Comprobante no disponible.") from exc
        record_event(
            actor=request.user,
            tenant=request.tenant,
            entity="payment",
            entity_id=payment.pk,
            action="payment_receipt_viewed",
        )
        response = FileResponse(
            file,
            as_attachment=True,
            filename=f"comprobante-{payment.pk}.{payment.receipt_file.name.rsplit('.', 1)[-1]}",
            content_type=payment.receipt_content_type,
        )
        response["X-Content-Type-Options"] = "nosniff"
        return response

    @extend_schema(
        request=ReceiptUploadSerializer, responses=PaymentSerializer, parameters=[WRITE_CONTEXT]
    )
    def post(self, request, payment_id):
        serializer = ReceiptUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = attach_receipt(
            actor=request.user,
            tenant=request.tenant,
            payment_id=payment_id,
            upload=serializer.validated_data["file"],
        )
        return Response(PaymentSerializer(payment).data)
