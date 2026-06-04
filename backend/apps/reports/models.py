from django.conf import settings
from django.db import models


class ReportStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class ReportFormat(models.TextChoices):
    JSON = "json", "JSON"
    HTML = "html", "HTML"
    PDF = "pdf", "PDF"
    CSV = "csv", "CSV"
    DOCX = "docx", "DOCX"


class ReportTemplate(models.Model):
    key = models.SlugField(unique=True)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    default_format = models.CharField(
        max_length=20,
        choices=ReportFormat.choices,
        default=ReportFormat.JSON,
    )
    ai_task_profile = models.ForeignKey(
        "ai.AITaskProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="report_templates",
    )
    config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]
        indexes = [
            models.Index(fields=["key", "is_active"]),
        ]

    def __str__(self):
        return self.key


class Report(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="reports",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_reports",
    )
    template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports",
    )
    title = models.CharField(max_length=240)
    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.QUEUED,
    )
    requested_format = models.CharField(
        max_length=20,
        choices=ReportFormat.choices,
        default=ReportFormat.JSON,
    )
    input_payload = models.JSONField(default=dict, blank=True)
    result_summary = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    related_entity_type = models.CharField(max_length=120, blank=True)
    related_entity_id = models.CharField(max_length=120, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["related_entity_type", "related_entity_id"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return self.title


class ReportArtifact(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="artifacts")
    format = models.CharField(max_length=20, choices=ReportFormat.choices)
    storage_backend = models.CharField(max_length=40, default="database")
    file_path = models.CharField(max_length=500, blank=True)
    external_url = models.URLField(blank=True)
    content = models.JSONField(default=dict, blank=True)
    checksum = models.CharField(max_length=128, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["report", "format"]),
            models.Index(fields=["storage_backend"]),
        ]

    def __str__(self):
        return f"{self.report_id} {self.format}"

