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

