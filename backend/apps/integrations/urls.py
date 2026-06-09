from django.urls import path

from .views import (
    ConnectIntegrationView,
    DisconnectIntegrationView,
    IntegrationAccountListView,
    IntegrationProviderListView,
    IntegrationSyncLogListView,
    ReconnectIntegrationView,
)

urlpatterns = [
    path("providers/", IntegrationProviderListView.as_view(), name="integration-providers"),
    path("accounts/", IntegrationAccountListView.as_view(), name="integration-accounts"),
    path(
        "<slug:provider_slug>/connect/",
        ConnectIntegrationView.as_view(),
        name="integration-connect",
    ),
    path(
        "<int:account_id>/disconnect/",
        DisconnectIntegrationView.as_view(),
        name="integration-disconnect",
    ),
    path(
        "<int:account_id>/reconnect/",
        ReconnectIntegrationView.as_view(),
        name="integration-reconnect",
    ),
    path(
        "<int:account_id>/sync-logs/",
        IntegrationSyncLogListView.as_view(),
        name="integration-sync-logs",
    ),
]
