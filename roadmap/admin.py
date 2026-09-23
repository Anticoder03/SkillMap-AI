"""Admin configuration for roadmaps."""
from django.contrib import admin

from .models import Roadmap, RoadmapPhase, RoadmapTask


class RoadmapTaskInline(admin.TabularInline):
    model = RoadmapTask
    extra = 2


class RoadmapPhaseInline(admin.TabularInline):
    model = RoadmapPhase
    extra = 1
    show_change_link = True


@admin.register(Roadmap)
class RoadmapAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "career", "duration_weeks", "created_at")
    list_filter = ("created_at", "career")
    search_fields = ("title", "user__username", "career__title")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ["user", "career"]
    inlines = [RoadmapPhaseInline]


@admin.register(RoadmapPhase)
class RoadmapPhaseAdmin(admin.ModelAdmin):
    list_display = ("title", "roadmap", "order", "duration_weeks")
    list_filter = ("roadmap",)
    search_fields = ("title", "roadmap__title", "roadmap__user__username")
    inlines = [RoadmapTaskInline]


@admin.register(RoadmapTask)
class RoadmapTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "phase", "status", "estimated_hours", "order")
    list_filter = ("status",)
    search_fields = ("title", "phase__title", "phase__roadmap__user__username")
    list_editable = ("status",)