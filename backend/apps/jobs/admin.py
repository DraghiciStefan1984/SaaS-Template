from django.contrib import admin

from .models import JobRun


@admin.register(JobRun)
class JobRunAdmin(admin.ModelAdmin):
    list_display = ("organization", "name", "task_name", "status", "attempts", "created_at")
    list_filter = ("status", "task_name", "created_at")
    search_fields = ("organization__name", "name", "task_name", "related_entity_id")
    autocomplete_fields = ("organization", "created_by")

