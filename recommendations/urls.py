"""URL configuration for the recommendations app."""
from django.urls import path

from . import views

app_name = "recommendations"

urlpatterns = [
    path("", views.recommendation_list, name="list"),
    path("generate/", views.generate, name="generate"),
    path("<int:recommendation_id>/ai/", views.ai_analysis, name="ai_analysis"),
]