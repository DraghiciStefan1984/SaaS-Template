from django.db import models


class SubscriptionStatus(models.TextChoices):
    FREE = "free", "Free"
    TRIALING = "trialing", "Trialing"
    ACTIVE = "active", "Active"
    PAST_DUE = "past_due", "Past due"
    CANCELED = "canceled", "Canceled"
    UNPAID = "unpaid", "Unpaid"
    INCOMPLETE = "incomplete", "Incomplete"


class StripeWebhookEventStatus(models.TextChoices):
    PROCESSING = "processing", "Processing"
    PROCESSED = "processed", "Processed"
    SKIPPED = "skipped", "Skipped"
    FAILED = "failed", "Failed"


class Plan(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    stripe_price_id = models.CharField(max_length=255, blank=True)
    features = models.JSONField(default=dict, blank=True)
    limits = models.JSONField(default=dict, blank=True)
    is_public = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_public", "is_active"]),
        ]

    def __str__(self):
        return self.name

    def limit_for(self, metric_name):
        return self.limits.get(metric_name)

    def has_feature(self, feature_name):
        return bool(self.features.get(feature_name))


class Subscription(models.Model):
    organization = models.OneToOneField(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    status = models.CharField(
        max_length=30,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.FREE,
    )
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organization_id"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["stripe_customer_id"]),
            models.Index(fields=["stripe_subscription_id"]),
        ]

    def __str__(self):
        return f"{self.organization} - {self.plan}"

    @property
    def is_billable_active(self):
        return self.status in {
            SubscriptionStatus.FREE,
            SubscriptionStatus.TRIALING,
            SubscriptionStatus.ACTIVE,
        }


class StripeWebhookEvent(models.Model):
    event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=120, blank=True)
    status = models.CharField(
        max_length=30,
        choices=StripeWebhookEventStatus.choices,
        default=StripeWebhookEventStatus.PROCESSING,
    )
    error_message = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["event_id"]),
            models.Index(fields=["event_type", "status"]),
        ]

    def __str__(self):
        return self.event_id
