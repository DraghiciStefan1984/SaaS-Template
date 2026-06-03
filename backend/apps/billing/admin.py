from django.contrib import admin

from .models import Plan, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_public", "is_active", "display_order")
    list_filter = ("is_public", "is_active")
    search_fields = ("name", "slug", "stripe_price_id")
    ordering = ("display_order", "name")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("organization", "plan", "status", "stripe_customer_id", "current_period_end")
    list_filter = ("status", "plan")
    search_fields = (
        "organization__name",
        "stripe_customer_id",
        "stripe_subscription_id",
    )
    autocomplete_fields = ("organization", "plan")

