from django.contrib import admin

from .models import UsageRecord


@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "metric_name",
        "quantity",
        "period_start",
        "period_end",
        "source",
        "product_scope",
    )
    list_filter = ("metric_name", "source", "product_scope", "period_start")
    search_fields = ("organization__name", "metric_name", "source", "product_scope")
    autocomplete_fields = ("organization", "subscription")

