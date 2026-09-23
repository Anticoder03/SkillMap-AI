"""URL configuration for the careers app."""
from django.urls import path

from . import views

app_name = "careers"

urlpatterns = [
    path("", views.career_list, name="list"),
    path("<slug:slug>/", views.career_detail, name="detail"),
    path("<slug:slug>/analyze/", views.analyze, name="analyze"),
]