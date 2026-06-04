from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response

from apps.audit.services import log_audit_event
from apps.organizations.models import MembershipStatus, Organization
from apps.organizations.permissions import (
    ADMIN_ROLES,
    require_membership,
    require_organization_role,
)

from .models import NotificationDeliveryLog, NotificationPreference
from .serializers import (
    NotificationDeliveryLogSerializer,
    NotificationPreferenceSerializer,
    NotificationPreferenceUpsertSerializer,
)
from .services import upsert_notification_preference


def get_member_organization(user, organization_id):
    organization = get_object_or_404(
        Organization.objects.filter(
            memberships__user=user,
            memberships__status=MembershipStatus.ACTIVE,
        ).distinct(),
        id=organization_id,
    )
    require_membership(user, organization)
    return organization


class NotificationPreferenceListCreateView(generics.ListCreateAPIView):
    queryset = NotificationPreference.objects.none()
    serializer_class = NotificationPreferenceSerializer
    throttle_scope = "product_write"

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="organization_id",
                type=int,
                location=OpenApiParameter.QUERY,
                required=True,
            )
        ],
        request=NotificationPreferenceUpsertSerializer,
        responses=NotificationPreferenceSerializer,
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        request=NotificationPreferenceUpsertSerializer,
        responses=NotificationPreferenceSerializer,
    )
    def post(self, request, *args, **kwargs):
        serializer = NotificationPreferenceUpsertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        organization = get_member_organization(request.user, data["organization_id"])
        target_user = None
        if data.get("user_id"):
            target_user = get_object_or_404(get_user_model(), id=data["user_id"])
            require_membership(target_user, organization)
            if target_user != request.user:
                require_organization_role(request.user, organization, ADMIN_ROLES)
        else:
            require_organization_role(request.user, organization, ADMIN_ROLES)
        preference = upsert_notification_preference(
            organization=organization,
            user=target_user,
            event=data["event"],
            channel=data["channel"],
            is_enabled=data["is_enabled"],
            config=data.get("config", {}),
        )
        log_audit_event(
            action="notifications.preference.updated",
            organization=organization,
            request=request,
            category="notifications",
            target_entity_type="notification_preference",
            target_entity_id=preference.id,
            metadata={
                "event": preference.event,
                "channel": preference.channel,
                "is_enabled": preference.is_enabled,
            },
        )
        return Response(
            NotificationPreferenceSerializer(preference).data,
            status=status.HTTP_200_OK,
        )

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return NotificationPreference.objects.none()

        organization = get_member_organization(
            self.request.user,
            self.request.query_params.get("organization_id"),
        )
        membership = require_membership(self.request.user, organization)
        queryset = NotificationPreference.objects.filter(organization=organization).select_related(
            "user"
        )
        if membership.role not in ADMIN_ROLES:
            queryset = queryset.filter(user=self.request.user)
        return queryset


class NotificationDeliveryLogListView(generics.ListAPIView):
    queryset = NotificationDeliveryLog.objects.none()
    serializer_class = NotificationDeliveryLogSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="organization_id",
                type=int,
                location=OpenApiParameter.QUERY,
                required=True,
            )
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return NotificationDeliveryLog.objects.none()

        organization = get_member_organization(
            self.request.user,
            self.request.query_params.get("organization_id"),
        )
        require_organization_role(self.request.user, organization, ADMIN_ROLES)
        return NotificationDeliveryLog.objects.filter(organization=organization).select_related(
            "user"
        )
