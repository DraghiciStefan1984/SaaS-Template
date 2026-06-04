from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from apps.accounts.models import UserAccountStatus
from apps.ai.models import AICallLog, AIModelDecisionLog
from apps.audit.models import AuditLog
from apps.billing.services import get_subscription_for_organization
from apps.integrations.models import (
    IntegrationAccount,
    IntegrationAccountStatus,
    IntegrationCredential,
    IntegrationSyncLog,
)
from apps.jobs.models import JobRun
from apps.notifications.models import NotificationDeliveryLog, NotificationPreference
from apps.products.example_insights.models import ExampleInsightRequest
from apps.reports.models import Report, ReportArtifact
from apps.usage.models import UsageRecord
from apps.usage.services import usage_summary_for_organization

from .models import (
    DataDeletionRequest,
    DataDeletionTarget,
    DataExportRequest,
    DataExportScope,
    PrivacyRequestStatus,
)


def _iso(value):
    return value.isoformat() if value else None


def _user_payload(user):
    if user is None:
        return None
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "account_status": user.account_status,
    }


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
        "membership_records": [
            {
                "id": membership.id,
                "user": _user_payload(membership.user),
                "invited_email": membership.invited_email,
                "role": membership.role,
                "status": membership.status,
                "created_at": _iso(membership.created_at),
                "updated_at": _iso(membership.updated_at),
            }
            for membership in organization.memberships.select_related("user").order_by("id")
        ],
        "subscription": {
            "status": subscription.status if subscription else "",
            "plan_slug": subscription.plan.slug if subscription and subscription.plan else "",
            "stripe_customer_id": subscription.stripe_customer_id if subscription else "",
            "stripe_subscription_id": subscription.stripe_subscription_id if subscription else "",
            "cancel_at_period_end": subscription.cancel_at_period_end if subscription else False,
            "current_period_start": (
                _iso(subscription.current_period_start) if subscription else None
            ),
            "current_period_end": _iso(subscription.current_period_end) if subscription else None,
        },
        "usage": usage_summary_for_organization(organization),
        "usage_records": [
            {
                "id": record.id,
                "metric_name": record.metric_name,
                "quantity": str(record.quantity),
                "source": record.source,
                "product_scope": record.product_scope,
                "period_start": record.period_start.isoformat(),
                "period_end": record.period_end.isoformat(),
                "metadata": record.metadata,
                "created_at": _iso(record.created_at),
            }
            for record in UsageRecord.objects.filter(organization=organization).order_by("id")
        ],
        "reports": {item["status"]: item["count"] for item in report_counts},
        "report_records": [
            {
                "id": report.id,
                "created_by": _user_payload(report.created_by),
                "template_key": report.template.key if report.template else "",
                "title": report.title,
                "status": report.status,
                "requested_format": report.requested_format,
                "input_payload": report.input_payload,
                "result_summary": report.result_summary,
                "error_message": report.error_message,
                "related_entity_type": report.related_entity_type,
                "related_entity_id": report.related_entity_id,
                "completed_at": _iso(report.completed_at),
                "created_at": _iso(report.created_at),
                "updated_at": _iso(report.updated_at),
                "artifacts": [
                    {
                        "id": artifact.id,
                        "format": artifact.format,
                        "storage_backend": artifact.storage_backend,
                        "file_path": artifact.file_path,
                        "external_url": artifact.external_url,
                        "content": artifact.content,
                        "checksum": artifact.checksum,
                        "metadata": artifact.metadata,
                        "created_at": _iso(artifact.created_at),
                    }
                    for artifact in ReportArtifact.objects.filter(report=report).order_by("id")
                ],
            }
            for report in Report.objects.filter(organization=organization)
            .select_related("created_by", "template")
            .order_by("id")
        ],
        "product_records": {
            "example_insight_requests": [
                {
                    "id": request.id,
                    "created_by": _user_payload(request.created_by),
                    "report_id": request.report_id,
                    "job_run_id": request.job_run_id,
                    "title": request.title,
                    "status": request.status,
                    "input_payload": request.input_payload,
                    "constraints": request.constraints,
                    "ai_execution_plan": request.ai_execution_plan,
                    "error_message": request.error_message,
                    "created_at": _iso(request.created_at),
                    "updated_at": _iso(request.updated_at),
                }
                for request in ExampleInsightRequest.objects.filter(
                    organization=organization
                )
                .select_related("created_by")
                .order_by("id")
            ],
        },
        "jobs": {item["status"]: item["count"] for item in job_counts},
        "job_records": [
            {
                "id": job.id,
                "created_by": _user_payload(job.created_by),
                "name": job.name,
                "task_name": job.task_name,
                "status": job.status,
                "attempts": job.attempts,
                "max_attempts": job.max_attempts,
                "last_error": job.last_error,
                "related_entity_type": job.related_entity_type,
                "related_entity_id": job.related_entity_id,
                "metadata": job.metadata,
                "started_at": _iso(job.started_at),
                "completed_at": _iso(job.completed_at),
                "created_at": _iso(job.created_at),
                "updated_at": _iso(job.updated_at),
            }
            for job in JobRun.objects.filter(organization=organization)
            .select_related("created_by")
            .order_by("id")
        ],
        "notification_preferences": [
            {
                "id": preference.id,
                "user": _user_payload(preference.user),
                "event": preference.event,
                "channel": preference.channel,
                "is_enabled": preference.is_enabled,
                "config": preference.config,
                "created_at": _iso(preference.created_at),
                "updated_at": _iso(preference.updated_at),
            }
            for preference in NotificationPreference.objects.filter(
                organization=organization
            )
            .select_related("user")
            .order_by("id")
        ],
        "notification_delivery_logs": [
            {
                "id": log.id,
                "user": _user_payload(log.user),
                "event": log.event,
                "channel": log.channel,
                "status": log.status,
                "recipient": log.recipient,
                "subject": log.subject,
                "payload": log.payload,
                "provider": log.provider,
                "provider_message_id": log.provider_message_id,
                "error_message": log.error_message,
                "metadata": log.metadata,
                "sent_at": _iso(log.sent_at),
                "created_at": _iso(log.created_at),
                "updated_at": _iso(log.updated_at),
            }
            for log in NotificationDeliveryLog.objects.filter(organization=organization)
            .select_related("user")
            .order_by("id")
        ],
        "integration_accounts": [
            {
                "id": account.id,
                "provider_slug": account.provider.slug,
                "external_account_id": account.external_account_id,
                "display_name": account.display_name,
                "status": account.status,
                "scopes": account.scopes,
                "connected_by": _user_payload(account.connected_by),
                "metadata": account.metadata,
                "has_credential": hasattr(account, "credential"),
                "last_sync_at": _iso(account.last_sync_at),
                "created_at": _iso(account.created_at),
                "updated_at": _iso(account.updated_at),
                "sync_logs": [
                    {
                        "id": sync_log.id,
                        "action": sync_log.action,
                        "status": sync_log.status,
                        "started_at": _iso(sync_log.started_at),
                        "completed_at": _iso(sync_log.completed_at),
                        "error_message": sync_log.error_message,
                        "external_request_id": sync_log.external_request_id,
                        "rate_limit_reset_at": _iso(sync_log.rate_limit_reset_at),
                        "retry_count": sync_log.retry_count,
                        "metadata": sync_log.metadata,
                        "created_at": _iso(sync_log.created_at),
                    }
                    for sync_log in IntegrationSyncLog.objects.filter(
                        integration_account=account
                    ).order_by("id")
                ],
            }
            for account in IntegrationAccount.objects.filter(organization=organization)
            .select_related("provider", "connected_by")
            .order_by("id")
        ],
        "ai_decision_logs": [
            {
                "id": decision.id,
                "user": _user_payload(decision.user),
                "task_key": decision.task_key,
                "selected_strategy": decision.selected_strategy,
                "selected_provider_slug": (
                    decision.selected_provider.slug if decision.selected_provider else ""
                ),
                "selected_model": decision.selected_model,
                "fallback_strategy": decision.fallback_strategy,
                "fallback_provider_slug": (
                    decision.fallback_provider.slug if decision.fallback_provider else ""
                ),
                "fallback_model": decision.fallback_model,
                "requires_human_review": decision.requires_human_review,
                "decision_reason": decision.decision_reason,
                "constraints": decision.constraints,
                "input_summary": decision.input_summary,
                "metadata": decision.metadata,
                "created_at": _iso(decision.created_at),
            }
            for decision in AIModelDecisionLog.objects.filter(organization=organization)
            .select_related("user", "selected_provider", "fallback_provider")
            .order_by("id")
        ],
        "ai_call_logs": [
            {
                "id": call.id,
                "user": _user_payload(call.user),
                "provider_slug": call.provider.slug,
                "prompt_key": call.prompt_template.key if call.prompt_template else "",
                "prompt_version": call.prompt_version,
                "model": call.model,
                "status": call.status,
                "related_entity_type": call.related_entity_type,
                "related_entity_id": call.related_entity_id,
                "request_hash": call.request_hash,
                "input_tokens": call.input_tokens,
                "output_tokens": call.output_tokens,
                "total_tokens": call.total_tokens,
                "estimated_cost": str(call.estimated_cost),
                "latency_ms": call.latency_ms,
                "response_payload": call.response_payload,
                "error_message": call.error_message,
                "metadata": call.metadata,
                "created_at": _iso(call.created_at),
            }
            for call in AICallLog.objects.filter(organization=organization)
            .select_related("user", "provider", "prompt_template")
            .order_by("id")
        ],
        "audit_logs": [
            {
                "id": log.id,
                "user": _user_payload(log.user),
                "action": log.action,
                "category": log.category,
                "status": log.status,
                "target_entity_type": log.target_entity_type,
                "target_entity_id": log.target_entity_id,
                "request_id": log.request_id,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "metadata": log.metadata,
                "created_at": _iso(log.created_at),
            }
            for log in AuditLog.objects.filter(organization=organization)
            .select_related("user")
            .order_by("id")
        ],
    }


