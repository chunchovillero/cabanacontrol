from django.urls import path

from apps.whatsapp import views

urlpatterns = [
    path("whatsapp/capabilities/", views.CapabilitiesView.as_view()),
    path("whatsapp/connection/", views.ConnectionView.as_view()),
    path("whatsapp/conversations/", views.ConversationListView.as_view()),
    path("whatsapp/conversations/<uuid:conversation_id>/", views.ConversationDetailView.as_view()),
    path(
        "whatsapp/conversations/<uuid:conversation_id>/messages/", views.MessageListView.as_view()
    ),
    path("whatsapp/messages/prepare/", views.PrepareView.as_view()),
    path("whatsapp/messages/send/", views.SendView.as_view()),
    path("whatsapp/consent/", views.ConsentView.as_view()),
    path("whatsapp/jobs/", views.JobListView.as_view()),
    path("whatsapp/templates/", views.TemplateListView.as_view()),
]
