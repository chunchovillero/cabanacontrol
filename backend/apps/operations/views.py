from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.insights.queries import property_scope
from apps.operations.day import daily_snapshot
from apps.operations.day_serializers import DayQuerySerializer, DayResultSerializer
from apps.operations.models import HousekeepingTask
from apps.operations.serializers import (
    AssigneeSerializer,
    TaskCreateSerializer,
    TaskQuerySerializer,
    TaskSerializer,
    TaskWriteSerializer,
)
from apps.operations.services import save_task
from apps.reservations.services import local_today
from apps.tenants.models import Membership
from apps.tenants.permissions import HasConsistentTenant


class OperationsDayView(APIView):
    permission_classes = [HasConsistentTenant]

    @extend_schema(parameters=[DayQuerySerializer], responses=DayResultSerializer)
    def get(self, request):
        query = DayQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data
        result = daily_snapshot(
            request.tenant,
            data.get("date", local_today(request.tenant)),
            data["kind"],
            data["page"],
            data.get("property_id"),
        )
        return Response(DayResultSerializer(result).data)


def tenant_tasks(tenant):
    return HousekeepingTask.objects.filter(tenant=tenant).select_related(
        "property", "assigned_to__user"
    )


class TaskListView(generics.ListCreateAPIView):
    permission_classes = [HasConsistentTenant]
    serializer_class = TaskSerializer

    def get_queryset(self):
        query = TaskQuerySerializer(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data
        rows = tenant_tasks(self.request.tenant)
        if data.get("property_id"):
            property_scope(self.request.tenant, data["property_id"])
            rows = rows.filter(property_id=data["property_id"])
        if data.get("status"):
            rows = rows.filter(status=data["status"])
        if data.get("assigned_to_id"):
            get_object_or_404(Membership, tenant=self.request.tenant, pk=data["assigned_to_id"])
            rows = rows.filter(assigned_to_id=data["assigned_to_id"])
        return rows

    @extend_schema(parameters=[TaskQuerySerializer])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(request=TaskCreateSerializer, responses={201: TaskSerializer})
    def post(self, request):
        query = TaskCreateSerializer(data=request.data)
        query.is_valid(raise_exception=True)
        task = save_task(actor=request.user, tenant=request.tenant, data=query.validated_data)
        return Response(
            TaskSerializer(tenant_tasks(request.tenant).get(pk=task.pk)).data, status=201
        )


class TaskDetailView(generics.RetrieveAPIView):
    permission_classes = [HasConsistentTenant]
    serializer_class = TaskSerializer
    lookup_url_kwarg = "task_id"

    def get_queryset(self):
        return tenant_tasks(self.request.tenant)

    @extend_schema(request=TaskWriteSerializer, responses=TaskSerializer)
    def patch(self, request, task_id):
        instance = self.get_object()
        query = TaskWriteSerializer(data=request.data)
        query.is_valid(raise_exception=True)
        task = save_task(
            actor=request.user, tenant=request.tenant, instance=instance, data=query.validated_data
        )
        return Response(TaskSerializer(tenant_tasks(request.tenant).get(pk=task.pk)).data)


class AssigneeListView(generics.ListAPIView):
    permission_classes = [HasConsistentTenant]
    serializer_class = AssigneeSerializer

    def get_queryset(self):
        return (
            Membership.objects.filter(tenant=self.request.tenant, active=True, user__is_active=True)
            .select_related("user")
            .order_by("user__first_name", "pk")
        )
