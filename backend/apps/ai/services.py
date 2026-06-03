import hashlib
import json
import time

from django.conf import settings
from django.db.models import Q
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate
from rest_framework.exceptions import APIException, ValidationError

from apps.billing.services import get_subscription_for_organization

from .models import (
    AICallLog,
    AICallStatus,
    AIExecutionStrategy,
    AIModelDecisionLog,
    AIModelPolicy,
    AIProvider,
    AITaskProfile,
    PromptTemplate,
)

PROVIDER_KEY_SETTINGS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}

LLM_STRATEGIES = {
    AIExecutionStrategy.LOW_COST_LLM,
    AIExecutionStrategy.STANDARD_LLM,
    AIExecutionStrategy.ADVANCED_LLM,
}

DEFAULT_AI_LADDER = (
    AIExecutionStrategy.DETERMINISTIC,
    AIExecutionStrategy.CLASSIC_ML,
    AIExecutionStrategy.LOCAL_MODEL,
    AIExecutionStrategy.LOW_COST_LLM,
    AIExecutionStrategy.STANDARD_LLM,
    AIExecutionStrategy.ADVANCED_LLM,
    AIExecutionStrategy.HUMAN_REVIEW,
)

HIGH_VOLUME_RUN_THRESHOLD = 500


class AIProviderNotConfigured(APIException):
    status_code = 503
    default_detail = (
        "AI provider is not configured yet. Create the provider account, add the API key, "
        "choose a default model, and keep calls routed through the backend AI service."
    )
    default_code = "ai_provider_not_configured"


def provider_configuration_status(provider):
    key_setting = PROVIDER_KEY_SETTINGS.get(provider.slug)
    if not key_setting:
        return {"status": "custom_provider", "detail": "Custom provider requires a product client."}
    if not getattr(settings, key_setting, ""):
        return {
            "status": "not_configured",
            "detail": f"{key_setting} is not configured yet.",
        }
    return {"status": "configured", "detail": "Provider API key is configured."}


def ensure_provider_configured(provider):
    status = provider_configuration_status(provider)
    if status["status"] != "configured":
        raise AIProviderNotConfigured(status["detail"])


def latest_prompt_template(key):
    return PromptTemplate.objects.filter(key=key, is_active=True).order_by("-version").first()


def build_request_hash(payload):
    serialized = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()


def validate_structured_output(payload, schema):
    if not schema:
        return True
    try:
        validate(instance=payload, schema=schema)
    except JsonSchemaValidationError as exc:
        raise ValidationError({"output": exc.message}) from exc
    return True


def get_organization_plan_slug(organization):
    subscription = get_subscription_for_organization(organization)
    if subscription is None or subscription.plan is None:
        return ""
    return subscription.plan.slug


def normalize_strategy(value):
    if value not in AIExecutionStrategy.values:
        raise ValidationError({"strategy": f"Unsupported AI execution strategy: {value}"})
    return value


def normalize_allowed_strategies(profile, constraints=None):
    constraints = constraints or {}
    configured = profile.allowed_strategies or list(DEFAULT_AI_LADDER)
    allowed = [normalize_strategy(strategy) for strategy in configured]

    requested_allowed = constraints.get("allowed_strategies") or []
    if requested_allowed:
        requested_allowed = [normalize_strategy(strategy) for strategy in requested_allowed]
        allowed = [strategy for strategy in allowed if strategy in requested_allowed]

    if not allowed:
        raise ValidationError({"allowed_strategies": "No valid AI strategies are available."})
    return allowed


def summarize_input_payload(input_payload):
    if input_payload is None:
        return {}
    if isinstance(input_payload, dict):
        return {
            "type": "object",
            "field_count": len(input_payload),
            "keys": sorted(input_payload.keys())[:20],
        }
    if isinstance(input_payload, list):
        return {
            "type": "array",
            "item_count": len(input_payload),
        }
    return {"type": type(input_payload).__name__}


def first_allowed_strategy(preferred_strategies, allowed_strategies):
    for strategy in preferred_strategies:
        if strategy in allowed_strategies:
            return strategy
    return allowed_strategies[0]


def strategy_fallback_chain(selected_strategy, allowed_strategies):
    try:
        selected_index = DEFAULT_AI_LADDER.index(selected_strategy)
    except ValueError:
        return []

    return [
        strategy
        for strategy in DEFAULT_AI_LADDER[selected_index + 1 :]
        if strategy in allowed_strategies
    ]


