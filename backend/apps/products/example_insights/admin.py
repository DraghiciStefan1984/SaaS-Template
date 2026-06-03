from django.contrib import admin

from .models import ExampleInsightRequest


@admin.register(ExampleInsightRequest)
class ExampleInsightRequestAdmin(admin.ModelAdmin):
    list_display = ("organization", "title", "status", "report", "job_run", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("organization__name", "title", "error_message")
    autocomplete_fields = ("organization", "created_by", "report", "job_run")

