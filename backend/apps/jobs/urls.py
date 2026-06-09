from django.urls import path

from .views import (
    JobRunListView,
    ScheduledRunListView,
    ScheduledWorkflowListCreateView,
    ScheduledWorkflowPauseView,
    ScheduledWorkflowResumeView,
    ScheduledWorkflowRunView,
)

urlpatterns = [
    path("", JobRunListView.as_view(), name="job-runs"),
    path("schedules/", ScheduledWorkflowListCreateView.as_view(), name="scheduled-workflows"),
    path(
        "schedules/<int:workflow_id>/runs/",
        ScheduledRunListView.as_view(),
        name="scheduled-workflow-runs",
    ),
    path(
        "schedules/<int:workflow_id>/run/",
        ScheduledWorkflowRunView.as_view(),
        name="scheduled-workflow-run",
    ),
    path(
        "schedules/<int:workflow_id>/pause/",
        ScheduledWorkflowPauseView.as_view(),
        name="scheduled-workflow-pause",
    ),
    path(
        "schedules/<int:workflow_id>/resume/",
        ScheduledWorkflowResumeView.as_view(),
        name="scheduled-workflow-resume",
    ),
]
