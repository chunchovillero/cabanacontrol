from django.urls import path

from apps.insights.report_views import ReportExportView, ReportView
from apps.insights.views import CalendarView, DashboardView

urlpatterns = [
    path("reports/", ReportView.as_view(), name="reports"),
    path("reports/export/", ReportExportView.as_view(), name="reports-export"),
    path("calendar/", CalendarView.as_view(), name="calendar"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
]
