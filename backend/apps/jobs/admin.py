from django.contrib import admin

from .models import JobRun, ScheduledRun, ScheduledWorkflow


@admin.register(JobRun)
class JobRunAdmin(admin.ModelAdmin):
    list_display = ("organization", "name", "task_name", "status", "attempts", "created_at")
    list_filter = ("status", "task_name", "created_at")
    search_fields = ("organization__name", "name", "task_name", "related_entity_id")
    autocomplete_fields = ("organization", "created_by")


@admin.register(ScheduledWorkflow)
class ScheduledWorkflowAdmin(admin.ModelAdmin):
    list_display = ("organization", "name", "workflow_type", "status", "frequency", "next_run_at")
    list_filter = ("workflow_type", "status", "frequency")
    search_fields = ("organization__name", "name")
    autocomplete_fields = ("organization", "created_by")


@admin.register(ScheduledRun)
class ScheduledRunAdmin(admin.ModelAdmin):
    list_display = ("workflow", "trigger", "job_run", "scheduled_for", "created_at")
    list_filter = ("trigger", "created_at")
    autocomplete_fields = ("workflow", "job_run")
