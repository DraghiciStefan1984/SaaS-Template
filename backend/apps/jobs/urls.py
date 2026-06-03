from django.urls import path

from .views import JobRunListView

urlpatterns = [
    path("", JobRunListView.as_view(), name="job-runs"),
]

