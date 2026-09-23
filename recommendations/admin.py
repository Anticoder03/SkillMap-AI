"""Admin configuration for stored recommendations."""
from django.contrib import admin

from .models import Recommendation


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ("user", "career", "match_score", "created_at")
    list_filter = ("match_score", "created_at", "career")
    search_fields = ("user__username", "career__title")
    readonly_fields = ("created_at",)
    autocomplete_fields = ["user", "career"]