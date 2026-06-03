from django.conf import settings
from django.db import models


class PrivacyRequestStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    QUEUED = "queued", "Queued"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class DataExportScope(models.TextChoices):
    ORGANIZATION = "organization", "Organization"
    ACCOUNT = "account", "Account"


class DataDeletionTarget(models.TextChoices):
    ORGANIZATION = "organization", "Organization"
    ACCOUNT = "account", "Account"


class DataExportRequest(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="data_export_requests",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="data_export_requests",
    )
    scope = models.CharField(
        max_length=30,
        choices=DataExportScope.choices,
        default=DataExportScope.ORGANIZATION,
    )
    status = models.CharField(
        max_length=30,
        choices=PrivacyRequestStatus.choices,
        default=PrivacyRequestStatus.COMPLETED,
    )
    export_payload = models.JSONField(default=dict, blank=True)
    file_path = models.CharField(max_length=500, blank=True)
    error_message = models.TextField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["requested_by", "created_at"]),
            models.Index(fields=["scope"]),
        ]

    def __str__(self):
        return f"{self.organization} export {self.scope} {self.status}"


class DataDeletionRequest(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="data_deletion_requests",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="data_deletion_requests",
    )
    target = models.CharField(
        max_length=30,
        choices=DataDeletionTarget.choices,
        default=DataDeletionTarget.ORGANIZATION,
    )
    status = models.CharField(
        max_length=30,
        choices=PrivacyRequestStatus.choices,
        default=PrivacyRequestStatus.PENDING,
    )
    reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["requested_by", "created_at"]),
            models.Index(fields=["target"]),
        ]

    def __str__(self):
        return f"{self.organization} deletion {self.target} {self.status}"
