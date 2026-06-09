from calendar import monthrange
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.audit.services import log_audit_event
from apps.billing.services import assert_feature_enabled
from apps.usage.services import check_and_record_usage

from .models import (
    JobRun,
    JobRunStatus,
    ScheduledRun,
    ScheduledRunTrigger,
    ScheduledWorkflow,
    ScheduledWorkflowStatus,
    ScheduledWorkflowType,
    ScheduleFrequency,
)

SCHEDULED_REPORTS_FEATURE = "scheduled_reports"
REPORTS_FEATURE = "reports"
GENERATED_REPORTS_USAGE_METRIC = "generated_reports"


def create_job_run(
    *,
    organization,
    created_by=None,
    name,
    task_name,
    related_entity_type="",
    related_entity_id="",
    max_attempts=3,
    metadata=None,
):
    return JobRun.objects.create(
        organization=organization,
        created_by=created_by,
        name=name,
        task_name=task_name,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        max_attempts=max_attempts,
        metadata=metadata or {},
    )


def mark_job_started(job_run):
    job_run.status = JobRunStatus.RUNNING
    job_run.attempts += 1
    job_run.started_at = timezone.now()
    job_run.finished_at = None
    job_run.save(update_fields=["status", "attempts", "started_at", "finished_at", "updated_at"])
    return job_run


def mark_job_succeeded(job_run, metadata=None):
    job_run.status = JobRunStatus.SUCCEEDED
    job_run.finished_at = timezone.now()
    if metadata:
        job_run.metadata = {**job_run.metadata, **metadata}
    job_run.save(update_fields=["status", "finished_at", "metadata", "updated_at"])
    return job_run


def mark_job_failed(job_run, error_message, retryable=True, metadata=None):
    can_retry = retryable and job_run.attempts < job_run.max_attempts
    job_run.status = JobRunStatus.RETRYING if can_retry else JobRunStatus.FAILED
    job_run.last_error = error_message
    job_run.finished_at = timezone.now()
    if metadata:
        job_run.metadata = {**job_run.metadata, **metadata}
    job_run.save(update_fields=["status", "last_error", "finished_at", "metadata", "updated_at"])
    return job_run


def calculate_next_run_at(reference, frequency):
    if frequency == ScheduleFrequency.DAILY:
        return reference + timedelta(days=1)
    if frequency == ScheduleFrequency.WEEKLY:
        return reference + timedelta(days=7)
    if frequency == ScheduleFrequency.MONTHLY:
        next_month = reference.month + 1
        year = reference.year + (1 if next_month == 13 else 0)
        month = 1 if next_month == 13 else next_month
        day = min(reference.day, monthrange(year, month)[1])
        return reference.replace(year=year, month=month, day=day)
    raise ValidationError({"frequency": "Unsupported schedule frequency."})


def next_future_run_at(reference, frequency, now=None):
    now = now or timezone.now()
    candidate = reference
    while candidate <= now:
        candidate = calculate_next_run_at(candidate, frequency)
    return candidate


def create_scheduled_workflow(
    *,
    organization,
    created_by,
    name,
    frequency,
    timezone_name,
    config,
    next_run_at=None,
):
    if not isinstance(config, dict):
        raise ValidationError({"config": "Expected a JSON object."})
    assert_feature_enabled(organization, SCHEDULED_REPORTS_FEATURE)
    assert_feature_enabled(organization, REPORTS_FEATURE)
    next_run_at = next_run_at or calculate_next_run_at(timezone.now(), frequency)
    return ScheduledWorkflow.objects.create(
        organization=organization,
        created_by=created_by,
        name=name,
        workflow_type=ScheduledWorkflowType.REPORT,
        frequency=frequency,
        timezone=timezone_name,
        config=config,
        next_run_at=next_run_at,
    )


@transaction.atomic
def run_scheduled_workflow(workflow, *, trigger, requested_by=None, require_due=False):
    from apps.reports.services import create_report_request

    workflow = ScheduledWorkflow.objects.select_for_update().select_related("organization").get(
        id=workflow.id
    )
    now = timezone.now()
    if (
        workflow.status != ScheduledWorkflowStatus.ACTIVE
        and trigger == ScheduledRunTrigger.SCHEDULED
    ):
        return None
    if require_due and workflow.next_run_at > now:
        return None
    if workflow.workflow_type != ScheduledWorkflowType.REPORT:
        raise ValidationError({"workflow_type": "Unsupported scheduled workflow type."})

    config = workflow.config if isinstance(workflow.config, dict) else {}
    assert_feature_enabled(workflow.organization, SCHEDULED_REPORTS_FEATURE)
    assert_feature_enabled(workflow.organization, REPORTS_FEATURE)
    usage_record = check_and_record_usage(
        workflow.organization,
        GENERATED_REPORTS_USAGE_METRIC,
        source="jobs.run_scheduled_workflow",
        metadata={"scheduled_workflow_id": workflow.id, "trigger": trigger},
    )
    report, job_run = create_report_request(
        organization=workflow.organization,
        created_by=requested_by or workflow.created_by,
        title=config.get("title") or workflow.name,
        template_key=config.get("template_key", ""),
        requested_format=config.get("requested_format", "json"),
        input_payload=config.get("input_payload", {}),
        related_entity_type="scheduled_workflow",
        related_entity_id=str(workflow.id),
    )
    scheduled_run = ScheduledRun.objects.create(
        workflow=workflow,
        job_run=job_run,
        trigger=trigger,
        scheduled_for=workflow.next_run_at if trigger == ScheduledRunTrigger.SCHEDULED else None,
    )
    usage_record.metadata = {
        "scheduled_workflow_id": workflow.id,
        "scheduled_run_id": scheduled_run.id,
        "report_id": report.id,
        "job_run_id": job_run.id,
        "trigger": trigger,
    }
    usage_record.save(update_fields=["metadata"])

    workflow.last_run_at = now
    if trigger == ScheduledRunTrigger.SCHEDULED:
        workflow.next_run_at = next_future_run_at(workflow.next_run_at, workflow.frequency, now=now)
    workflow.save(update_fields=["last_run_at", "next_run_at", "updated_at"])
    log_audit_event(
        action="jobs.scheduled_workflow.run",
        organization=workflow.organization,
        user=requested_by or workflow.created_by,
        category="jobs",
        target_entity_type="scheduled_workflow",
        target_entity_id=workflow.id,
        metadata={
            "trigger": trigger,
            "scheduled_run_id": scheduled_run.id,
            "report_id": report.id,
            "job_run_id": job_run.id,
        },
    )
    return scheduled_run


def set_scheduled_workflow_status(workflow, status):
    workflow.status = status
    if status == ScheduledWorkflowStatus.ACTIVE and workflow.next_run_at <= timezone.now():
        workflow.next_run_at = next_future_run_at(workflow.next_run_at, workflow.frequency)
    workflow.save(update_fields=["status", "next_run_at", "updated_at"])
    return workflow
