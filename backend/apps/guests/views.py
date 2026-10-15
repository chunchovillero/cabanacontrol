from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django_filters import rest_framework as filters
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.audit.services import record_event
from apps.guests.models import Guest
from apps.guests.permissions import GuestPermission, can_manage_guests
from apps.guests.queries import guests_for_tenant
from apps.guests.serializers import (
    GuestDetailSerializer,
    GuestListSerializer,
    GuestSearchResultSerializer,
    GuestSearchSerializer,
    GuestWriteSerializer,
)
from apps.guests.services import save_guest
from apps.guests.validators import normalize_document

WRITE_CONTEXT = OpenApiParameter(
    name="X-Tenant-Context",
    location=OpenApiParameter.HEADER,
    type=OpenApiTypes.UUID,
    required=True,
    description="UUID esperado de la empresa activa, validado contra sesión.",
)


class GuestFilter(filters.FilterSet):
    class Meta:
        model = Guest
        fields = ["active", "document_type"]


class GuestListView(generics.ListCreateAPIView):
    permission_classes = [GuestPermission]
    serializer_class = GuestListSerializer
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = GuestFilter

    def get_queryset(self):
        return guests_for_tenant(getattr(self.request, "tenant", None)).defer(
            "notes", "phone", "email"
        )

    @extend_schema(
        request=GuestWriteSerializer,
        responses={201: GuestDetailSerializer},
        parameters=[WRITE_CONTEXT],
    )
    def post(self, request, *args, **kwargs):
        serializer = GuestWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = save_guest(
            actor=request.user, tenant=request.tenant, data=serializer.validated_data
        )
        return Response(
            GuestDetailSerializer(instance, context={"request": request}).data, status=201
        )


class GuestDetailView(generics.RetrieveAPIView):
    permission_classes = [GuestPermission]
    serializer_class = GuestDetailSerializer
    lookup_url_kwarg = "guest_id"

    def get_queryset(self):
        queryset = guests_for_tenant(getattr(self.request, "tenant", None))
        if getattr(self.request, "membership", None) and not can_manage_guests(self.request):
            queryset = queryset.defer("notes")
        return queryset

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if can_manage_guests(request):
            record_event(
                actor=request.user,
                tenant=request.tenant,
                entity="guest",
                entity_id=instance.pk,
                action="guest_sensitive_viewed",
            )
        return Response(self.get_serializer(instance).data)

    @extend_schema(
        request=GuestWriteSerializer, responses=GuestDetailSerializer, parameters=[WRITE_CONTEXT]
    )
    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = GuestWriteSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        saved = save_guest(
            actor=request.user,
            tenant=request.tenant,
            data=serializer.validated_data,
            instance=instance,
        )
        return Response(GuestDetailSerializer(saved, context={"request": request}).data)


class BodyPagePagination(PageNumberPagination):
    def get_page_number(self, request, paginator):
        return self.page_number

    def get_next_link(self):
        # La búsqueda no debe reflejar parámetros personales en un URL.
        return None

    def get_previous_link(self):
        return None

    def get_paginated_response(self, data):
        return Response(
            {
                "count": self.page.paginator.count,
                "page": self.page.number,
                "has_next": self.page.has_next(),
                "has_previous": self.page.has_previous(),
                "results": data,
            }
        )

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "required": ["count", "page", "has_next", "has_previous", "results"],
            "properties": {
                "count": {"type": "integer"},
                "page": {"type": "integer"},
                "has_next": {"type": "boolean"},
                "has_previous": {"type": "boolean"},
                "results": schema,
            },
        }


class GuestSearchView(generics.GenericAPIView):
    permission_classes = [GuestPermission]
    serializer_class = GuestListSerializer
    pagination_class = BodyPagePagination
    read_only_search = True

    @extend_schema(
        request=GuestSearchSerializer,
        responses=GuestSearchResultSerializer,
        parameters=[WRITE_CONTEXT],
    )
    def post(self, request):
        serializer = GuestSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        self.paginator.page_number = data["page"]
        queryset = guests_for_tenant(request.tenant).defer("notes", "phone", "email")
        if "active" in data:
            queryset = queryset.filter(active=data["active"])
        query = data["query"].strip()
        if query:
            condition = Q()
            for part in query.split():
                condition &= Q(first_name__icontains=part) | Q(last_name__icontains=part)
            # Documentos exactos: no enumerar números parciales o contactos.
            documents = []
            for kind in Guest.DocumentType.values:
                try:
                    documents.append(normalize_document(kind, query))
                except DjangoValidationError:
                    pass
            condition |= Q(document_number__in=documents)
            queryset = queryset.filter(condition)
        if any(key in request.query_params for key in ("query", "search", "document_number")):
            raise ValidationError(
                "Envía la búsqueda en el cuerpo JSON para proteger los datos personales."
            )
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)
