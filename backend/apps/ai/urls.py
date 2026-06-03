from django.urls import path

from .views import (
    AICallLogListView,
    AIExecutionPlanView,
    AIModelDecisionLogListView,
    AIModelPolicyListView,
    AIProviderListView,
    AITaskProfileListView,
    PromptTemplateListView,
)

urlpatterns = [
    path("providers/", AIProviderListView.as_view(), name="ai-providers"),
    path("prompt-templates/", PromptTemplateListView.as_view(), name="ai-prompt-templates"),
    path("task-profiles/", AITaskProfileListView.as_view(), name="ai-task-profiles"),
    path("model-policies/", AIModelPolicyListView.as_view(), name="ai-model-policies"),
    path("execution-plan/", AIExecutionPlanView.as_view(), name="ai-execution-plan"),
    path("decision-logs/", AIModelDecisionLogListView.as_view(), name="ai-decision-logs"),
    path("call-logs/", AICallLogListView.as_view(), name="ai-call-logs"),
]
