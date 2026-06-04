from celery import shared_task

from apps.ai.services import select_ai_execution_plan
from apps.jobs.models import JobRun, JobRunStatus
from apps.jobs.services import mark_job_failed, mark_job_started, mark_job_succeeded
from apps.notifications.services import send_report_ready_notification

from .models import Report
from .services import (
    create_report_artifact,
    mark_report_failed,
    mark_report_retrying,
    mark_report_running,
    mark_report_succeeded,
)


@shared_task(bind=True, name="apps.reports.tasks.generate_report_task")
def generate_report_task(self, report_id, job_run_id=None):
    report = Report.objects.select_related("organization", "created_by", "template").get(
        id=report_id
    )
    job_run = JobRun.objects.filter(id=job_run_id).first() if job_run_id else None
    if job_run:
        mark_job_started(job_run)

    try:
        mark_report_running(report)
        ai_task_key = (
            report.template.ai_task_profile.key
            if report.template and report.template.ai_task_profile
            else "recurring_ai_report"
        )
        execution_plan = select_ai_execution_plan(
            organization=report.organization,
            user=report.created_by,
            task_key=ai_task_key,
            input_payload=report.input_payload,
            constraints=report.input_payload.get("ai_constraints", {}),
            metadata={"report_id": report.id},
            log_decision=True,
        )
        artifact = create_report_artifact(
            report=report,
            format=report.requested_format,
            content={
                "status": "placeholder",
                "execution_plan": execution_plan,
                "message": "Product-specific report rendering should replace this artifact.",
            },
            metadata={"generated_by": "template_placeholder"},
        )
        mark_report_succeeded(
            report,
            result_summary={
                "artifact_id": artifact.id,
                "strategy": execution_plan["strategy"],
                "provider_slug": execution_plan["provider_slug"],
            },
        )
        send_report_ready_notification(report)
        if job_run:
            mark_job_succeeded(
                job_run,
                metadata={"report_id": report.id, "artifact_id": artifact.id},
            )
        return {"report_id": report.id, "artifact_id": artifact.id}
    except Exception as exc:
        failed_job = None
        if job_run:
            failed_job = mark_job_failed(job_run, str(exc), retryable=True)
        if failed_job and failed_job.status == JobRunStatus.RETRYING:
            mark_report_retrying(report, str(exc))
            raise self.retry(exc=exc, countdown=30) from exc
        mark_report_failed(report, str(exc))
        raise
