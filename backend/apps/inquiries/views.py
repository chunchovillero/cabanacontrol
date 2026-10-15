from datetime import datetime, time
from zoneinfo import ZoneInfo

from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.assistant.dispatcher import dispatch
from apps.assistant.privacy import mask_text
from apps.assistant.providers import get_provider
from apps.assistant.services import record_consumption, reserve
from apps.inquiries.models import Inquiry
from apps.inquiries.serializers import (
    AnalyzeSerializer,
    ConvertSerializer,
    InquirySerializer,
    InquiryUpdateSerializer,
    InquiryWriteSerializer,
)
from apps.inquiries.services import convert, editable, save_inquiry
from apps.insights.serializers import PeriodQuerySerializer
from apps.reservations.serializers import ReservationDetailSerializer
from apps.reservations.services import local_today, require_operator
from apps.reservations.views import WRITE_CONTEXT
from apps.tenants.models import Membership
from apps.tenants.permissions import HasConsistentTenant
from apps.tenants.serializers import MembershipSerializer


class InquiryListView(generics.ListAPIView):
    permission_classes = [HasConsistentTenant]
    serializer_class = InquirySerializer

    def get_queryset(self):
        query = Inquiry.objects.filter(tenant=self.request.tenant)
        archived = self.request.query_params.get("archived", "false")
        if archived not in ["true", "false"]:
            raise ValidationError("Archivo debe ser true o false.")
        condition = Q(expires_at__lte=timezone.now()) | Q(archived_at__isnull=False)
        query = query.filter(condition) if archived == "true" else query.exclude(condition)
        status = self.request.query_params.get("status")
        if status:
            if status not in Inquiry.Status.values:
                raise ValidationError("Estado inválido.")
            query = query.filter(status=status)
        return query

    @extend_schema(parameters=[OpenApiParameter("archived", bool), OpenApiParameter("status", str)])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        request=InquiryWriteSerializer,
        responses={201: InquirySerializer},
        parameters=[WRITE_CONTEXT],
    )
    def post(self, request):
        serializer = InquiryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inquiry = save_inquiry(
            actor=request.user, tenant=request.tenant, data=serializer.validated_data
        )
        return Response(InquirySerializer(inquiry).data, status=201)


class InquiryDetailView(generics.RetrieveAPIView):
    permission_classes = [HasConsistentTenant]
    serializer_class = InquirySerializer
    lookup_url_kwarg = "inquiry_id"

    def get_queryset(self):
        return Inquiry.objects.filter(tenant=self.request.tenant)

    @extend_schema(
        request=InquiryUpdateSerializer, responses=InquirySerializer, parameters=[WRITE_CONTEXT]
    )
    def patch(self, request, inquiry_id):
        serializer = InquiryUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if "revision" not in serializer.validated_data:
            raise ValidationError("Indica la revisión actual.")
        inquiry = save_inquiry(
            actor=request.user,
            tenant=request.tenant,
            inquiry_id=inquiry_id,
            data=serializer.validated_data,
        )
        return Response(InquirySerializer(inquiry).data)


class InquiryAnalyzeView(APIView):
    permission_classes = [HasConsistentTenant]

    @extend_schema(
        request=AnalyzeSerializer, responses=InquirySerializer, parameters=[WRITE_CONTEXT]
    )
    def post(self, request, inquiry_id):
        serializer = AnalyzeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if not data["reviewed"]:
            raise ValidationError("Revisa el texto antes de enviarlo.")
        inquiry = get_object_or_404(Inquiry, tenant=request.tenant, pk=inquiry_id)
        editable(inquiry, data["revision"])
        text = mask_text(data["text"])
        usage_id = reserve(request.user, request.tenant, text)
        interpretation = get_provider().interpret(
            text, local_today(request.tenant), request.tenant.timezone, {}
        )
        record_consumption(usage_id, interpretation)
        result = dispatch(
            interpretation.calls, actor=request.user, tenant=request.tenant, text=text, previous={}
        )
        # Only validated filters are retained, never guest facts or model free text.
        from apps.assistant.dispatcher import read_context

        extraction = read_context(result["context"], request.user, request.tenant)
        with transaction.atomic():
            require_operator(request.user, request.tenant)
            inquiry = get_object_or_404(
                Inquiry.objects.select_for_update(), tenant=request.tenant, pk=inquiry_id
            )
            editable(inquiry, data["revision"])
            inquiry.review_text = text
            inquiry.extraction = extraction
            for card in result["results"]:
                if card["tool"] == "prepare_whatsapp_message":
                    inquiry.response_text = card["data"].get("message", "")
            inquiry.revision += 1
            inquiry.save()
        return Response(InquirySerializer(inquiry).data)


class InquiryConvertView(APIView):
    permission_classes = [HasConsistentTenant]

    @extend_schema(
        request=ConvertSerializer, responses=ReservationDetailSerializer, parameters=[WRITE_CONTEXT]
    )
    def post(self, request, inquiry_id):
        serializer = ConvertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reservation = convert(
            actor=request.user,
            tenant=request.tenant,
            inquiry_id=inquiry_id,
            data=serializer.validated_data,
        )
        return Response(ReservationDetailSerializer(reservation).data)


class InquiryStatsView(APIView):
    permission_classes = [HasConsistentTenant]

    @extend_schema(
        parameters=[PeriodQuerySerializer],
        responses={
            200: {
                "type": "object",
                "properties": {"counts": {"type": "array", "items": {"type": "object"}}},
            }
        },
    )
    def get(self, request):
        query = Inquiry.objects.filter(tenant=request.tenant)
        if request.query_params:
            serializer = PeriodQuerySerializer(data=request.query_params)
            serializer.is_valid(raise_exception=True)
            if "property_id" in serializer.validated_data:
                raise ValidationError("Las consultas se agrupan por creación, no por cabaña.")
            zone = ZoneInfo(request.tenant.timezone)
            query = query.filter(
                created_at__gte=datetime.combine(serializer.validated_data["from"], time.min, zone),
                created_at__lt=datetime.combine(serializer.validated_data["to"], time.min, zone),
            )
        counts = (
            query.values("channel", "status")
            .annotate(count=Count("pk"))
            .order_by("channel", "status")
        )
        return Response({"counts": list(counts)})


class InquiryAssigneesView(generics.ListAPIView):
    permission_classes = [HasConsistentTenant]
    serializer_class = MembershipSerializer

    def get_queryset(self):
        return (
            Membership.objects.filter(tenant=self.request.tenant, active=True, user__is_active=True)
            .select_related("user")
            .order_by("pk")
        )
