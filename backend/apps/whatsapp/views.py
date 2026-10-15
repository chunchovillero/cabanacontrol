from django.db import connection as database_connection
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.reservations.services import require_operator
from apps.reservations.views import WRITE_CONTEXT
from apps.tenants.permissions import HasConsistentTenant
from apps.whatsapp.models import Connection, Message, OutboxJob, Template
from apps.whatsapp.providers import ready, simulated
from apps.whatsapp.serializers import (
    CapabilitiesSerializer,
    ConnectionSerializer,
    ConnectionWriteSerializer,
    ConsentSerializer,
    ConversationSerializer,
    JobSerializer,
    MessagePageSerializer,
    MessageSerializer,
    PreparedSerializer,
    PrepareSerializer,
    SendSerializer,
    TemplateSerializer,
    TemplateWriteSerializer,
)
from apps.whatsapp.services import configure, consent, conversation_scope, enqueue


class CapabilitiesView(APIView):
    permission_classes = [HasConsistentTenant]

    @extend_schema(responses=CapabilitiesSerializer)
    def get(self, request):
        connection = Connection.objects.filter(tenant=request.tenant).first()
        return Response(
            {
                "ready": ready(),
                "enabled": bool(connection and connection.enabled),
                "simulated": simulated(),
            }
        )


class ConnectionView(APIView):
    permission_classes = [HasConsistentTenant]

    @extend_schema(responses=ConnectionSerializer)
    def get(self, request):
        require_operator(request.user, request.tenant, blocks=True)
        connection = Connection.objects.filter(tenant=request.tenant).first()
        return Response(ConnectionSerializer(connection).data if connection else None)

    @extend_schema(
        request=ConnectionWriteSerializer,
        responses=ConnectionSerializer,
        parameters=[WRITE_CONTEXT],
    )
    def patch(self, request):
        serializer = ConnectionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            ConnectionSerializer(
                configure(actor=request.user, tenant=request.tenant, data=serializer.validated_data)
            ).data
        )


class ConversationListView(generics.ListAPIView):
    permission_classes = [HasConsistentTenant]
    serializer_class = ConversationSerializer

    def get_queryset(self):
        query = conversation_scope(self.request.tenant)
        archived = self.request.query_params.get("archived", "false")
        if archived not in ["true", "false"]:
            raise ValidationError("Archivo debe ser true o false.")
        return (
            query.filter(expires_at__lte=timezone.now())
            if archived == "true"
            else query.filter(expires_at__gt=timezone.now())
        )

    @extend_schema(parameters=[OpenApiParameter("archived", bool)])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ConversationDetailView(generics.RetrieveAPIView):
    permission_classes = [HasConsistentTenant]
    serializer_class = ConversationSerializer
    lookup_url_kwarg = "conversation_id"

    def get_queryset(self):
        return conversation_scope(self.request.tenant)


class MessageListView(generics.ListAPIView):
    permission_classes = [HasConsistentTenant]
    serializer_class = MessageSerializer

    @extend_schema(responses=MessagePageSerializer, parameters=[OpenApiParameter("archived", bool)])
    def get(self, request, *args, **kwargs):
        with transaction.atomic():
            with database_connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            require_operator(request.user, request.tenant)
            response = super().get(request, *args, **kwargs)
            conversation = get_object_or_404(
                conversation_scope(request.tenant), pk=kwargs["conversation_id"]
            )
            response.data["conversation"] = ConversationSerializer(conversation).data
            return response

    def get_queryset(self):
        conversation = get_object_or_404(
            conversation_scope(self.request.tenant), pk=self.kwargs["conversation_id"]
        )
        archived = self.request.query_params.get("archived", "false")
        if archived not in ["true", "false"]:
            raise ValidationError("Archivo debe ser true o false.")
        query = Message.objects.filter(conversation=conversation).order_by("-occurred_at", "-pk")
        return (
            query.filter(expires_at__lte=timezone.now())
            if archived == "true"
            else query.filter(expires_at__gt=timezone.now())
        )


class SendView(APIView):
    permission_classes = [HasConsistentTenant]

    @extend_schema(
        request=SendSerializer, responses={202: JobSerializer}, parameters=[WRITE_CONTEXT]
    )
    def post(self, request):
        serializer = SendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            JobSerializer(
                enqueue(actor=request.user, tenant=request.tenant, data=serializer.validated_data)
            ).data,
            status=202,
        )


class ConsentView(APIView):
    permission_classes = [HasConsistentTenant]

    @extend_schema(
        request=ConsentSerializer, responses=ConversationSerializer, parameters=[WRITE_CONTEXT]
    )
    def post(self, request):
        serializer = ConsentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            ConversationSerializer(
                consent(actor=request.user, tenant=request.tenant, **serializer.validated_data)
            ).data
        )


class PrepareView(APIView):
    permission_classes = [HasConsistentTenant]

    @extend_schema(
        request=PrepareSerializer, responses=PreparedSerializer, parameters=[WRITE_CONTEXT]
    )
    def post(self, request):
        serializer = PrepareSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation = get_object_or_404(
            conversation_scope(request.tenant), pk=serializer.validated_data["conversation_id"]
        )
        text = (
            "Hola, gracias por tu consulta. Indícanos las fechas de entrada y salida con año, "
            "y la cantidad de adultos y niños. Verificaremos disponibilidad; precio por confirmar."
        )
        return Response({"text": text, "revision": conversation.revision})


class JobListView(generics.ListAPIView):
    permission_classes = [HasConsistentTenant]
    serializer_class = JobSerializer

    def get_queryset(self):
        return OutboxJob.objects.filter(connection__tenant=self.request.tenant).order_by(
            "-created_at", "-pk"
        )


class TemplateListView(generics.ListAPIView):
    permission_classes = [HasConsistentTenant]
    serializer_class = TemplateSerializer

    def get_queryset(self):
        return Template.objects.filter(connection__tenant=self.request.tenant).order_by(
            "name", "pk"
        )

    @extend_schema(
        request=TemplateWriteSerializer, responses=TemplateSerializer, parameters=[WRITE_CONTEXT]
    )
    def post(self, request):
        require_operator(request.user, request.tenant, blocks=True)
        serializer = TemplateWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if not data.pop("reviewed") or "{{" in data["body"]:
            raise ValidationError(
                "Revisa una plantilla estática, sin parámetros, aprobada en Meta."
            )
        connection = get_object_or_404(Connection, tenant=request.tenant)
        template, _ = Template.objects.update_or_create(
            connection=connection,
            name=data.pop("name"),
            language=data.pop("language"),
            defaults={**data, "verified_at": timezone.now() if data["approved"] else None},
        )
        return Response(TemplateSerializer(template).data)
