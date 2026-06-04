from django.urls import path

from .views import (
    DataDeletionRequestExecuteView,
    DataDeletionRequestListCreateView,
    DataExportRequestListCreateView,
)

urlpatterns = [
    path("exports/", DataExportRequestListCreateView.as_view(), name="privacy-exports"),
    path(
        "deletion-requests/",
        DataDeletionRequestListCreateView.as_view(),
        name="privacy-deletion-requests",
    ),
    path(
        "deletion-requests/<int:request_id>/execute/",
        DataDeletionRequestExecuteView.as_view(),
        name="privacy-deletion-request-execute",
    ),
]
