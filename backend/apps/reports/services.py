from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.jobs.services import create_job_run

from .models import Report, ReportArtifact, ReportStatus, ReportTemplate


def get_report_template(template_key):
    if not template_key:
        return None
    return ReportTemplate.objects.filter(key=template_key, is_active=True).first()


def create_report_request(
    *,
    organization,
    created_by,
    title,
    template_key="",
    requested_format="json",
    input_payload=None,
    related_entity_type="",
    related_entity_id="",
):
    template = get_report_template(template_key)
    if template_key and template is None:
        raise ValidationError({"template_key": "Unknown or inactive report template."})
    input_payload = input_payload or {}
    if not isinstance(input_payload, dict):
        raise ValidationError({"input_payload": "Expected a JSON object."})
    if template is not None and requested_format == "":
        requested_format = template.default_format

    report = Report.objects.create(
        organization=organization,
        created_by=created_by,
        template=template,
        title=title,
        requested_format=requested_format or "json",
        input_payload=input_payload,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
    )
    job_run = create_report_generation_job(report, created_by=created_by)
    return report, job_run


def create_report_generation_job(report, created_by=None):
    job_run = create_job_run(
        organization=report.organization,
        created_by=created_by,
        name="Generate report",
        task_name="apps.reports.tasks.generate_report_task",
        related_entity_type="report",
        related_entity_id=str(report.id),
        metadata={
            "report_id": report.id,
            "template_key": report.template.key if report.template else "",
        },
    )
    transaction.on_commit(lambda: enqueue_report_generation_job(report, job_run))
    return job_run


def enqueue_report_generation_job(report, job_run):
    from .tasks import generate_report_task

    task_result = generate_report_task.delay(report.id, job_run.id)
    job_run.refresh_from_db(fields=["metadata"])
    job_run.metadata = {**job_run.metadata, "celery_task_id": task_result.id}
    job_run.save(update_fields=["metadata", "updated_at"])
    return task_result


def mark_report_running(report):
    report.status = ReportStatus.RUNNING
    report.save(update_fields=["status", "updated_at"])
    return report


def mark_report_succeeded(report, result_summary=None):
    report.status = ReportStatus.SUCCEEDED
    report.result_summary = result_summary or report.result_summary
    report.error_message = ""
    report.completed_at = timezone.now()
    report.save(
        update_fields=[
            "status",
            "result_summary",
            "error_message",
            "completed_at",
            "updated_at",
        ]
    )
    return report


def mark_report_retrying(report, error_message):
    report.status = ReportStatus.QUEUED
    report.error_message = error_message
    report.completed_at = None
    report.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
    return report


def mark_report_failed(report, error_message):
    report.status = ReportStatus.FAILED
    report.error_message = error_message
    report.completed_at = timezone.now()
    report.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
    return report


def create_report_artifact(
    *,
    report,
    format,
    content=None,
    storage_backend="database",
    file_path="",
    external_url="",
    checksum="",
    metadata=None,
):
    return ReportArtifact.objects.create(
        report=report,
        format=format,
        content=content or {},
        storage_backend=storage_backend,
        file_path=file_path,
        external_url=external_url,
        checksum=checksum,
        metadata=metadata or {},
    )
