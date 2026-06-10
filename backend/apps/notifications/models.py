from django.conf import settings
from django.db import models
from django.utils import timezone


class NotificationChannel(models.TextChoices):
    EMAIL = "email", "Email"
    IN_APP = "in_app", "In-app"
    WEBHOOK = "webhook", "Webhook"


class NotificationEvent(models.TextChoices):
    REPORT_READY = "report_ready", "Report ready"
    REPORT_FAILED = "report_failed", "Report failed"
    INVITE_MEMBER = "invite_member", "Invite member"
    BILLING_EVENT = "billing_event", "Billing event"
    SYSTEM_ALERT = "system_alert", "System alert"


class NotificationDeliveryStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"
    SKIPPED = "skipped", "Skipped"


class InAppNotification(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="in_app_notifications",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="in_app_notifications",
    )
    event = models.CharField(max_length=40, choices=NotificationEvent.choices)
    title = models.CharField(max_length=240)
    message = models.TextField(blank=True)
    target_url = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["organization", "user", "is_read"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user} {self.event}"

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])
        return self


class NotificationPreference(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notification_preferences",
    )
    event = models.CharField(max_length=40, choices=NotificationEvent.choices)
    channel = models.CharField(max_length=20, choices=NotificationChannel.choices)
    is_enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organization_id", "event", "channel", "user_id"]
        indexes = [
            models.Index(fields=["organization", "event", "channel"]),
            models.Index(fields=["user", "event"]),
        ]

    def __str__(self):
        return f"{self.organization} {self.event} {self.channel}"


class NotificationDeliveryLog(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="notification_delivery_logs",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notification_delivery_logs",
    )
    event = models.CharField(max_length=40, choices=NotificationEvent.choices)
    channel = models.CharField(max_length=20, choices=NotificationChannel.choices)
    status = models.CharField(
        max_length=20,
        choices=NotificationDeliveryStatus.choices,
        default=NotificationDeliveryStatus.QUEUED,
    )
    recipient = models.CharField(max_length=255, blank=True)
    subject = models.CharField(max_length=240, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    provider = models.CharField(max_length=80, blank=True)
    provider_message_id = models.CharField(max_length=160, blank=True)
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["organization", "event", "channel"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["recipient"]),
        ]

    def __str__(self):
        return f"{self.event} {self.channel} {self.status}"

    def mark_sent(self, provider_message_id=""):
        self.status = NotificationDeliveryStatus.SENT
        self.provider_message_id = provider_message_id
        self.sent_at = timezone.now()
        self.save(update_fields=["status", "provider_message_id", "sent_at", "updated_at"])
        return self

    def mark_failed(self, error_message):
        self.status = NotificationDeliveryStatus.FAILED
        self.error_message = error_message
        self.save(update_fields=["status", "error_message", "updated_at"])
        return self

    def mark_skipped(self, reason):
        self.status = NotificationDeliveryStatus.SKIPPED
        self.error_message = reason
        self.save(update_fields=["status", "error_message", "updated_at"])
        return self
