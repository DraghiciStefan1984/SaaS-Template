from django.db import transaction
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_audit_event
from apps.billing.services import assert_feature_enabled
from apps.organizations.models import MembershipStatus, Organization
from apps.organizations.permissions import (
    ADMIN_ROLES,
    require_membership,
    require_organization_role,
)
from apps.usage.services import check_and_record_usage

from .models import Report, ReportArtifact, ReportTemplate
from .serializers import (
    ReportArtifactSerializer,
    ReportCreateSerializer,
    ReportSerializer,
    ReportSummarySerializer,
    ReportTemplateSerializer,
)
from .services import create_report_request, report_artifact_download

REPORTS_FEATURE = "reports"
REPORTS_USAGE_METRIC = "generated_reports"


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


class ReportTemplateListView(generics.ListAPIView):
    serializer_class = ReportTemplateSerializer
    pagination_class = None

    def get_queryset(self):
        return ReportTemplate.objects.filter(is_active=True).order_by("key")


class ReportListCreateView(generics.ListCreateAPIView):
    queryset = Report.objects.none()
    serializer_class = ReportSummarySerializer
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
        request=ReportCreateSerializer,
        responses=ReportSummarySerializer,
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(request=ReportCreateSerializer, responses=ReportSummarySerializer)
    def post(self, request, *args, **kwargs):
        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        organization = get_member_organization(request.user, data["organization_id"])
        with transaction.atomic():
            assert_feature_enabled(organization, REPORTS_FEATURE)
            usage_record = check_and_record_usage(
                organization,
                REPORTS_USAGE_METRIC,
                source="reports.create_request",
                metadata={"status": "reserved"},
            )
            report, job_run = create_report_request(
                organization=organization,
                created_by=request.user,
                title=data["title"],
                template_key=data.get("template_key", ""),
                requested_format=data.get("requested_format", "json"),
                input_payload=data.get("input_payload", {}),
                related_entity_type=data.get("related_entity_type", ""),
                related_entity_id=data.get("related_entity_id", ""),
            )
            usage_record.metadata = {"report_id": report.id, "job_run_id": job_run.id}
            usage_record.save(update_fields=["metadata"])
        body = ReportSummarySerializer(report).data
        body["job_run_id"] = job_run.id
        log_audit_event(
            action="reports.request.created",
            organization=organization,
            request=request,
            category="reports",
            target_entity_type="report",
            target_entity_id=report.id,
            metadata={"job_run_id": job_run.id, "template_key": data.get("template_key", "")},
        )
        return Response(body, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Report.objects.none()

        organization = get_member_organization(
            self.request.user,
            self.request.query_params.get("organization_id"),
        )
        return (
            Report.objects.filter(organization=organization)
            .select_related("created_by", "template", "template__ai_task_profile")
            .order_by("-created_at", "-id")
        )


class ReportDetailView(generics.RetrieveAPIView):
    serializer_class = ReportSerializer

    def get_queryset(self):
        queryset = Report.objects.filter(
            organization__memberships__user=self.request.user,
            organization__memberships__status=MembershipStatus.ACTIVE,
        ).select_related("organization", "created_by", "template", "template__ai_task_profile")
        report = queryset.filter(id=self.kwargs["pk"]).first()
        if report is not None:
            require_organization_role(self.request.user, report.organization, ADMIN_ROLES)
        return queryset


class ReportArtifactListView(generics.ListAPIView):
    queryset = ReportArtifact.objects.none()
    serializer_class = ReportArtifactSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ReportArtifact.objects.none()

        report = get_object_or_404(
            Report.objects.filter(
                organization__memberships__user=self.request.user,
                organization__memberships__status=MembershipStatus.ACTIVE,
            )
            .select_related("organization")
            .distinct(),
            id=self.kwargs["report_id"],
        )
        require_organization_role(self.request.user, report.organization, ADMIN_ROLES)
        return ReportArtifact.objects.filter(report=report)


class ReportArtifactDownloadView(APIView):
    throttle_scope = "expensive_action"

    @extend_schema(
        request=None,
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.BINARY,
                description="Organization-authorized report artifact download.",
            )
        },
    )
    def get(self, request, report_id, artifact_id):
        artifact = get_object_or_404(
            ReportArtifact.objects.select_related("report", "report__organization").filter(
                report_id=report_id,
                report__organization__memberships__user=request.user,
                report__organization__memberships__status=MembershipStatus.ACTIVE,
            ),
            id=artifact_id,
        )
        require_organization_role(request.user, artifact.report.organization, ADMIN_ROLES)
        download = report_artifact_download(artifact)
        if download["kind"] == "file":
            response = FileResponse(
                download["path"].open("rb"),
                content_type=download["content_type"],
                as_attachment=True,
                filename=download["filename"],
            )
        else:
            response = HttpResponse(download["content"], content_type=download["content_type"])
            response["Content-Disposition"] = f'attachment; filename="{download["filename"]}"'
        log_audit_event(
            action="reports.artifact.downloaded",
            organization=artifact.report.organization,
            request=request,
            category="reports",
            target_entity_type="report_artifact",
            target_entity_id=artifact.id,
            metadata={"report_id": artifact.report_id, "storage_backend": artifact.storage_backend},
        )
        return response
