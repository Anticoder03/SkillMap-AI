"""URL configuration for the roadmap app."""
from django.urls import path

from . import views

app_name = "roadmap"

urlpatterns = [
    path("", views.roadmap_list, name="list"),
    path("<int:pk>/", views.roadmap_detail, name="detail"),
    path("<int:pk>/task/<int:task_id>/", views.update_task, name="update_task"),
    path("<int:pk>/resources/", views.refresh_resources, name="refresh_resources"),
    path("generate/<int:career_id>/", views.generate, name="generate"),
]