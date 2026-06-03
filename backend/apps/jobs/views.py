from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics

from apps.organizations.models import MembershipStatus, Organization
from apps.organizations.permissions import require_membership

from .models import JobRun
from .serializers import JobRunSerializer


class JobRunListView(generics.ListAPIView):
    queryset = JobRun.objects.none()
    serializer_class = JobRunSerializer

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
            return JobRun.objects.none()

        organization = get_object_or_404(
            Organization.objects.filter(
                memberships__user=self.request.user,
                memberships__status=MembershipStatus.ACTIVE,
            ).distinct(),
            id=self.request.query_params.get("organization_id"),
        )
        require_membership(self.request.user, organization)
        return JobRun.objects.filter(organization=organization).select_related("created_by")

