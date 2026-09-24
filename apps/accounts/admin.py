"""Django admin for user accounts."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["username"]
    list_display = ["username", "full_name", "role", "department", "faculty", "is_active"]
    list_filter = ["role", "faculty", "is_active"]
    search_fields = ["username", "full_name", "email"]

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal", {"fields": ("full_name", "email")}),
        ("Role & scope", {"fields": ("role", "department", "faculty")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "full_name", "role", "department", "faculty", "password1", "password2"),
        }),
    )
    readonly_fields = ["date_joined"]