def choose_strategy_from_constraints(profile, constraints, allowed_strategies):
    forced_strategy = constraints.get("force_strategy")
    if forced_strategy:
        forced_strategy = normalize_strategy(forced_strategy)
        if forced_strategy not in allowed_strategies:
            raise ValidationError(
                {"force_strategy": "Forced strategy is not allowed for this task."}
            )
        return forced_strategy, "Forced by request constraints."

    risk_level = constraints.get("risk_level", "low")
    requires_human_review = constraints.get("requires_human_review", False)
    if requires_human_review or (profile.is_high_risk and risk_level == "high"):
        if AIExecutionStrategy.HUMAN_REVIEW in allowed_strategies:
            return AIExecutionStrategy.HUMAN_REVIEW, "High-risk task requires human review."
        if AIExecutionStrategy.ADVANCED_LLM in allowed_strategies:
            return AIExecutionStrategy.ADVANCED_LLM, "High-risk task escalated to advanced LLM."

    if constraints.get("can_use_deterministic") or constraints.get("can_solve_without_ai"):
        if AIExecutionStrategy.DETERMINISTIC in allowed_strategies:
            return AIExecutionStrategy.DETERMINISTIC, "Task can be solved with deterministic code."

    if constraints.get("can_use_classic_ml"):
        if AIExecutionStrategy.CLASSIC_ML in allowed_strategies:
            return AIExecutionStrategy.CLASSIC_ML, "Task can be solved by classic ML/DL libraries."

    if constraints.get("can_use_local_model"):
        if AIExecutionStrategy.LOCAL_MODEL in allowed_strategies:
            return AIExecutionStrategy.LOCAL_MODEL, "Task can use a local small model."

    if constraints.get("requires_advanced_reasoning"):
        advanced = (AIExecutionStrategy.ADVANCED_LLM, AIExecutionStrategy.STANDARD_LLM)
        return first_allowed_strategy(advanced, allowed_strategies), "Advanced reasoning requested."

    expected_runs = int(
        constraints.get("expected_runs_per_month") or profile.expected_runs_per_month
    )
    cost_sensitivity = constraints.get("cost_sensitivity", "")
    if expected_runs >= HIGH_VOLUME_RUN_THRESHOLD or cost_sensitivity == "high":
        preferred = (
            AIExecutionStrategy.LOW_COST_LLM,
            AIExecutionStrategy.LOCAL_MODEL,
            AIExecutionStrategy.CLASSIC_ML,
            AIExecutionStrategy.DETERMINISTIC,
        )
        return (
            first_allowed_strategy(preferred, allowed_strategies),
            "High-volume/cost-sensitive task.",
        )

    if profile.default_strategy in allowed_strategies:
        return profile.default_strategy, "Selected task profile default strategy."

    return allowed_strategies[0], "Selected first allowed strategy."


def select_policy_for_strategy(profile, strategy, organization):
    plan_slug = get_organization_plan_slug(organization)
    policies = (
        AIModelPolicy.objects.filter(
            task_profile=profile,
            strategy=strategy,
            is_active=True,
        )
        .filter(Q(plan_slug="") | Q(plan_slug=plan_slug))
        .select_related("provider", "fallback_provider")
        .order_by("priority", "id")
    )

    plan_specific_policy = next(
        (policy for policy in policies if policy.plan_slug == plan_slug),
        None,
    )
    if plan_specific_policy is not None:
        return plan_specific_policy
    return next(iter(policies), None)


def default_llm_provider():
    provider_slug = settings.DEFAULT_AI_PROVIDER
    provider = AIProvider.objects.filter(slug=provider_slug, is_active=True).first()
    if provider is not None:
        return provider
    return AIProvider.objects.filter(is_active=True).order_by("name").first()


