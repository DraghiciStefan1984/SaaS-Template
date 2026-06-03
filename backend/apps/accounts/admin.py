from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("name",)}),
        (
            _("Status"),
            {
                "fields": (
                    "account_status",
                    "is_email_verified",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                )
            },
        ),
        (_("Permissions"), {"fields": ("groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "name", "password1", "password2"),
            },
        ),
    )
    list_display = ("email", "name", "account_status", "is_email_verified", "is_staff")
    list_filter = ("account_status", "is_email_verified", "is_staff", "is_superuser")
    ordering = ("email",)
    search_fields = ("email", "name")

