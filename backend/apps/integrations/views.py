from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_audit_event
from apps.organizations.models import MembershipStatus, Organization
from apps.organizations.permissions import (
    ADMIN_ROLES,
    require_membership,
    require_organization_role,
)

from .models import IntegrationAccount, IntegrationProvider, IntegrationSyncLog
from .serializers import (
    ConnectIntegrationSerializer,
    DisconnectIntegrationResponseSerializer,
    IntegrationAccountSerializer,
    IntegrationProviderSerializer,
    IntegrationSyncLogSerializer,
    ReconnectIntegrationSerializer,
)
from .services import disconnect_integration_account


class OrganizationScopedMixin:
    def get_user_organization(self, organization_id):
        return get_object_or_404(
            Organization.objects.filter(
                memberships__user=self.request.user,
                memberships__status=MembershipStatus.ACTIVE,
            ).distinct(),
            id=organization_id,
        )

    def get_user_integration_account(self, account_id):
        return get_object_or_404(
            IntegrationAccount.objects.filter(
                organization__memberships__user=self.request.user,
                organization__memberships__status=MembershipStatus.ACTIVE,
            )
            .select_related("organization", "provider", "connected_by")
            .distinct(),
            id=account_id,
        )


class IntegrationProviderListView(generics.ListAPIView):
    serializer_class = IntegrationProviderSerializer
    pagination_class = None

    def get_queryset(self):
        return IntegrationProvider.objects.filter(is_active=True).order_by("category", "name")


class IntegrationAccountListView(OrganizationScopedMixin, generics.ListAPIView):
    queryset = IntegrationAccount.objects.none()
    serializer_class = IntegrationAccountSerializer

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
            return IntegrationAccount.objects.none()

        organization = self.get_user_organization(self.request.query_params.get("organization_id"))
        require_membership(self.request.user, organization)
        return (
            IntegrationAccount.objects.filter(organization=organization)
            .select_related("provider", "connected_by")
            .order_by("provider__name", "display_name")
        )


class ConnectIntegrationView(OrganizationScopedMixin, APIView):
    throttle_scope = "product_write"

    @extend_schema(
        request=ConnectIntegrationSerializer,
        responses={201: IntegrationAccountSerializer},
    )
    def post(self, request, provider_slug):
        provider = get_object_or_404(IntegrationProvider, slug=provider_slug, is_active=True)
        serializer = ConnectIntegrationSerializer(data=request.data, context={"provider": provider})
        serializer.is_valid(raise_exception=True)
        organization = self.get_user_organization(serializer.validated_data["organization_id"])
        require_organization_role(request.user, organization, ADMIN_ROLES)
        account = serializer.save(
            organization=organization,
            request=request,
            provider=provider,
        )
        log_audit_event(
            action="integrations.account.connected",
            organization=organization,
            request=request,
            category="integrations",
            target_entity_type="integration_account",
            target_entity_id=account.id,
            metadata={"provider_slug": provider.slug},
        )
        return Response(IntegrationAccountSerializer(account).data, status=status.HTTP_201_CREATED)


class DisconnectIntegrationView(OrganizationScopedMixin, APIView):
    throttle_scope = "product_write"

    @extend_schema(request=None, responses=DisconnectIntegrationResponseSerializer)
    def post(self, request, account_id):
        account = self.get_user_integration_account(account_id)
        require_organization_role(request.user, account.organization, ADMIN_ROLES)
        disconnect_integration_account(account)
        log_audit_event(
            action="integrations.account.disconnected",
            organization=account.organization,
            request=request,
            category="integrations",
            target_entity_type="integration_account",
            target_entity_id=account.id,
            metadata={"provider_slug": account.provider.slug},
        )
        return Response({"status": account.status})


class ReconnectIntegrationView(OrganizationScopedMixin, APIView):
    throttle_scope = "product_write"

    @extend_schema(
        request=ReconnectIntegrationSerializer,
        responses=IntegrationAccountSerializer,
    )
    def post(self, request, account_id):
        account = self.get_user_integration_account(account_id)
        require_organization_role(request.user, account.organization, ADMIN_ROLES)
        serializer = ReconnectIntegrationSerializer(
            data=request.data,
            context={"account": account, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        account = serializer.save()
        log_audit_event(
            action="integrations.account.reconnected",
            organization=account.organization,
            request=request,
            category="integrations",
            target_entity_type="integration_account",
            target_entity_id=account.id,
            metadata={"provider_slug": account.provider.slug},
        )
        return Response(IntegrationAccountSerializer(account).data)


class IntegrationSyncLogListView(OrganizationScopedMixin, generics.ListAPIView):
    queryset = IntegrationSyncLog.objects.none()
    serializer_class = IntegrationSyncLogSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return IntegrationSyncLog.objects.none()

        account = self.get_user_integration_account(self.kwargs["account_id"])
        require_organization_role(self.request.user, account.organization, ADMIN_ROLES)
        return IntegrationSyncLog.objects.filter(integration_account=account).order_by(
            "-created_at",
            "-id",
        )
