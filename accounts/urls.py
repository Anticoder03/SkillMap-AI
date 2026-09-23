"""URL configuration for the accounts app."""
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    # Auth
    path("register/", views.register, name="register"),
    path("login/", views.UserLoginView.as_view(), name="login"),
    path("logout/", views.UserLogoutView.as_view(), name="logout"),
    path("password/change/", views.change_password, name="change_password"),
    # Profile
    path("profile/", views.profile, name="profile"),
    path("profile/skills/add/", views.add_skill, name="add_skill"),
    path("profile/skills/<int:skill_id>/remove/", views.remove_skill, name="remove_skill"),
    path("profile/interests/add/", views.add_interest, name="add_interest"),
    path("profile/interests/<int:interest_id>/remove/", views.remove_interest, name="remove_interest"),
    # Home / dashboard
    path("", views.landing, name="landing"),
    path("dashboard/", views.dashboard, name="dashboard"),
]