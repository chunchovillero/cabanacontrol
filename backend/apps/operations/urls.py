from django.urls import path

from apps.operations.views import AssigneeListView, OperationsDayView, TaskDetailView, TaskListView
from apps.operations.whatsapp import WhatsAppDraftView

urlpatterns = [
    path(
        "reservations/<uuid:reservation_id>/whatsapp-draft/",
        WhatsAppDraftView.as_view(),
        name="whatsapp-draft",
    ),
    path("operations/day/", OperationsDayView.as_view(), name="operations-day"),
    path("housekeeping/", TaskListView.as_view(), name="housekeeping"),
    path("housekeeping/<uuid:task_id>/", TaskDetailView.as_view(), name="housekeeping-detail"),
    path("housekeeping/assignees/", AssigneeListView.as_view(), name="housekeeping-assignees"),
]
