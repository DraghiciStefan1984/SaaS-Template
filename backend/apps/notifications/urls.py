from django.urls import path

from .views import NotificationDeliveryLogListView, NotificationPreferenceListCreateView

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
]
