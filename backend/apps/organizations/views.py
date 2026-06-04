from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.privacy.models import DataDeletionTarget
from apps.privacy.services import create_data_deletion_request, execute_data_deletion_request

from .models import MembershipStatus, Organization
from .permissions import ADMIN_ROLES, OWNER_ROLES, require_organization_role
from .serializers import InviteMemberSerializer, MembershipSerializer, OrganizationSerializer


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
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def members(self, request, pk=None):
        organization = self.get_object()
        require_organization_role(request.user, organization, ADMIN_ROLES)
        memberships = organization.memberships.filter(
            status=MembershipStatus.ACTIVE,
        ).select_related("user")
        return Response(MembershipSerializer(memberships, many=True).data)

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
        return Response(MembershipSerializer(membership).data, status=status.HTTP_201_CREATED)
