from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import generics
from rest_framework.exceptions import NotFound
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.properties.models import Property, PropertyPhoto
from apps.properties.permissions import PropertyPermission
from apps.properties.queries import properties_for_tenant
from apps.properties.serializers import (
    PhotoUploadSerializer,
    PhotoWriteSerializer,
    PropertyPhotoSerializer,
    PropertySerializer,
    PropertyWriteSerializer,
)
from apps.properties.services import save_property, update_photo, upload_photo

WRITE_CONTEXT = OpenApiParameter(
    name="X-Tenant-Context",
    location=OpenApiParameter.HEADER,
    type=OpenApiTypes.UUID,
    required=True,
    description="UUID esperado de la empresa activa; no selecciona ni concede acceso.",
)


class PropertyFilter(filters.FilterSet):
    class Meta:
        model = Property
        fields = ["active"]


class PropertyListView(generics.ListCreateAPIView):
    permission_classes = [PropertyPermission]
    serializer_class = PropertySerializer
    filter_backends = [filters.DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = PropertyFilter
    search_fields = ["name", "code"]
    ordering_fields = ["name", "code", "capacity", "base_rate", "created_at"]

    def get_queryset(self):
        return properties_for_tenant(getattr(self.request, "tenant", None))

    @extend_schema(
        request=PropertyWriteSerializer,
        responses={201: PropertySerializer},
        parameters=[WRITE_CONTEXT],
    )
    def post(self, request, *args, **kwargs):
        serializer = PropertyWriteSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        instance = save_property(
            actor=request.user, tenant=request.tenant, data=serializer.validated_data
        )
        return Response(PropertySerializer(instance).data, status=201)


class PropertyDetailView(generics.RetrieveAPIView):
    permission_classes = [PropertyPermission]
    serializer_class = PropertySerializer
    lookup_url_kwarg = "property_id"

    def get_queryset(self):
        return properties_for_tenant(getattr(self.request, "tenant", None))

    @extend_schema(
        request=PropertyWriteSerializer, responses=PropertySerializer, parameters=[WRITE_CONTEXT]
    )
    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = PropertyWriteSerializer(
            instance, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        saved = save_property(
            actor=request.user,
            tenant=request.tenant,
            data=serializer.validated_data,
            instance=instance,
        )
        return Response(PropertySerializer(saved).data)


class PhotoListView(generics.GenericAPIView):
    pagination_class = None
    permission_classes = [PropertyPermission]
    serializer_class = PropertyPhotoSerializer
    parser_classes = [MultiPartParser, FormParser]

    def property(self):
        return get_object_or_404(
            properties_for_tenant(getattr(self.request, "tenant", None)),
            pk=self.kwargs["property_id"],
        )

    @extend_schema(responses=PropertyPhotoSerializer(many=True))
    def get(self, request, property_id):
        return Response(PropertyPhotoSerializer(self.property().active_photos, many=True).data)

    @extend_schema(
        request=PhotoUploadSerializer,
        responses={201: PropertyPhotoSerializer},
        parameters=[WRITE_CONTEXT],
    )
    def post(self, request, property_id):
        property = self.property()
        serializer = PhotoUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        photo = upload_photo(
            actor=request.user,
            tenant=request.tenant,
            property=property,
            upload=data["file"],
            alt=data["alt"],
            order=data["order"],
        )
        return Response(PropertyPhotoSerializer(photo).data, status=201)


class PhotoDetailView(APIView):
    permission_classes = [PropertyPermission]
    http_method_names = ["patch", "options"]

    def photo(self, request, property_id, photo_id):
        property = get_object_or_404(properties_for_tenant(request.tenant), pk=property_id)
        # Consulta explícita para permitir editar/reactivar una foto oculta.
        return get_object_or_404(PropertyPhoto.objects.filter(property=property), pk=photo_id)

    @extend_schema(
        request=PhotoWriteSerializer, responses=PropertyPhotoSerializer, parameters=[WRITE_CONTEXT]
    )
    def patch(self, request, property_id, photo_id):
        photo = self.photo(request, property_id, photo_id)
        serializer = PhotoWriteSerializer(photo, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        saved = update_photo(
            actor=request.user,
            tenant=request.tenant,
            instance=photo,
            data=serializer.validated_data,
        )
        return Response(PropertyPhotoSerializer(saved).data)


class PhotoFileView(PhotoDetailView):
    @extend_schema(
        responses={
            (200, "image/png"): OpenApiTypes.BINARY,
            (200, "image/jpeg"): OpenApiTypes.BINARY,
            (200, "image/webp"): OpenApiTypes.BINARY,
        }
    )
    def get(self, request, property_id, photo_id):
        photo = self.photo(request, property_id, photo_id)
        if not photo.active:
            raise NotFound("Foto no disponible.")
        try:
            file = photo.file.open("rb")
        except FileNotFoundError as exc:
            raise NotFound("Foto no disponible.") from exc
        response = FileResponse(file, content_type=photo.content_type)
        response["X-Content-Type-Options"] = "nosniff"
        return response

    # La ruta de archivo es solo lectura, aunque hereda el acceso a photo().
    http_method_names = ["get", "head", "options"]
