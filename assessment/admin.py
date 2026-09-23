"""Admin configuration for the assessment app."""
from django.contrib import admin

from .models import Answer, Assessment, Interest, Question, QuestionOption, Skill, UserInterest, UserSkill


class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 3
    autocomplete_fields = ["interest", "skill"]


@admin.register(Interest)
class InterestAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name", "description")
    ordering = ("name",)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "description")
    list_filter = ("category",)
    search_fields = ("name", "description")
    ordering = ("name",)


@admin.register(UserInterest)
class UserInterestAdmin(admin.ModelAdmin):
    list_display = ("user", "interest", "level")
    list_filter = ("level", "interest")
    search_fields = ("user__username", "interest__name")
    autocomplete_fields = ["user", "interest"]


@admin.register(UserSkill)
class UserSkillAdmin(admin.ModelAdmin):
    list_display = ("user", "skill", "proficiency")
    list_filter = ("proficiency", "skill")
    search_fields = ("user__username", "skill__name")
    autocomplete_fields = ["user", "skill"]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("order", "question_text", "question_type", "category", "weight", "is_active")
    list_filter = ("question_type", "category", "is_active")
    search_fields = ("question_text",)
    list_editable = ("weight", "is_active")
    list_display_links = ("question_text",)
    inlines = [QuestionOptionInline]


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("user", "started_at", "completed_at", "score", "is_completed")
    list_filter = ("is_completed", "started_at")
    search_fields = ("user__username",)
    readonly_fields = ("started_at", "completed_at")
    autocomplete_fields = ["user"]


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("assessment", "question", "option", "score")
    list_filter = ("score",)
    search_fields = ("assessment__user__username", "question__question_text")