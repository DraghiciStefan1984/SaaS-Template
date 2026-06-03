from django.contrib import admin

from .models import DataDeletionRequest, DataExportRequest


@admin.register(DataExportRequest)
class DataExportRequestAdmin(admin.ModelAdmin):
    list_display = ("organization", "scope", "status", "requested_by", "created_at")
    list_filter = ("scope", "status", "created_at")
    search_fields = ("organization__name", "requested_by__email")
    readonly_fields = ("created_at", "updated_at", "completed_at")


@admin.register(DataDeletionRequest)
class DataDeletionRequestAdmin(admin.ModelAdmin):
    list_display = ("organization", "target", "status", "requested_by", "created_at")
    list_filter = ("target", "status", "created_at")
    search_fields = ("organization__name", "requested_by__email", "reason")
    readonly_fields = ("created_at", "updated_at", "completed_at")
