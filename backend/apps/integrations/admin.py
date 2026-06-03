from django.contrib import admin

from .models import (
    IntegrationAccount,
    IntegrationCredential,
    IntegrationProvider,
    IntegrationSyncLog,
)


@admin.register(IntegrationProvider)
class IntegrationProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "category", "auth_type", "status", "is_active")
    list_filter = ("category", "auth_type", "status", "is_active")
    search_fields = ("name", "slug", "category")
    ordering = ("category", "name")


class IntegrationCredentialInline(admin.StackedInline):
    model = IntegrationCredential
    extra = 0
    readonly_fields = ("created_at", "updated_at")
    fields = (
        "credential_type",
        "encrypted_payload",
        "expires_at",
        "refresh_metadata",
        "created_at",
        "updated_at",
    )


@admin.register(IntegrationAccount)
class IntegrationAccountAdmin(admin.ModelAdmin):
    list_display = ("organization", "provider", "display_name", "status", "connected_by")
    list_filter = ("provider", "status")
    search_fields = (
        "organization__name",
        "provider__name",
        "display_name",
        "external_account_id",
    )
    autocomplete_fields = ("organization", "provider", "connected_by")
    inlines = [IntegrationCredentialInline]


@admin.register(IntegrationSyncLog)
class IntegrationSyncLogAdmin(admin.ModelAdmin):
    list_display = ("integration_account", "action", "status", "started_at", "completed_at")
    list_filter = ("status", "action", "started_at")
    search_fields = ("integration_account__display_name", "external_request_id", "error_message")
    autocomplete_fields = ("integration_account",)

