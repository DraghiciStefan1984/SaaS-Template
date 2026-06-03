from rest_framework import serializers

from .models import (
    AICallLog,
    AIModelDecisionLog,
    AIModelPolicy,
    AIProvider,
    AITaskProfile,
    PromptTemplate,
)
from .services import provider_configuration_status


class AIProviderSerializer(serializers.ModelSerializer):
    configuration = serializers.SerializerMethodField()

    class Meta:
        model = AIProvider
        fields = (
            "id",
            "name",
            "slug",
            "status",
            "default_model",
            "supported_features",
            "configuration",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_configuration(self, obj) -> dict:
        return provider_configuration_status(obj)


class PromptTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromptTemplate
        fields = (
            "id",
            "key",
            "name",
            "version",
            "description",
            "system_prompt",
            "user_prompt",
            "output_schema",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AITaskProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AITaskProfile
        fields = (
            "id",
            "key",
            "name",
            "description",
            "product_area",
            "default_strategy",
            "allowed_strategies",
            "expected_runs_per_month",
            "max_cost_per_run",
            "latency_target_ms",
            "quality_threshold",
            "is_high_risk",
            "requires_structured_output",
            "config",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AIModelPolicySerializer(serializers.ModelSerializer):
    task_profile = AITaskProfileSerializer(read_only=True)
    provider = AIProviderSerializer(read_only=True)
    fallback_provider = AIProviderSerializer(read_only=True)

    class Meta:
        model = AIModelPolicy
        fields = (
            "id",
            "task_profile",
            "name",
            "strategy",
            "provider",
            "model_name",
            "plan_slug",
            "priority",
            "max_cost_per_run",
            "max_latency_ms",
            "confidence_threshold",
            "fallback_strategy",
            "fallback_provider",
            "fallback_model_name",
            "rules",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AIModelDecisionLogSerializer(serializers.ModelSerializer):
    task_profile = AITaskProfileSerializer(read_only=True)
    policy = AIModelPolicySerializer(read_only=True)
    selected_provider = AIProviderSerializer(read_only=True)
    fallback_provider = AIProviderSerializer(read_only=True)

    class Meta:
        model = AIModelDecisionLog
        fields = (
            "id",
            "organization",
            "user",
            "task_profile",
            "policy",
            "task_key",
            "selected_strategy",
            "selected_provider",
            "selected_model",
            "fallback_strategy",
            "fallback_provider",
            "fallback_model",
            "requires_human_review",
            "decision_reason",
            "constraints",
            "input_summary",
            "metadata",
            "created_at",
        )
        read_only_fields = fields


class AIExecutionPlanRequestSerializer(serializers.Serializer):
    organization_id = serializers.IntegerField()
    task_key = serializers.SlugField()
    input_payload = serializers.JSONField(required=False)
    constraints = serializers.JSONField(required=False)
    metadata = serializers.JSONField(required=False)
    log_decision = serializers.BooleanField(required=False, default=True)


class AIExecutionPlanSerializer(serializers.Serializer):
    task_key = serializers.CharField()
    task_profile_id = serializers.IntegerField()
    decision_log_id = serializers.IntegerField(allow_null=True)
    strategy = serializers.CharField()
    provider_slug = serializers.CharField(allow_blank=True)
    model = serializers.CharField(allow_blank=True)
    policy_id = serializers.IntegerField(allow_null=True)
    requires_human_review = serializers.BooleanField()
    fallback = serializers.JSONField()
    fallback_chain = serializers.ListField(child=serializers.CharField())
    reason = serializers.CharField()
    configuration = serializers.JSONField()
    constraints = serializers.JSONField()
    input_summary = serializers.JSONField()


class AICallLogSerializer(serializers.ModelSerializer):
    provider = AIProviderSerializer(read_only=True)
    prompt_template = PromptTemplateSerializer(read_only=True)

    class Meta:
        model = AICallLog
        fields = (
            "id",
            "organization",
            "user",
            "provider",
            "prompt_template",
            "prompt_version",
            "model",
            "status",
            "related_entity_type",
            "related_entity_id",
            "request_hash",
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "estimated_cost",
            "latency_ms",
            "response_payload",
            "error_message",
            "metadata",
            "created_at",
        )
        read_only_fields = fields
