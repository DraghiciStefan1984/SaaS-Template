from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_audit_event
from apps.privacy.models import DataDeletionTarget
from apps.privacy.services import create_data_deletion_request, execute_data_deletion_request

from .models import Membership, MembershipStatus, Organization
from .permissions import ADMIN_ROLES, OWNER_ROLES, require_organization_role
from .serializers import (
    AcceptInvitationSerializer,
    InviteMemberSerializer,
    MembershipSerializer,
    OrganizationSerializer,
)
from .services import (
    accept_membership_invitation,
    cancel_membership_invitation,
    send_membership_invitation_email,
)


class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.none()
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Organization.objects.none()

        return (
            Organization.objects.filter(
                memberships__user=self.request.user,
                memberships__status=MembershipStatus.ACTIVE,
            )
            .select_related("owner")
            .distinct()
        )

    def perform_update(self, serializer):
        require_organization_role(self.request.user, self.get_object(), ADMIN_ROLES)
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        organization = self.get_object()
        require_organization_role(request.user, organization, OWNER_ROLES)
        deletion_request = create_data_deletion_request(
            organization=organization,
            requested_by=request.user,
            target=DataDeletionTarget.ORGANIZATION,
            reason="Organization deleted through the API.",
            metadata={"source": "organization_destroy"},
        )
        execute_data_deletion_request(deletion_request)
        log_audit_event(
            action="organizations.deleted",
            organization=organization,
            request=request,
            category="organizations",
            target_entity_type="organization",
            target_entity_id=organization.id,
            metadata={
                "deletion_request_id": deletion_request.id,
                "status": deletion_request.status,
            },
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def members(self, request, pk=None):
        organization = self.get_object()
        require_organization_role(request.user, organization, ADMIN_ROLES)
        memberships = organization.memberships.filter(
            status__in=[MembershipStatus.ACTIVE, MembershipStatus.INVITED],
        ).select_related("user")
        return Response(MembershipSerializer(memberships, many=True).data)

    @extend_schema(request=InviteMemberSerializer, responses=MembershipSerializer)
    @action(detail=True, methods=["post"], url_path="invite-member")
    def invite_member(self, request, pk=None):
        organization = self.get_object()
        require_organization_role(request.user, organization, ADMIN_ROLES)
        serializer = InviteMemberSerializer(
            data=request.data,
            context={"request": request, "organization": organization},
        )
        serializer.is_valid(raise_exception=True)
        membership = serializer.save()
        send_membership_invitation_email(membership)
        log_audit_event(
            action="organizations.invitation.sent",
            organization=organization,
            request=request,
            category="organizations",
            target_entity_type="membership",
            target_entity_id=membership.id,
            metadata={"role": membership.role},
        )
        return Response(MembershipSerializer(membership).data, status=status.HTTP_201_CREATED)

    def _pending_invitation(self, organization, membership_id):
        return get_object_or_404(
            Membership,
            id=membership_id,
            organization=organization,
            status=MembershipStatus.INVITED,
            user__isnull=True,
        )

    @extend_schema(
        parameters=[OpenApiParameter("membership_id", int, OpenApiParameter.PATH)],
        request=None,
        responses=MembershipSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path=r"invitations/(?P<membership_id>[^/.]+)/resend",
    )
    def resend_invitation(self, request, pk=None, membership_id=None):
        organization = self.get_object()
        require_organization_role(request.user, organization, ADMIN_ROLES)
        membership = self._pending_invitation(organization, membership_id)
        send_membership_invitation_email(membership)
        log_audit_event(
            action="organizations.invitation.resent",
            organization=organization,
            request=request,
            category="organizations",
            target_entity_type="membership",
            target_entity_id=membership.id,
        )
        return Response(MembershipSerializer(membership).data)

    @extend_schema(
        parameters=[OpenApiParameter("membership_id", int, OpenApiParameter.PATH)],
        request=None,
        responses=MembershipSerializer,
    )
    @action(
        detail=True,
        methods=["post"],
        url_path=r"invitations/(?P<membership_id>[^/.]+)/cancel",
    )
    def cancel_invitation(self, request, pk=None, membership_id=None):
        organization = self.get_object()
        require_organization_role(request.user, organization, ADMIN_ROLES)
        membership = self._pending_invitation(organization, membership_id)
        cancel_membership_invitation(membership)
        log_audit_event(
            action="organizations.invitation.cancelled",
            organization=organization,
            request=request,
            category="organizations",
            target_entity_type="membership",
            target_entity_id=membership.id,
        )
        return Response(MembershipSerializer(membership).data)


class AcceptInvitationView(APIView):
    throttle_scope = "auth"

    @extend_schema(request=AcceptInvitationSerializer, responses=MembershipSerializer)
    def post(self, request):
        serializer = AcceptInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = accept_membership_invitation(
            token=serializer.validated_data["token"],
            user=request.user,
        )
        log_audit_event(
            action="organizations.invitation.accepted",
            organization=membership.organization,
            request=request,
            category="organizations",
            target_entity_type="membership",
            target_entity_id=membership.id,
        )
        return Response(MembershipSerializer(membership).data)
