from django.conf import settings
from django.db.models import Count
from django.utils import timezone

from apps.billing.services import get_subscription_for_organization
from apps.jobs.models import JobRun
from apps.reports.models import Report
from apps.usage.services import usage_summary_for_organization

from .models import DataDeletionRequest, DataExportRequest, PrivacyRequestStatus


def build_organization_export_payload(organization):
    subscription = get_subscription_for_organization(organization)
    report_counts = Report.objects.filter(organization=organization).values("status").annotate(
        count=Count("id")
    )
    job_counts = JobRun.objects.filter(organization=organization).values("status").annotate(
        count=Count("id")
    )

    return {
        "schema_version": 1,
        "generated_at": timezone.now().isoformat(),
        "retention": {
            "data_retention_days": settings.DATA_RETENTION_DAYS,
            "audit_log_retention_days": settings.AUDIT_LOG_RETENTION_DAYS,
        },
        "organization": {
            "id": organization.id,
            "name": organization.name,
            "timezone": organization.timezone,
            "default_language": organization.default_language,
            "created_at": organization.created_at.isoformat(),
        },
        "owner": {
            "id": organization.owner_id,
            "email": organization.owner.email,
        },
        "memberships": {
            "active_count": organization.memberships.filter(status="active").count(),
            "invited_count": organization.memberships.filter(status="invited").count(),
        },
        "subscription": {
            "status": subscription.status if subscription else "",
            "plan_slug": subscription.plan.slug if subscription and subscription.plan else "",
        },
        "usage": usage_summary_for_organization(organization),
        "reports": {item["status"]: item["count"] for item in report_counts},
        "jobs": {item["status"]: item["count"] for item in job_counts},
    }


def create_data_export_request(*, organization, requested_by, scope):
    return DataExportRequest.objects.create(
        organization=organization,
        requested_by=requested_by,
        scope=scope,
        status=PrivacyRequestStatus.COMPLETED,
        export_payload=build_organization_export_payload(organization),
        completed_at=timezone.now(),
    )


def create_data_deletion_request(*, organization, requested_by, target, reason="", metadata=None):
    return DataDeletionRequest.objects.create(
        organization=organization,
        requested_by=requested_by,
        target=target,
        reason=reason,
        metadata=metadata or {},
        status=PrivacyRequestStatus.PENDING,
    )
