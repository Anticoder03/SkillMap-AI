"""Admin configuration for the accounts app."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User

from .models import UserProfile

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False


class UserAdmin(DjangoUserAdmin):
    inlines = [UserProfileInline]


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "education_level", "experience_level", "degree", "college", "location")
    list_filter = ("education_level", "experience_level", "college")
    search_fields = ("user__username", "user__email", "degree", "college", "location")
    readonly_fields = ("created_at", "updated_at")


admin.site.unregister(User)
admin.site.register(User, UserAdmin)