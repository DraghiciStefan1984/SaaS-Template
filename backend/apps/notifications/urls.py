from django.urls import path

from .views import (
    InAppNotificationListView,
    InAppNotificationReadAllView,
    InAppNotificationReadView,
    NotificationDeliveryLogListView,
    NotificationPreferenceListCreateView,
)

urlpatterns = [
    path(
        "preferences/",
        NotificationPreferenceListCreateView.as_view(),
        name="notification-preferences",
    ),
    path(
        "delivery-logs/",
        NotificationDeliveryLogListView.as_view(),
        name="notification-delivery-logs",
    ),
    path("in-app/", InAppNotificationListView.as_view(), name="in-app-notifications"),
    path("in-app/read-all/", InAppNotificationReadAllView.as_view(), name="in-app-read-all"),
    path("in-app/<int:pk>/read/", InAppNotificationReadView.as_view(), name="in-app-read"),
]
