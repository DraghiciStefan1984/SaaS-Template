from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_audit_event
from apps.organizations.models import MembershipStatus, Organization
from apps.organizations.permissions import ADMIN_ROLES, require_organization_role

from .models import (
    JobRun,
    ScheduledRun,
    ScheduledRunTrigger,
    ScheduledWorkflow,
    ScheduledWorkflowStatus,
)
from .serializers import (
    JobRunSerializer,
    ScheduledRunSerializer,
    ScheduledWorkflowCreateSerializer,
    ScheduledWorkflowSerializer,
)
from .services import (
    create_scheduled_workflow,
    run_scheduled_workflow,
    set_scheduled_workflow_status,
)


def get_admin_organization(user, organization_id):
    organization = get_object_or_404(
        Organization.objects.filter(
            memberships__user=user,
            memberships__status=MembershipStatus.ACTIVE,
        ).distinct(),
        id=organization_id,
    )
    require_organization_role(user, organization, ADMIN_ROLES)
    return organization


def get_admin_scheduled_workflow(user, workflow_id):
    workflow = get_object_or_404(
        ScheduledWorkflow.objects.select_related("organization", "created_by").filter(
            organization__memberships__user=user,
            organization__memberships__status=MembershipStatus.ACTIVE,
        ),
        id=workflow_id,
    )
    require_organization_role(user, workflow.organization, ADMIN_ROLES)
    return workflow


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
        require_organization_role(self.request.user, organization, ADMIN_ROLES)
        return JobRun.objects.filter(organization=organization).select_related("created_by")


class ScheduledWorkflowListCreateView(generics.ListCreateAPIView):
    queryset = ScheduledWorkflow.objects.none()
    serializer_class = ScheduledWorkflowSerializer
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
        request=ScheduledWorkflowCreateSerializer,
        responses=ScheduledWorkflowSerializer,
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        request=ScheduledWorkflowCreateSerializer,
        responses={status.HTTP_201_CREATED: ScheduledWorkflowSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = ScheduledWorkflowCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        organization = get_admin_organization(request.user, data["organization_id"])
        workflow = create_scheduled_workflow(
            organization=organization,
            created_by=request.user,
            name=data["name"],
            frequency=data["frequency"],
            timezone_name=data["timezone"],
            next_run_at=data.get("next_run_at"),
            config={
                "title": data["title"],
                "template_key": data["template_key"],
                "requested_format": data["requested_format"],
                "input_payload": data.get("input_payload", {}),
            },
        )
        log_audit_event(
            action="jobs.scheduled_workflow.created",
            organization=organization,
            request=request,
            category="jobs",
            target_entity_type="scheduled_workflow",
            target_entity_id=workflow.id,
            metadata={"frequency": workflow.frequency, "workflow_type": workflow.workflow_type},
        )
        return Response(
            ScheduledWorkflowSerializer(workflow).data,
            status=status.HTTP_201_CREATED,
        )

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ScheduledWorkflow.objects.none()
        organization = get_admin_organization(
            self.request.user,
            self.request.query_params.get("organization_id"),
        )
        return ScheduledWorkflow.objects.filter(organization=organization).select_related(
            "created_by"
        )


class ScheduledWorkflowRunView(APIView):
    throttle_scope = "expensive_action"

    @extend_schema(request=None, responses=ScheduledRunSerializer)
    def post(self, request, workflow_id):
        workflow = get_admin_scheduled_workflow(request.user, workflow_id)
        scheduled_run = run_scheduled_workflow(
            workflow,
            trigger=ScheduledRunTrigger.MANUAL,
            requested_by=request.user,
        )
        return Response(ScheduledRunSerializer(scheduled_run).data)


class ScheduledWorkflowPauseView(APIView):
    throttle_scope = "product_write"

    @extend_schema(request=None, responses=ScheduledWorkflowSerializer)
    def post(self, request, workflow_id):
        workflow = get_admin_scheduled_workflow(request.user, workflow_id)
        workflow = set_scheduled_workflow_status(workflow, ScheduledWorkflowStatus.PAUSED)
        log_audit_event(
            action="jobs.scheduled_workflow.pause",
            organization=workflow.organization,
            request=request,
            category="jobs",
            target_entity_type="scheduled_workflow",
            target_entity_id=workflow.id,
        )
        return Response(ScheduledWorkflowSerializer(workflow).data)


class ScheduledWorkflowResumeView(APIView):
    throttle_scope = "product_write"

    @extend_schema(request=None, responses=ScheduledWorkflowSerializer)
    def post(self, request, workflow_id):
        workflow = get_admin_scheduled_workflow(request.user, workflow_id)
        workflow = set_scheduled_workflow_status(workflow, ScheduledWorkflowStatus.ACTIVE)
        log_audit_event(
            action="jobs.scheduled_workflow.resume",
            organization=workflow.organization,
            request=request,
            category="jobs",
            target_entity_type="scheduled_workflow",
            target_entity_id=workflow.id,
        )
        return Response(ScheduledWorkflowSerializer(workflow).data)


class ScheduledRunListView(generics.ListAPIView):
    queryset = ScheduledRun.objects.none()
    serializer_class = ScheduledRunSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ScheduledRun.objects.none()
        workflow = get_admin_scheduled_workflow(self.request.user, self.kwargs["workflow_id"])
        return ScheduledRun.objects.filter(workflow=workflow).select_related("job_run")
