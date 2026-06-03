from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("organization", "user", "action", "status", "target_entity_type", "created_at")
    list_filter = ("action", "category", "status", "created_at")
    search_fields = ("organization__name", "user__email", "action", "target_entity_id")
    autocomplete_fields = ("organization", "user")

