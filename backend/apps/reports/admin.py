from django.contrib import admin

from .models import Report, ReportArtifact, ReportTemplate


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "default_format", "ai_task_profile", "is_active")
    list_filter = ("default_format", "is_active")
    search_fields = ("key", "name", "description")
    autocomplete_fields = ("ai_task_profile",)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("organization", "title", "status", "requested_format", "created_at")
    list_filter = ("status", "requested_format", "created_at")
    search_fields = ("organization__name", "title", "related_entity_id", "error_message")
    autocomplete_fields = ("organization", "created_by", "template")


@admin.register(ReportArtifact)
class ReportArtifactAdmin(admin.ModelAdmin):
    list_display = ("report", "format", "storage_backend", "created_at")
    list_filter = ("format", "storage_backend", "created_at")
    search_fields = ("report__title", "file_path", "external_url", "checksum")
    autocomplete_fields = ("report",)

