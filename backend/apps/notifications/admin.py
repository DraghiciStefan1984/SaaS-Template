from django.contrib import admin

from .models import InAppNotification, NotificationDeliveryLog, NotificationPreference


@admin.register(InAppNotification)
class InAppNotificationAdmin(admin.ModelAdmin):
    list_display = ("organization", "user", "event", "title", "is_read", "created_at")
    list_filter = ("event", "is_read", "created_at")
    search_fields = ("organization__name", "user__email", "title", "message")
    autocomplete_fields = ("organization", "user")


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("organization", "user", "event", "channel", "is_enabled")
    list_filter = ("event", "channel", "is_enabled")
    search_fields = ("organization__name", "user__email", "event", "channel")
    autocomplete_fields = ("organization", "user")


@admin.register(NotificationDeliveryLog)
class NotificationDeliveryLogAdmin(admin.ModelAdmin):
    list_display = ("organization", "event", "channel", "status", "recipient", "created_at")
    list_filter = ("event", "channel", "status", "provider", "created_at")
    search_fields = ("organization__name", "user__email", "recipient", "subject", "error_message")
    autocomplete_fields = ("organization", "user")
