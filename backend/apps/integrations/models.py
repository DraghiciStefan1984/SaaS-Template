from django.conf import settings
from django.db import models


class ProviderAuthType(models.TextChoices):
    OAUTH2 = "oauth2", "OAuth 2"
    API_KEY = "api_key", "API key"
    NONE = "none", "None"


class ProviderStatus(models.TextChoices):
    AVAILABLE = "available", "Available"
    BETA = "beta", "Beta"
    DISABLED = "disabled", "Disabled"


class IntegrationAccountStatus(models.TextChoices):
    CONNECTED = "connected", "Connected"
    EXPIRED = "expired", "Expired"
    DISCONNECTED = "disconnected", "Disconnected"
    ERROR = "error", "Error"


class CredentialType(models.TextChoices):
    OAUTH_TOKEN = "oauth_token", "OAuth token"
    API_KEY = "api_key", "API key"
    BEARER_TOKEN = "bearer_token", "Bearer token"


class SyncLogStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    RATE_LIMITED = "rate_limited", "Rate limited"


class IntegrationProvider(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    category = models.CharField(max_length=120)
    auth_type = models.CharField(max_length=20, choices=ProviderAuthType.choices)
    scopes = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=20,
        choices=ProviderStatus.choices,
        default=ProviderStatus.AVAILABLE,
    )
    feature_flags = models.JSONField(default=dict, blank=True)
    config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["auth_type"]),
        ]

    def __str__(self):
        return self.name


class IntegrationAccount(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="integration_accounts",
    )
    provider = models.ForeignKey(
        IntegrationProvider,
        on_delete=models.PROTECT,
        related_name="accounts",
    )
    external_account_id = models.CharField(max_length=255, blank=True)
    display_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=IntegrationAccountStatus.choices,
        default=IntegrationAccountStatus.CONNECTED,
    )
    scopes = models.JSONField(default=list, blank=True)
    connected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="connected_integrations",
    )
    metadata = models.JSONField(default=dict, blank=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organization_id", "provider__name", "display_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "provider", "external_account_id"],
                name="unique_integration_account_per_external_resource",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["provider", "status"]),
            models.Index(fields=["external_account_id"]),
        ]

    def __str__(self):
        return self.display_name or f"{self.provider} connection"


class IntegrationCredential(models.Model):
    integration_account = models.OneToOneField(
        IntegrationAccount,
        on_delete=models.CASCADE,
        related_name="credential",
    )
    credential_type = models.CharField(max_length=30, choices=CredentialType.choices)
    encrypted_payload = models.TextField()
    expires_at = models.DateTimeField(null=True, blank=True)
    refresh_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["integration_account_id"]

    def __str__(self):
        return f"{self.integration_account} credential"


class IntegrationSyncLog(models.Model):
    integration_account = models.ForeignKey(
        IntegrationAccount,
        on_delete=models.CASCADE,
        related_name="sync_logs",
    )
    action = models.CharField(max_length=120)
    status = models.CharField(
        max_length=20,
        choices=SyncLogStatus.choices,
        default=SyncLogStatus.PENDING,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    external_request_id = models.CharField(max_length=255, blank=True)
    rate_limit_reset_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["integration_account", "status"]),
            models.Index(fields=["action", "status"]),
            models.Index(fields=["external_request_id"]),
        ]

    def __str__(self):
        return f"{self.integration_account} {self.action} {self.status}"

