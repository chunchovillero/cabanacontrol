from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.insights.queries import snapshot_calendar, snapshot_dashboard
from apps.insights.serializers import (
    CalendarResultSerializer,
    DashboardResultSerializer,
    PeriodQuerySerializer,
)
from apps.tenants.permissions import HasConsistentTenant


class CalendarView(APIView):
    permission_classes = [HasConsistentTenant]

    @extend_schema(parameters=[PeriodQuerySerializer], responses=CalendarResultSerializer)
    def get(self, request):
        query = PeriodQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data
        result = snapshot_calendar(
            request.tenant, data["from"], data["to"], data.get("property_id")
        )
        return Response(CalendarResultSerializer(result).data)


class DashboardView(APIView):
    permission_classes = [HasConsistentTenant]

    @extend_schema(parameters=[PeriodQuerySerializer], responses=DashboardResultSerializer)
    def get(self, request):
        query = PeriodQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data
        result = snapshot_dashboard(
            request.tenant, data["from"], data["to"], data.get("property_id")
        )
        return Response(DashboardResultSerializer(result).data)
