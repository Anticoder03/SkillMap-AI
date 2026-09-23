"""Admin configuration for the careers knowledge base."""
from django.contrib import admin

from .models import Career, CareerInterest, CareerPrerequisite, CareerSkill


class CareerSkillInline(admin.TabularInline):
    model = CareerSkill
    extra = 2
    autocomplete_fields = ["skill"]


class CareerInterestInline(admin.TabularInline):
    model = CareerInterest
    extra = 2
    autocomplete_fields = ["interest"]


class CareerPrerequisiteInline(admin.TabularInline):
    model = CareerPrerequisite
    extra = 1


@admin.register(Career)
class CareerAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "difficulty", "demand_level", "salary_range")
    list_filter = ("category", "difficulty", "demand_level", "required_education")
    search_fields = ("title", "description", "category")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("slug",)
    inlines = [CareerSkillInline, CareerInterestInline, CareerPrerequisiteInline]


@admin.register(CareerSkill)
class CareerSkillAdmin(admin.ModelAdmin):
    list_display = ("career", "skill", "importance", "required_level")
    list_filter = ("importance", "required_level")
    search_fields = ("career__title", "skill__name")
    autocomplete_fields = ["career", "skill"]


@admin.register(CareerInterest)
class CareerInterestAdmin(admin.ModelAdmin):
    list_display = ("career", "interest", "weight")
    list_filter = ("weight",)
    search_fields = ("career__title", "interest__name")
    autocomplete_fields = ["career", "interest"]


@admin.register(CareerPrerequisite)
class CareerPrerequisiteAdmin(admin.ModelAdmin):
    list_display = ("career", "priority", "description")
    list_filter = ("priority",)
    search_fields = ("career__title", "description")
    autocomplete_fields = ["career"]