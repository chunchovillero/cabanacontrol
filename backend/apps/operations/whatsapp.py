from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import record_event
from apps.reservations.models import Reservation
from apps.tenants.permissions import HasConsistentTenant


class WhatsAppDraftSerializer(serializers.Serializer):
    phone = serializers.CharField()
    message = serializers.CharField()


class WhatsAppDraftView(APIView):
    permission_classes = [HasConsistentTenant]

    @extend_schema(responses=WhatsAppDraftSerializer)
    def get(self, request, reservation_id):
        item = get_object_or_404(
            Reservation.objects.filter(tenant=request.tenant)
            .select_related("property", "primary_guest")
            .only(
                "id",
                "tenant_id",
                "check_in",
                "check_out",
                "status",
                "property__id",
                "property__name",
                "primary_guest__id",
                "primary_guest__phone",
            ),
            pk=reservation_id,
        )
        message = (
            f"Hola. Te contactamos por la reserva en {item.property.name}, "
            f"con entrada el {item.check_in:%d/%m/%Y} y salida el {item.check_out:%d/%m/%Y}. "
            f"Estado: {item.get_status_display()}. Puedes escribirnos por aquí para coordinar."
        )
        record_event(
            actor=request.user,
            tenant=request.tenant,
            entity="reservation",
            entity_id=item.pk,
            action="whatsapp_draft_viewed",
        )
        return Response({"phone": item.primary_guest.phone, "message": message})
