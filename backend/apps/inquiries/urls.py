from django.urls import path

from apps.inquiries.views import (
    InquiryAnalyzeView,
    InquiryAssigneesView,
    InquiryConvertView,
    InquiryDetailView,
    InquiryListView,
    InquiryStatsView,
)

urlpatterns = [
    path("inquiries/", InquiryListView.as_view()),
    path("inquiries/stats/", InquiryStatsView.as_view()),
    path("inquiries/assignees/", InquiryAssigneesView.as_view()),
    path("inquiries/<uuid:inquiry_id>/", InquiryDetailView.as_view()),
    path("inquiries/<uuid:inquiry_id>/analyze/", InquiryAnalyzeView.as_view()),
    path("inquiries/<uuid:inquiry_id>/convert/", InquiryConvertView.as_view()),
]
