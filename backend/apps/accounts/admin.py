from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Profile, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("LEGACY 7", {"fields": ("role", "is_email_verified", "avatar")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        (None, {"fields": ("email", "role")}),
    )
    list_display = ("email", "username", "role", "is_email_verified", "is_staff")
    list_filter = ("role", "is_email_verified", "is_staff")
    search_fields = ("email", "username")
    ordering = ("email",)


admin.site.register(Profile)