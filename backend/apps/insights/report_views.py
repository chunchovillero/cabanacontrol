from django.http import HttpResponse
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    PolymorphicProxySerializer,
    extend_schema,
)
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import record_event
from apps.insights.report_serializers import (
    ReportExportQuerySerializer,
    ReportPaymentPageSerializer,
    ReportQuerySerializer,
    ReportReservationPageSerializer,
    ReportSummarySerializer,
)
from apps.insights.reports import report_csv, snapshot_report
from apps.tenants.permissions import HasConsistentTenant, TenantContextConflict


class ReportView(APIView):
    permission_classes = [HasConsistentTenant]

    @extend_schema(
        parameters=[ReportQuerySerializer],
        responses=PolymorphicProxySerializer(
            component_name="ReportResult",
            serializers=[
                ReportSummarySerializer,
                ReportReservationPageSerializer,
                ReportPaymentPageSerializer,
            ],
            resource_type_field_name=None,
        ),
    )
    def get(self, request):
        query = ReportQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        result = snapshot_report(request.tenant, query.validated_data)
        response = Response(result)
        response["Cache-Control"] = "private, no-store"
        return response


class ReportExportView(APIView):
    permission_classes = [HasConsistentTenant]

    @extend_schema(
        parameters=[
            ReportExportQuerySerializer,
            OpenApiParameter(
                "X-Tenant-Context", OpenApiTypes.UUID, OpenApiParameter.HEADER, required=True
            ),
        ],
        responses={(200, "text/csv"): OpenApiTypes.BINARY},
    )
    def get(self, request):
        if not request.headers.get("X-Tenant-Context"):
            raise TenantContextConflict()
        query = ReportExportQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data
        if "page" in request.query_params:
            raise ValidationError("La exportación incluye todas las páginas; no envíes page.")
        result = snapshot_report(request.tenant, data, export=True)
        content = report_csv(result, data["kind"])
        record_event(
            actor=request.user,
            tenant=request.tenant,
            action="report.export",
            entity="report",
            after={
                "kind": data["kind"],
                "from": data["from"].isoformat(),
                "to": data["to"].isoformat(),
                "property_id": str(data.get("property_id", "")),
                "status": data.get("status", ""),
                "rows": len(result["money"]) if data["kind"] == "summary" else result["count"],
            },
        )
        response = HttpResponse(content, content_type="text/csv; charset=utf-8")
        filename = f"cabanacontrol-{data['kind']}-{data['from']}-{data['to']}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
