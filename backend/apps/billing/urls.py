from django.urls import path

from apps.billing.simulation_views import (
    AcceptView,
    IntentView,
    QuoteView,
    ResultView,
    SimulationStateView,
)
from apps.billing.views import PlanUsageView

urlpatterns = [path("billing/plan/", PlanUsageView.as_view(), name="billing-plan")]
urlpatterns += [
    path("billing/simulation/", SimulationStateView.as_view()),
    path("billing/simulation/quotes/", QuoteView.as_view()),
    path("billing/simulation/intents/", IntentView.as_view()),
    path("billing/simulation/attempts/<uuid:attempt_id>/accept/", AcceptView.as_view()),
    path("billing/simulation/attempts/<uuid:attempt_id>/result/", ResultView.as_view()),
]