def build_account_export_payload(*, organization, user):
    return {
        "schema_version": 1,
        "generated_at": timezone.now().isoformat(),
        "retention": {
            "data_retention_days": settings.DATA_RETENTION_DAYS,
            "audit_log_retention_days": settings.AUDIT_LOG_RETENTION_DAYS,
        },
        "account": _user_payload(user),
        "selected_organization": {
            "id": organization.id,
            "name": organization.name,
        },
        "membership_records": [
            {
                "id": membership.id,
                "organization": {
                    "id": membership.organization_id,
                    "name": membership.organization.name,
                },
                "role": membership.role,
                "status": membership.status,
                "joined_at": _iso(membership.joined_at),
                "created_at": _iso(membership.created_at),
                "updated_at": _iso(membership.updated_at),
            }
            for membership in user.organization_memberships.select_related(
                "organization"
            ).order_by("organization_id", "id")
        ],
        "created_reports": [
            {
                "id": report.id,
                "organization_id": report.organization_id,
                "template_key": report.template.key if report.template else "",
                "title": report.title,
                "status": report.status,
                "requested_format": report.requested_format,
                "input_payload": report.input_payload,
                "result_summary": report.result_summary,
                "error_message": report.error_message,
                "created_at": _iso(report.created_at),
                "updated_at": _iso(report.updated_at),
            }
            for report in Report.objects.filter(created_by=user)
            .select_related("template")
            .order_by("id")
        ],
        "created_example_insight_requests": [
            {
                "id": request.id,
                "organization_id": request.organization_id,
                "report_id": request.report_id,
                "job_run_id": request.job_run_id,
                "title": request.title,
                "status": request.status,
                "input_payload": request.input_payload,
                "constraints": request.constraints,
                "ai_execution_plan": request.ai_execution_plan,
                "error_message": request.error_message,
                "created_at": _iso(request.created_at),
                "updated_at": _iso(request.updated_at),
            }
            for request in ExampleInsightRequest.objects.filter(created_by=user).order_by("id")
        ],
    }


