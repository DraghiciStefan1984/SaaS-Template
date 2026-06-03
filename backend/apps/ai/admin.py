from django.contrib import admin

from .models import (
    AICallLog,
    AIModelDecisionLog,
    AIModelPolicy,
    AIProvider,
    AIResultCache,
    AITaskProfile,
    PromptTemplate,
)


@admin.register(AIProvider)
class AIProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "status", "default_model", "is_active")
    list_filter = ("status", "is_active")
    search_fields = ("name", "slug", "default_model")


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "version", "is_active", "created_at")
    list_filter = ("is_active", "key")
    search_fields = ("key", "name", "description")
    ordering = ("key", "-version")


@admin.register(AITaskProfile)
class AITaskProfileAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "default_strategy", "product_area", "is_active")
    list_filter = ("default_strategy", "product_area", "is_high_risk", "is_active")
    search_fields = ("key", "name", "description", "product_area")


@admin.register(AIModelPolicy)
class AIModelPolicyAdmin(admin.ModelAdmin):
    list_display = ("task_profile", "name", "strategy", "provider", "model_name", "priority")
    list_filter = ("strategy", "provider", "plan_slug", "is_active")
    search_fields = ("task_profile__key", "name", "model_name", "plan_slug")
    autocomplete_fields = ("task_profile", "provider", "fallback_provider")


@admin.register(AIModelDecisionLog)
class AIModelDecisionLogAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "task_key",
        "selected_strategy",
        "selected_provider",
        "requires_human_review",
        "created_at",
    )
    list_filter = ("selected_strategy", "selected_provider", "requires_human_review", "created_at")
    search_fields = ("organization__name", "user__email", "task_key", "selected_model")
    autocomplete_fields = ("organization", "user", "task_profile", "policy", "selected_provider")


@admin.register(AICallLog)
class AICallLogAdmin(admin.ModelAdmin):
    list_display = ("organization", "provider", "model", "status", "total_tokens", "estimated_cost")
    list_filter = ("provider", "status", "model", "created_at")
    search_fields = ("organization__name", "user__email", "model", "request_hash", "error_message")
    autocomplete_fields = ("organization", "user", "provider", "prompt_template")


@admin.register(AIResultCache)
class AIResultCacheAdmin(admin.ModelAdmin):
    list_display = ("organization", "provider", "model", "request_hash", "expires_at", "created_at")
    list_filter = ("provider", "model", "expires_at")
    search_fields = ("organization__name", "request_hash", "model")
    autocomplete_fields = ("organization", "provider", "prompt_template")
