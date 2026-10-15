from django.urls import path

from apps.assistant.views import (
    CapabilitiesView,
    MessageView,
    PrepareMessageView,
    SettingsView,
    TranscriptionView,
)

urlpatterns = [
    path("assistant/capabilities/", CapabilitiesView.as_view()),
    path("assistant/settings/", SettingsView.as_view()),
    path("assistant/messages/", MessageView.as_view()),
    path("assistant/transcriptions/", TranscriptionView.as_view()),
    path("assistant/whatsapp/", PrepareMessageView.as_view()),
]
