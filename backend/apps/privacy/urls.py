from django.urls import path

from .views import DataDeletionRequestListCreateView, DataExportRequestListCreateView

urlpatterns = [
    path("exports/", DataExportRequestListCreateView.as_view(), name="privacy-exports"),
    path(
        "deletion-requests/",
        DataDeletionRequestListCreateView.as_view(),
        name="privacy-deletion-requests",
    ),
]
