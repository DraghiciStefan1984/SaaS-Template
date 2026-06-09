from django.conf import settings
from django.db import models
from django.utils import timezone


class JobRunStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    RETRYING = "retrying", "Retrying"
    CANCELLED = "cancelled", "Cancelled"


class ScheduledWorkflowStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"


class ScheduleFrequency(models.TextChoices):
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"
    MONTHLY = "monthly", "Monthly"


class ScheduledWorkflowType(models.TextChoices):
    REPORT = "report", "Report"


class ScheduledRunTrigger(models.TextChoices):
    SCHEDULED = "scheduled", "Scheduled"
    MANUAL = "manual", "Manual"


class JobRun(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="job_runs",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_job_runs",
    )
    name = models.CharField(max_length=160)
    task_name = models.CharField(max_length=240)
    status = models.CharField(
        max_length=20,
        choices=JobRunStatus.choices,
        default=JobRunStatus.QUEUED,
    )
    related_entity_type = models.CharField(max_length=120, blank=True)
    related_entity_id = models.CharField(max_length=120, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=3)
    queued_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["task_name"]),
            models.Index(fields=["related_entity_type", "related_entity_id"]),
            models.Index(fields=["queued_at"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.status})"


class ScheduledWorkflow(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="scheduled_workflows",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_scheduled_workflows",
    )
    name = models.CharField(max_length=160)
    workflow_type = models.CharField(
        max_length=40,
        choices=ScheduledWorkflowType.choices,
        default=ScheduledWorkflowType.REPORT,
    )
    status = models.CharField(
        max_length=20,
        choices=ScheduledWorkflowStatus.choices,
        default=ScheduledWorkflowStatus.ACTIVE,
    )
    frequency = models.CharField(max_length=20, choices=ScheduleFrequency.choices)
    timezone = models.CharField(max_length=64, default="UTC")
    config = models.JSONField(default=dict, blank=True)
    next_run_at = models.DateTimeField()
    last_run_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["next_run_at", "id"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["status", "next_run_at"]),
            models.Index(fields=["workflow_type"]),
        ]

    def __str__(self):
        return f"{self.organization} {self.name}"


class ScheduledRun(models.Model):
    workflow = models.ForeignKey(
        ScheduledWorkflow,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    job_run = models.ForeignKey(
        JobRun,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scheduled_runs",
    )
    trigger = models.CharField(max_length=20, choices=ScheduledRunTrigger.choices)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["workflow", "created_at"]),
            models.Index(fields=["trigger", "created_at"]),
        ]

    def __str__(self):
        return f"{self.workflow} {self.trigger}"
