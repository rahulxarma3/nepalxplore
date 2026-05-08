from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "display_name", "is_subscribed", "is_active", "created_at"]
    list_filter = ["is_active", "is_staff", "preferred_language"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["-created_at"]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("NepaXplore", {
            "fields": ("avatar", "preferred_language", "dark_mode", "notifications_enabled")
        }),
    )
