"""URL configuration for the assessment app."""
from django.urls import path

from . import views

app_name = "assessment"

urlpatterns = [
    path("start/", views.start, name="start"),
    path("question/<int:question_id>/", views.question, name="question"),
    path("complete/<int:assessment_id>/", views.complete, name="complete"),
]