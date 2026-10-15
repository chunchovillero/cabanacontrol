import json

from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.assistant.audio import audio_ready, transcribe
from apps.assistant.dispatcher import dispatch, read_context
from apps.assistant.models import TenantAISettings
from apps.assistant.privacy import mask_text
from apps.assistant.providers import get_provider
from apps.assistant.serializers import (
    CapabilitiesSerializer,
    MessageResultSerializer,
    MessageSerializer,
    PrepareMessageSerializer,
    SettingsSerializer,
    TranscriptionResultSerializer,
    TranscriptionSerializer,
)
from apps.assistant.services import configuration, ready, record_consumption, reserve
from apps.reservations.services import local_today
from apps.reservations.views import WRITE_CONTEXT
from apps.tenants.permissions import HasConsistentTenant


class CapabilitiesView(APIView):
    permission_classes = [HasConsistentTenant]

    @extend_schema(responses=CapabilitiesSerializer)
    def get(self, request):
        from apps.assistant.testing import simulated

        config = configuration(request.tenant)
        return Response(
            {
                "ready": ready(),
                "simulated": simulated(),
                "enabled": config.enabled,
                "voice_enabled": bool(config.enabled and config.voice_enabled and audio_ready()),
                "settings": SettingsSerializer(config).data,
            }
        )


class SettingsView(APIView):
    permission_classes = [HasConsistentTenant]

    @extend_schema(responses=SettingsSerializer)
    def get(self, request):
        return Response(SettingsSerializer(configuration(request.tenant)).data)

    @extend_schema(
        request=SettingsSerializer, responses=SettingsSerializer, parameters=[WRITE_CONTEXT]
    )
    def patch(self, request):
        if request.membership.role not in ["owner", "manager"]:
            raise PermissionDenied("Solo propietario o administrador pueden configurar la IA.")
        serializer = SettingsSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        config, _ = TenantAISettings.objects.update_or_create(
            tenant=request.tenant, defaults=serializer.validated_data
        )
        return Response(SettingsSerializer(config).data)


class MessageView(APIView):
    permission_classes = [HasConsistentTenant]

    @extend_schema(
        request=MessageSerializer, responses=MessageResultSerializer, parameters=[WRITE_CONTEXT]
    )
    def post(self, request):
        serializer = MessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        previous = read_context(data.get("context"), request.user, request.tenant)
        text = mask_text(data["text"])
        usage_id = reserve(request.user, request.tenant, text)
        interpretation = get_provider().interpret(
            text, local_today(request.tenant), request.tenant.timezone, previous
        )
        record_consumption(usage_id, interpretation)
        return Response(
            dispatch(
                interpretation.calls,
                actor=request.user,
                tenant=request.tenant,
                text=text,
                previous=previous,
            )
        )


class TranscriptionView(APIView):
    permission_classes = [HasConsistentTenant]
    parser_classes = [MultiPartParser]

    @extend_schema(
        request=TranscriptionSerializer,
        responses=TranscriptionResultSerializer,
        parameters=[WRITE_CONTEXT],
    )
    def post(self, request):
        serializer = TranscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            {
                "text": transcribe(
                    actor=request.user,
                    tenant=request.tenant,
                    upload=serializer.validated_data["audio"],
                )
            }
        )


class PrepareMessageView(APIView):
    permission_classes = [HasConsistentTenant]

    @extend_schema(
        request=PrepareMessageSerializer,
        responses=MessageResultSerializer,
        parameters=[WRITE_CONTEXT],
    )
    def post(self, request):
        serializer = PrepareMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        # Explicit human selection; no provider call or AI quota consumption.
        return Response(
            dispatch(
                [("prepare_whatsapp_message", json.dumps(data, default=str))],
                actor=request.user,
                tenant=request.tenant,
                previous={},
                text=f"{data['check_in']} {data['check_out']}",
            )
        )
