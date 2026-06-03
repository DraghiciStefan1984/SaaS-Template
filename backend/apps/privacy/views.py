from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response

from apps.audit.services import log_audit_event
from apps.organizations.models import MembershipStatus, Organization
from apps.organizations.permissions import ADMIN_ROLES, OWNER_ROLES, require_organization_role

from .models import DataDeletionRequest, DataExportRequest
from .serializers import (
    DataDeletionCreateSerializer,
    DataDeletionRequestSerializer,
    DataExportCreateSerializer,
    DataExportRequestSerializer,
)
from .services import create_data_deletion_request, create_data_export_request


def get_member_organization(user, organization_id):
    return get_object_or_404(
        Organization.objects.filter(
            memberships__user=user,
            memberships__status=MembershipStatus.ACTIVE,
        ).distinct(),
        id=organization_id,
    )


class DataExportRequestListCreateView(generics.ListCreateAPIView):
    queryset = DataExportRequest.objects.none()
    serializer_class = DataExportRequestSerializer
    throttle_scope = "expensive_action"

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="organization_id",
                type=int,
                location=OpenApiParameter.QUERY,
                required=True,
            )
        ],
        request=DataExportCreateSerializer,
        responses=DataExportRequestSerializer,
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(request=DataExportCreateSerializer, responses=DataExportRequestSerializer)
    def post(self, request, *args, **kwargs):
        serializer = DataExportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = get_member_organization(
            request.user,
            serializer.validated_data["organization_id"],
        )
        require_organization_role(request.user, organization, ADMIN_ROLES)
        export_request = create_data_export_request(
            organization=organization,
            requested_by=request.user,
            scope=serializer.validated_data["scope"],
        )
        log_audit_event(
            action="privacy.export.requested",
            organization=organization,
            request=request,
            category="privacy",
            target_entity_type="data_export_request",
            target_entity_id=export_request.id,
            metadata={"scope": export_request.scope, "status": export_request.status},
        )
        return Response(
            DataExportRequestSerializer(export_request).data,
            status=status.HTTP_201_CREATED,
        )

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return DataExportRequest.objects.none()

        organization = get_member_organization(
            self.request.user,
            self.request.query_params.get("organization_id"),
        )
        require_organization_role(self.request.user, organization, ADMIN_ROLES)
        return DataExportRequest.objects.filter(organization=organization).select_related(
            "requested_by"
        )


class DataDeletionRequestListCreateView(generics.ListCreateAPIView):
    queryset = DataDeletionRequest.objects.none()
    serializer_class = DataDeletionRequestSerializer
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
        request=DataDeletionCreateSerializer,
        responses=DataDeletionRequestSerializer,
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(request=DataDeletionCreateSerializer, responses=DataDeletionRequestSerializer)
    def post(self, request, *args, **kwargs):
        serializer = DataDeletionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = get_member_organization(
            request.user,
            serializer.validated_data["organization_id"],
        )
        require_organization_role(request.user, organization, OWNER_ROLES)
        deletion_request = create_data_deletion_request(
            organization=organization,
            requested_by=request.user,
            target=serializer.validated_data["target"],
            reason=serializer.validated_data.get("reason", ""),
            metadata={"source": "api"},
        )
        log_audit_event(
            action="privacy.deletion.requested",
            organization=organization,
            request=request,
            category="privacy",
            target_entity_type="data_deletion_request",
            target_entity_id=deletion_request.id,
            metadata={"target": deletion_request.target, "status": deletion_request.status},
        )
        return Response(
            DataDeletionRequestSerializer(deletion_request).data,
            status=status.HTTP_201_CREATED,
        )

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return DataDeletionRequest.objects.none()

        organization = get_member_organization(
            self.request.user,
            self.request.query_params.get("organization_id"),
        )
        require_organization_role(self.request.user, organization, OWNER_ROLES)
        return DataDeletionRequest.objects.filter(organization=organization).select_related(
            "requested_by"
        )