def _privacy_export_expires_at():
    return timezone.now() + timedelta(days=settings.DATA_RETENTION_DAYS)


def create_data_export_request(*, organization, requested_by, scope):
    export_payload = (
        build_account_export_payload(organization=organization, user=requested_by)
        if scope == DataExportScope.ACCOUNT
        else build_organization_export_payload(organization)
    )
    return DataExportRequest.objects.create(
        organization=organization,
        requested_by=requested_by,
        scope=scope,
        status=PrivacyRequestStatus.COMPLETED,
        export_payload=export_payload,
        expires_at=_privacy_export_expires_at(),
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


def _anonymize_user(user):
    if user is None:
        return
    user.email = f"deleted-user-{user.id}@deleted.local"
    user.name = ""
    user.is_email_verified = False
    user.account_status = UserAccountStatus.SUSPENDED
    user.is_active = False
    user.set_unusable_password()
    user.save(
        update_fields=[
            "email",
            "name",
            "is_email_verified",
            "account_status",
            "is_active",
            "password",
        ]
    )


def _scrub_data_exports(queryset):
    queryset.update(
        export_payload={"privacy_deleted": True},
        file_path="",
        error_message="",
        expires_at=timezone.now(),
    )


def _anonymize_organization(organization):
    organization.name = f"Deleted organization {organization.id}"
    organization.timezone = "UTC"
    organization.default_language = "en"
    organization.save(update_fields=["name", "timezone", "default_language", "updated_at"])

    if hasattr(organization, "subscription"):
        subscription = organization.subscription
        subscription.stripe_customer_id = ""
        subscription.stripe_subscription_id = ""
        subscription.metadata = {"privacy_deleted": True}
        subscription.cancel_at_period_end = True
        subscription.save(
            update_fields=[
                "stripe_customer_id",
                "stripe_subscription_id",
                "metadata",
                "cancel_at_period_end",
                "updated_at",
            ]
        )

    organization.memberships.update(
        invited_email="",
        status="disabled",
    )
    UsageRecord.objects.filter(organization=organization).update(metadata={})
    Report.objects.filter(organization=organization).update(
        title="Deleted report",
        input_payload={},
        result_summary={},
        error_message="",
        related_entity_type="",
        related_entity_id="",
    )
    ReportArtifact.objects.filter(report__organization=organization).update(
        file_path="",
        external_url="",
        content={},
        checksum="",
        metadata={},
    )
    ExampleInsightRequest.objects.filter(organization=organization).update(
        title="Deleted insight request",
        input_payload={},
        constraints={},
        ai_execution_plan={},
        error_message="",
    )
    JobRun.objects.filter(organization=organization).update(
        name="Deleted job",
        related_entity_type="",
        related_entity_id="",
        last_error="",
        metadata={},
    )
    NotificationPreference.objects.filter(organization=organization).update(config={})
    NotificationDeliveryLog.objects.filter(organization=organization).update(
        recipient="",
        subject="",
        payload={},
        provider_message_id="",
        error_message="",
        metadata={},
    )
    IntegrationCredential.objects.filter(
        integration_account__organization=organization
    ).delete()
    IntegrationAccount.objects.filter(organization=organization).update(
        external_account_id="",
        display_name="",
        status=IntegrationAccountStatus.DISCONNECTED,
        scopes=[],
        metadata={},
        last_sync_at=None,
    )
    IntegrationSyncLog.objects.filter(integration_account__organization=organization).update(
        error_message="",
        external_request_id="",
        metadata={},
    )
    AIModelDecisionLog.objects.filter(organization=organization).update(
        selected_model="",
        fallback_model="",
        decision_reason="Deleted by privacy request.",
        constraints={},
        input_summary={},
        metadata={},
    )
    AICallLog.objects.filter(organization=organization).update(
        related_entity_type="",
        related_entity_id="",
        request_hash="0" * 64,
        response_payload={},
        error_message="",
        metadata={},
    )
    AuditLog.objects.filter(organization=organization).update(
        ip_address=None,
        user_agent="",
        request_id="",
        metadata={},
    )
    _scrub_data_exports(DataExportRequest.objects.filter(organization=organization))


def _anonymize_account(deletion_request):
    user = deletion_request.requested_by
    if user is None:
        return
    user.organization_memberships.update(
        invited_email="",
        status="disabled",
    )
    _scrub_data_exports(DataExportRequest.objects.filter(requested_by=user))
    _anonymize_user(user)


@transaction.atomic
def execute_data_deletion_request(deletion_request):
    if deletion_request.status == PrivacyRequestStatus.COMPLETED:
        return deletion_request

    deletion_request.status = PrivacyRequestStatus.PROCESSING
    deletion_request.save(update_fields=["status", "updated_at"])

    if deletion_request.target == DataDeletionTarget.ORGANIZATION:
        _anonymize_organization(deletion_request.organization)
    elif deletion_request.target == DataDeletionTarget.ACCOUNT:
        _anonymize_account(deletion_request)

    deletion_request.status = PrivacyRequestStatus.COMPLETED
    deletion_request.completed_at = timezone.now()
    deletion_request.metadata = {
        **deletion_request.metadata,
        "executed_at": deletion_request.completed_at.isoformat(),
        "executor": "template_privacy_executor",
    }
    deletion_request.save(update_fields=["status", "completed_at", "metadata", "updated_at"])
    return deletion_request
