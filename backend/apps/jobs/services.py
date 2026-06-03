from django.utils import timezone

from .models import JobRun, JobRunStatus


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

