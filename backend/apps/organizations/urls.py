from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AcceptInvitationView, OrganizationViewSet

router = DefaultRouter()
router.register("", OrganizationViewSet, basename="organization")

urlpatterns = [
    path("invitations/accept/", AcceptInvitationView.as_view(), name="accept-invitation"),
    *router.urls,
]
