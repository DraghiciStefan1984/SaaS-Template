from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response

from apps.audit.services import log_audit_event
from apps.organizations.models import MembershipStatus, Organization
from apps.organizations.permissions import require_membership

from .models import ExampleInsightRequest
from .serializers import ExampleInsightCreateSerializer, ExampleInsightRequestSerializer


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


class ExampleInsightRequestListCreateView(generics.ListCreateAPIView):
    queryset = ExampleInsightRequest.objects.none()
    serializer_class = ExampleInsightRequestSerializer
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
        request=ExampleInsightCreateSerializer,
        responses=ExampleInsightRequestSerializer,
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        request=ExampleInsightCreateSerializer,
        responses=ExampleInsightRequestSerializer,
    )
    def post(self, request, *args, **kwargs):
        serializer = ExampleInsightCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = get_member_organization(
            request.user,
            serializer.validated_data["organization_id"],
        )
        insight_request = serializer.save(
            organization=organization,
            created_by=request.user,
        )
        log_audit_event(
            action="products.example_insights.request.created",
            organization=organization,
            request=request,
            category="products",
            target_entity_type="example_insight_request",
            target_entity_id=insight_request.id,
            metadata={
                "strategy": insight_request.ai_execution_plan.get("strategy"),
                "report_id": insight_request.report_id,
                "job_run_id": insight_request.job_run_id,
            },
        )
        return Response(
            ExampleInsightRequestSerializer(insight_request).data,
            status=status.HTTP_201_CREATED,
        )

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ExampleInsightRequest.objects.none()

        organization = get_member_organization(
            self.request.user,
            self.request.query_params.get("organization_id"),
        )
        return (
            ExampleInsightRequest.objects.filter(organization=organization)
            .select_related("created_by", "report", "job_run")
            .order_by("-created_at", "-id")
        )
