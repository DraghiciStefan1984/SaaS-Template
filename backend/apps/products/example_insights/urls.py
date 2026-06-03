from django.urls import path

from .views import ExampleInsightRequestListCreateView

urlpatterns = [
    path(
        "requests/",
        ExampleInsightRequestListCreateView.as_view(),
        name="example-insight-requests",
    ),
]
