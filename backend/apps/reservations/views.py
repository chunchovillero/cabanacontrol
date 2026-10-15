from django.db.models import Q
from django_filters import rest_framework as filters
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.payments.queries import CHARGEABLE_STATES
from apps.reservations.intervals import validate_interval
from apps.reservations.models import AvailabilityBlock, Reservation
from apps.reservations.permissions import BlockPermission, ReservationPermission
from apps.reservations.queries import (
    availability_for_tenant,
    reservations_for_tenant,
)
from apps.reservations.serializers import (
    AvailabilityItemSerializer,
    AvailabilityQuerySerializer,
    BlockSerializer,
    BlockWriteSerializer,
    CancelSerializer,
    ConfirmSerializer,
    ReservationCreateSerializer,
    ReservationDetailSerializer,
    ReservationSerializer,
    ReservationWriteSerializer,
    TransitionSerializer,
)
from apps.reservations.services import (
    local_today,
    save_block,
    save_reservation,
    transition_reservation,
)

WRITE_CONTEXT = OpenApiParameter(
    "X-Tenant-Context", OpenApiTypes.UUID, OpenApiParameter.HEADER, required=True
)


class ReservationFilter(filters.FilterSet):
    debt = filters.BooleanFilter(method="filter_debt")

    def filter_debt(self, queryset, name, value):
        debt = Q(status__in=CHARGEABLE_STATES, balance__gt=0)
        return queryset.filter(debt) if value else queryset.exclude(debt)

    from_date = filters.DateFilter(field_name="check_out", lookup_expr="gt")
    to_date = filters.DateFilter(field_name="check_in", lookup_expr="lt")

    class Meta:
        model = Reservation
        fields = ["property_id", "status", "from_date", "to_date"]


class ReservationListView(generics.ListCreateAPIView):
    permission_classes = [ReservationPermission]
    serializer_class = ReservationSerializer
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = ReservationFilter

    def get_queryset(self):
        return reservations_for_tenant(getattr(self.request, "tenant", None)).defer(
            "notes",
            "cancel_reason",
            "primary_guest__notes",
            "primary_guest__phone",
            "primary_guest__email",
        )

    @extend_schema(
        request=ReservationCreateSerializer,
        responses={201: ReservationDetailSerializer},
        parameters=[WRITE_CONTEXT],
    )
    def post(self, request):
        serializer = ReservationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = save_reservation(
            actor=request.user, tenant=request.tenant, data=serializer.validated_data
        )
        return Response(ReservationDetailSerializer(instance).data, status=201)


class ReservationDetailView(generics.RetrieveAPIView):
    permission_classes = [ReservationPermission]
    serializer_class = ReservationDetailSerializer
    lookup_url_kwarg = "reservation_id"

    def get_queryset(self):
        return reservations_for_tenant(getattr(self.request, "tenant", None)).defer(
            "primary_guest__notes", "primary_guest__phone", "primary_guest__email"
        )

    @extend_schema(
        request=ReservationWriteSerializer,
        responses=ReservationDetailSerializer,
        parameters=[WRITE_CONTEXT],
    )
    def patch(self, request, *args, **kwargs):
        serializer = ReservationWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = save_reservation(
            actor=request.user,
            tenant=request.tenant,
            data=serializer.validated_data,
            instance=self.get_object(),
        )
        return Response(ReservationDetailSerializer(instance).data)


class ReservationTransitionView(ReservationDetailView):
    http_method_names = ["post", "options"]

    @extend_schema(
        request=TransitionSerializer,
        responses=ReservationDetailSerializer,
        parameters=[WRITE_CONTEXT],
    )
    def post(self, request, *args, **kwargs):
        serializer = TransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = transition_reservation(
            actor=request.user,
            tenant=request.tenant,
            instance=self.get_object(),
            **serializer.validated_data,
        )
        return Response(ReservationDetailSerializer(instance).data)


class ReservationConfirmView(ReservationTransitionView):
    @extend_schema(
        request=ConfirmSerializer, responses=ReservationDetailSerializer, parameters=[WRITE_CONTEXT]
    )
    def post(self, request, *args, **kwargs):
        serializer = ConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = transition_reservation(
            actor=request.user,
            tenant=request.tenant,
            instance=self.get_object(),
            status="confirmed",
        )
        return Response(ReservationDetailSerializer(instance).data)


class ReservationCancelView(ReservationTransitionView):
    @extend_schema(
        request=CancelSerializer, responses=ReservationDetailSerializer, parameters=[WRITE_CONTEXT]
    )
    def post(self, request, *args, **kwargs):
        serializer = CancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = transition_reservation(
            actor=request.user,
            tenant=request.tenant,
            instance=self.get_object(),
            status="cancelled",
            **serializer.validated_data,
        )
        return Response(ReservationDetailSerializer(instance).data)


class BlockListView(generics.ListCreateAPIView):
    permission_classes = [BlockPermission]
    serializer_class = BlockSerializer
    filter_backends = [filters.DjangoFilterBackend]
    filterset_fields = ["property_id", "active", "reason"]

    def get_queryset(self):
        return AvailabilityBlock.objects.filter(
            tenant=getattr(self.request, "tenant", None)
        ).select_related("property")

    @extend_schema(
        request=BlockWriteSerializer, responses={201: BlockSerializer}, parameters=[WRITE_CONTEXT]
    )
    def post(self, request):
        serializer = BlockWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = save_block(
            actor=request.user, tenant=request.tenant, data=serializer.validated_data
        )
        return Response(BlockSerializer(instance).data, status=201)


class BlockDetailView(generics.RetrieveAPIView):
    permission_classes = [BlockPermission]
    serializer_class = BlockSerializer
    lookup_url_kwarg = "block_id"

    def get_queryset(self):
        return AvailabilityBlock.objects.filter(
            tenant=getattr(self.request, "tenant", None)
        ).select_related("property")

    @extend_schema(
        request=BlockWriteSerializer, responses=BlockSerializer, parameters=[WRITE_CONTEXT]
    )
    def patch(self, request, *args, **kwargs):
        serializer = BlockWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = save_block(
            actor=request.user,
            tenant=request.tenant,
            data=serializer.validated_data,
            instance=self.get_object(),
        )
        return Response(BlockSerializer(instance).data)


class AvailabilityView(generics.ListAPIView):
    permission_classes = [ReservationPermission]
    serializer_class = AvailabilityItemSerializer

    @extend_schema(parameters=[AvailabilityQuerySerializer])
    def get(self, request, *args, **kwargs):
        serializer = AvailabilityQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        start, end = data["from"], data["to"]
        validate_interval(start, end)
        if start < local_today(request.tenant):
            raise ValidationError({"from": "Consulta disponibilidad desde hoy."})
        queryset = availability_for_tenant(request.tenant, start, end, data.get("guests", 1))
        if "property_id" in data:
            from django.shortcuts import get_object_or_404

            get_object_or_404(queryset, pk=data["property_id"])
            queryset = queryset.filter(pk=data["property_id"])
        page = self.paginate_queryset(queryset)
        items = [
            {
                "property_id": prop.pk,
                "property_name": prop.name,
                "capacity": prop.capacity,
                "available": prop.available,
            }
            for prop in page
        ]
        return self.get_paginated_response(self.get_serializer(items, many=True).data)
