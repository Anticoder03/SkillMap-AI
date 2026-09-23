"""URL configuration for the ai_engine app."""
from django.urls import path

from . import views

app_name = "ai_engine"

urlpatterns = [
    path("analysis/<int:career_id>/", views.analysis_json, name="analysis_json"),
]