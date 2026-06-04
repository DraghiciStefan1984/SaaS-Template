from django.urls import path

from .views import (
    ReportArtifactListView,
    ReportDetailView,
    ReportListCreateView,
    ReportTemplateListView,
)

urlpatterns = [
    path("templates/", ReportTemplateListView.as_view(), name="report-templates"),
    path("", ReportListCreateView.as_view(), name="reports"),
    path("<int:pk>/", ReportDetailView.as_view(), name="report-detail"),
    path("<int:report_id>/artifacts/", ReportArtifactListView.as_view(), name="report-artifacts"),
]

