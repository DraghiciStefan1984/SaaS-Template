from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.organizations.models import MembershipStatus, Organization
from apps.organizations.permissions import require_membership

from .serializers import UsageSummarySerializer
from .services import usage_summary_for_organization


class UsageSummaryView(APIView):
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="organization_id",
                type=int,
                location=OpenApiParameter.QUERY,
                required=True,
            )
        ],
        responses=UsageSummarySerializer,
    )
    def get(self, request):
        organization = get_object_or_404(
            Organization.objects.filter(
                memberships__user=request.user,
                memberships__status=MembershipStatus.ACTIVE,
            ).distinct(),
            id=request.query_params.get("organization_id"),
        )
        require_membership(request.user, organization)
        return Response(usage_summary_for_organization(organization))
