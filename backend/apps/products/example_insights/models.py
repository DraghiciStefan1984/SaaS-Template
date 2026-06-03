from django.conf import settings
from django.db import models


class ExampleInsightStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    PLANNED = "planned", "Planned"
    FAILED = "failed", "Failed"


class ExampleInsightRequest(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="example_insight_requests",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="example_insight_requests",
    )
    report = models.ForeignKey(
        "reports.Report",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="example_insight_requests",
    )
    job_run = models.ForeignKey(
        "jobs.JobRun",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="example_insight_requests",
    )
    title = models.CharField(max_length=240)
    status = models.CharField(
        max_length=20,
        choices=ExampleInsightStatus.choices,
        default=ExampleInsightStatus.QUEUED,
    )
    input_payload = models.JSONField(default=dict, blank=True)
    constraints = models.JSONField(default=dict, blank=True)
    ai_execution_plan = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return self.title

