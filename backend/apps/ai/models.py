from decimal import Decimal

from django.conf import settings
from django.db import models


class AIProviderStatus(models.TextChoices):
    AVAILABLE = "available", "Available"
    DISABLED = "disabled", "Disabled"


class AICallStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    CACHED = "cached", "Cached"


class AIExecutionStrategy(models.TextChoices):
    DETERMINISTIC = "deterministic", "Deterministic code/rules"
    CLASSIC_ML = "classic_ml", "Classic ML/DL library"
    LOCAL_MODEL = "local_model", "Local small model"
    LOW_COST_LLM = "low_cost_llm", "Low-cost LLM"
    STANDARD_LLM = "standard_llm", "Standard LLM"
    ADVANCED_LLM = "advanced_llm", "Advanced LLM"
    HUMAN_REVIEW = "human_review", "Human review"


class AIProvider(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    status = models.CharField(
        max_length=20,
        choices=AIProviderStatus.choices,
        default=AIProviderStatus.AVAILABLE,
    )
    default_model = models.CharField(max_length=120, blank=True)
    supported_features = models.JSONField(default=dict, blank=True)
    config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active", "status"]),
        ]

    def __str__(self):
        return self.name


class PromptTemplate(models.Model):
    key = models.SlugField()
    name = models.CharField(max_length=160)
    version = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True)
    system_prompt = models.TextField(blank=True)
    user_prompt = models.TextField()
    output_schema = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["key", "version"],
                name="unique_prompt_template_version",
            )
        ]
        indexes = [
            models.Index(fields=["key", "is_active"]),
            models.Index(fields=["version"]),
        ]

    def __str__(self):
        return f"{self.key} v{self.version}"


class AITaskProfile(models.Model):
    key = models.SlugField(unique=True)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    product_area = models.CharField(max_length=120, blank=True)
    default_strategy = models.CharField(
        max_length=30,
        choices=AIExecutionStrategy.choices,
        default=AIExecutionStrategy.LOW_COST_LLM,
    )
    allowed_strategies = models.JSONField(default=list, blank=True)
    expected_runs_per_month = models.PositiveIntegerField(default=0)
    max_cost_per_run = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        default=Decimal("0"),
    )
    latency_target_ms = models.PositiveIntegerField(default=0)
    quality_threshold = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("0.80"),
    )
    is_high_risk = models.BooleanField(default=False)
    requires_structured_output = models.BooleanField(default=False)
    config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]
        indexes = [
            models.Index(fields=["key", "is_active"]),
            models.Index(fields=["product_area"]),
        ]

    def __str__(self):
        return self.key


class AIModelPolicy(models.Model):
    task_profile = models.ForeignKey(
        AITaskProfile,
        on_delete=models.CASCADE,
        related_name="policies",
    )
    name = models.CharField(max_length=160)
    strategy = models.CharField(max_length=30, choices=AIExecutionStrategy.choices)
    provider = models.ForeignKey(
        AIProvider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="model_policies",
    )
    model_name = models.CharField(max_length=120, blank=True)
    plan_slug = models.SlugField(blank=True)
    priority = models.PositiveSmallIntegerField(default=100)
    max_cost_per_run = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        default=Decimal("0"),
    )
    max_latency_ms = models.PositiveIntegerField(default=0)
    confidence_threshold = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("0.80"),
    )
    fallback_strategy = models.CharField(
        max_length=30,
        choices=AIExecutionStrategy.choices,
        blank=True,
    )
    fallback_provider = models.ForeignKey(
        AIProvider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fallback_model_policies",
    )
    fallback_model_name = models.CharField(max_length=120, blank=True)
    rules = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["task_profile", "priority", "id"]
        indexes = [
            models.Index(fields=["task_profile", "strategy", "is_active"]),
            models.Index(fields=["plan_slug"]),
            models.Index(fields=["priority"]),
        ]

    def __str__(self):
        return f"{self.task_profile.key}: {self.strategy}"


class AIModelDecisionLog(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="ai_model_decisions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_model_decisions",
    )
    task_profile = models.ForeignKey(
        AITaskProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decision_logs",
    )
    policy = models.ForeignKey(
        AIModelPolicy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decision_logs",
    )
    task_key = models.SlugField()
    selected_strategy = models.CharField(max_length=30, choices=AIExecutionStrategy.choices)
    selected_provider = models.ForeignKey(
        AIProvider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decision_logs",
    )
    selected_model = models.CharField(max_length=120, blank=True)
    fallback_strategy = models.CharField(
        max_length=30,
        choices=AIExecutionStrategy.choices,
        blank=True,
    )
    fallback_provider = models.ForeignKey(
        AIProvider,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fallback_decision_logs",
    )
    fallback_model = models.CharField(max_length=120, blank=True)
    requires_human_review = models.BooleanField(default=False)
    decision_reason = models.TextField(blank=True)
    constraints = models.JSONField(default=dict, blank=True)
    input_summary = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["task_key", "selected_strategy"]),
            models.Index(fields=["requires_human_review"]),
        ]

    def __str__(self):
        return f"{self.organization} {self.task_key} {self.selected_strategy}"


class AICallLog(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="ai_call_logs",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_call_logs",
    )
    provider = models.ForeignKey(
        AIProvider,
        on_delete=models.PROTECT,
        related_name="call_logs",
    )
    prompt_template = models.ForeignKey(
        PromptTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="call_logs",
    )
    prompt_version = models.PositiveIntegerField(null=True, blank=True)
    model = models.CharField(max_length=120)
    status = models.CharField(
        max_length=20,
        choices=AICallStatus.choices,
        default=AICallStatus.PENDING,
    )
    related_entity_type = models.CharField(max_length=120, blank=True)
    related_entity_id = models.CharField(max_length=120, blank=True)
    request_hash = models.CharField(max_length=64, db_index=True)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    total_tokens = models.PositiveIntegerField(default=0)
    estimated_cost = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        default=Decimal("0"),
    )
    latency_ms = models.PositiveIntegerField(default=0)
    response_payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["provider", "model"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.organization} {self.provider} {self.status}"


class AIResultCache(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ai_result_cache",
    )
    provider = models.ForeignKey(AIProvider, on_delete=models.CASCADE, related_name="result_cache")
    prompt_template = models.ForeignKey(
        PromptTemplate,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="result_cache",
    )
    model = models.CharField(max_length=120)
    request_hash = models.CharField(max_length=64)
    response_payload = models.JSONField(default=dict)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "provider", "model", "request_hash"],
                name="unique_ai_cache_entry",
            )
        ]
        indexes = [
            models.Index(fields=["request_hash"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"{self.provider} {self.model} {self.request_hash}"