def select_ai_execution_plan(
    *,
    organization,
    user,
    task_key,
    input_payload=None,
    constraints=None,
    metadata=None,
    log_decision=True,
):
    constraints = constraints or {}
    metadata = metadata or {}
    profile = AITaskProfile.objects.filter(key=task_key, is_active=True).first()
    if profile is None:
        raise ValidationError({"task_key": "No active AI task profile exists for this key."})

    allowed_strategies = normalize_allowed_strategies(profile, constraints)
    selected_strategy, reason = choose_strategy_from_constraints(
        profile,
        constraints,
        allowed_strategies,
    )
    policy = select_policy_for_strategy(profile, selected_strategy, organization)
    fallback_chain = strategy_fallback_chain(selected_strategy, allowed_strategies)

    provider = None
    selected_model = ""
    if selected_strategy in LLM_STRATEGIES:
        provider = policy.provider if policy and policy.provider else default_llm_provider()
        selected_model = (
            policy.model_name
            if policy and policy.model_name
            else getattr(provider, "default_model", "") or settings.DEFAULT_AI_MODEL
        )

    fallback_strategy = policy.fallback_strategy if policy and policy.fallback_strategy else ""
    fallback_provider = policy.fallback_provider if policy and policy.fallback_provider else None
    fallback_model = policy.fallback_model_name if policy else ""

    requires_human_review = (
        selected_strategy == AIExecutionStrategy.HUMAN_REVIEW
        or constraints.get("requires_human_review", False)
        or (profile.is_high_risk and constraints.get("risk_level") == "high")
    )
    input_summary = summarize_input_payload(input_payload)

    decision_log = None
    if log_decision:
        decision_log = AIModelDecisionLog.objects.create(
            organization=organization,
            user=user,
            task_profile=profile,
            policy=policy,
            task_key=task_key,
            selected_strategy=selected_strategy,
            selected_provider=provider,
            selected_model=selected_model,
            fallback_strategy=fallback_strategy,
            fallback_provider=fallback_provider,
            fallback_model=fallback_model,
            requires_human_review=requires_human_review,
            decision_reason=reason,
            constraints=constraints,
            input_summary=input_summary,
            metadata=metadata,
        )

    return {
        "task_key": task_key,
        "task_profile_id": profile.id,
        "decision_log_id": decision_log.id if decision_log else None,
        "strategy": selected_strategy,
        "provider_slug": provider.slug if provider else "",
        "model": selected_model,
        "policy_id": policy.id if policy else None,
        "requires_human_review": requires_human_review,
        "fallback": {
            "strategy": fallback_strategy,
            "provider_slug": fallback_provider.slug if fallback_provider else "",
            "model": fallback_model,
        },
        "fallback_chain": fallback_chain,
        "reason": reason,
        "configuration": (
            provider_configuration_status(provider)
            if provider
            else {
                "status": "not_required",
                "detail": "Selected strategy does not require an external LLM provider.",
            }
        ),
        "constraints": constraints,
        "input_summary": input_summary,
    }


def run_ai_task(
    *,
    organization,
    user,
    task_key,
    prompt_key,
    input_payload,
    constraints=None,
    related_entity_type="",
    related_entity_id="",
    metadata=None,
):
    execution_plan = select_ai_execution_plan(
        organization=organization,
        user=user,
        task_key=task_key,
        input_payload=input_payload,
        constraints=constraints,
        metadata=metadata,
        log_decision=True,
    )

    if execution_plan["strategy"] not in LLM_STRATEGIES:
        return {
            "status": "selected",
            "execution_plan": execution_plan,
            "detail": (
                "This strategy should be handled by a product-specific deterministic, "
                "ML/DL, local model, or human-review executor."
            ),
        }

    if not execution_plan["provider_slug"]:
        raise AIProviderNotConfigured("No active LLM provider is available for this task.")

    return run_ai_prompt(
        organization=organization,
        user=user,
        provider_slug=execution_plan["provider_slug"],
        prompt_key=prompt_key,
        input_payload=input_payload,
        model=execution_plan["model"],
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        metadata={
            **(metadata or {}),
            "ai_execution_plan": execution_plan,
        },
    )


def run_ai_prompt(
    *,
    organization,
    user,
    provider_slug,
    prompt_key,
    input_payload,
    model="",
    related_entity_type="",
    related_entity_id="",
    metadata=None,
):
    provider = AIProvider.objects.get(slug=provider_slug, is_active=True)
    prompt_template = latest_prompt_template(prompt_key)
    if prompt_template is None:
        raise ValidationError({"prompt_key": "No active prompt template exists for this key."})

    request_hash = build_request_hash(
        {
            "provider": provider.slug,
            "model": model or provider.default_model,
            "prompt_key": prompt_template.key,
            "prompt_version": prompt_template.version,
            "input": input_payload,
        }
    )
    started = time.perf_counter()

    try:
        ensure_provider_configured(provider)
    except AIProviderNotConfigured as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        AICallLog.objects.create(
            organization=organization,
            user=user,
            provider=provider,
            prompt_template=prompt_template,
            prompt_version=prompt_template.version,
            model=model or provider.default_model,
            status=AICallStatus.FAILED,
            request_hash=request_hash,
            latency_ms=latency_ms,
            error_message=str(exc.detail),
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            metadata=metadata or {},
        )
        raise

    # Real provider calls are intentionally not made in the core template.
    # Product endpoints should call this service after selecting a provider and prompt.
    raise AIProviderNotConfigured(
        "Provider client execution is not implemented in the core template yet."
    )
