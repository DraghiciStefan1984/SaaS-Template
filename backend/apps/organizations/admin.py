from django.contrib import admin

from .models import Membership, Organization


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0
    autocomplete_fields = ("user", "invited_by")


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "timezone", "default_language", "created_at")
    list_filter = ("timezone", "default_language")
    search_fields = ("name", "owner__email")
    autocomplete_fields = ("owner",)
    inlines = [MembershipInline]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("organization", "user", "role", "status", "created_at")
    list_filter = ("role", "status")
    search_fields = ("organization__name", "user__email", "invited_email")
    autocomplete_fields = ("organization", "user", "invited_by")

