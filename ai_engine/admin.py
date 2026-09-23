"""Admin configuration for the AI engine results."""
from django.contrib import admin

from .models import CareerAnalysis


@admin.register(CareerAnalysis)
class CareerAnalysisAdmin(admin.ModelAdmin):
    list_display = ("user", "career", "source", "provider", "created_at")
    list_filter = ("source", "provider", "created_at")
    search_fields = ("user__username", "career__title")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ["user", "career"]