from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_audit_event
from apps.organizations.models import MembershipStatus, Organization
from apps.organizations.permissions import (
    ADMIN_ROLES,
    require_membership,
    require_organization_role,
)

from .models import (
    AICallLog,
    AIModelDecisionLog,
    AIModelPolicy,
    AIProvider,
    AITaskProfile,
    PromptTemplate,
)
from .serializers import (
    AICallLogSerializer,
    AIExecutionPlanRequestSerializer,
    AIExecutionPlanSerializer,
    AIModelDecisionLogSerializer,
    AIModelPolicySerializer,
    AIProviderSerializer,
    AITaskProfileSerializer,
    PromptTemplateSerializer,
)
from .services import select_ai_execution_plan


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


class AIProviderListView(generics.ListAPIView):
    serializer_class = AIProviderSerializer
    pagination_class = None

    def get_queryset(self):
        return AIProvider.objects.filter(is_active=True).order_by("name")


class PromptTemplateListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = PromptTemplateSerializer

    def get_queryset(self):
        return PromptTemplate.objects.filter(is_active=True).order_by("key", "-version")


class AITaskProfileListView(generics.ListAPIView):
    serializer_class = AITaskProfileSerializer

    def get_queryset(self):
        return AITaskProfile.objects.filter(is_active=True).order_by("key")


class AIModelPolicyListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = AIModelPolicySerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="task_key",
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
            )
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = (
            AIModelPolicy.objects.filter(is_active=True)
            .select_related("task_profile", "provider", "fallback_provider")
            .order_by("task_profile__key", "priority", "id")
        )
        task_key = self.request.query_params.get("task_key")
        if task_key:
            queryset = queryset.filter(task_profile__key=task_key)
        return queryset


class AIExecutionPlanView(APIView):
    throttle_scope = "expensive_action"

    @extend_schema(
        request=AIExecutionPlanRequestSerializer,
        responses=AIExecutionPlanSerializer,
    )
    def post(self, request):
        serializer = AIExecutionPlanRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        organization = get_member_organization(request.user, data["organization_id"])
        execution_plan = select_ai_execution_plan(
            organization=organization,
            user=request.user,
            task_key=data["task_key"],
            input_payload=data.get("input_payload"),
            constraints=data.get("constraints") or {},
            metadata=data.get("metadata") or {},
            log_decision=data.get("log_decision", True),
        )
        log_audit_event(
            action="ai.execution_plan.created",
            organization=organization,
            request=request,
            category="ai",
            target_entity_type="ai_task_profile",
            target_entity_id=data["task_key"],
            metadata={
                "strategy": execution_plan["strategy"],
                "provider_slug": execution_plan["provider_slug"],
            },
        )
        return Response(AIExecutionPlanSerializer(execution_plan).data)


class AIModelDecisionLogListView(generics.ListAPIView):
    queryset = AIModelDecisionLog.objects.none()
    serializer_class = AIModelDecisionLogSerializer

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
            return AIModelDecisionLog.objects.none()

        organization = get_member_organization(
            self.request.user,
            self.request.query_params.get("organization_id"),
        )
        require_organization_role(self.request.user, organization, ADMIN_ROLES)
        return (
            AIModelDecisionLog.objects.filter(organization=organization)
            .select_related(
                "task_profile",
                "policy",
                "selected_provider",
                "fallback_provider",
                "user",
            )
            .order_by("-created_at", "-id")
        )


class AICallLogListView(generics.ListAPIView):
    queryset = AICallLog.objects.none()
    serializer_class = AICallLogSerializer

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
            return AICallLog.objects.none()

        organization = get_member_organization(
            self.request.user,
            self.request.query_params.get("organization_id"),
        )
        require_organization_role(self.request.user, organization, ADMIN_ROLES)
        return (
            AICallLog.objects.filter(organization=organization)
            .select_related("provider", "prompt_template", "user")
            .order_by("-created_at", "-id")
        )
