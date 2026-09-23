"""Views for authentication, profiles and the dashboard."""
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from assessment.models import Interest, Skill, UserInterest, UserSkill

from .forms import RegistrationForm, UserForm, UserProfileForm
from .services import build_dashboard_context, profile_completeness


def landing(request):
    """Public marketing landing page."""
    steps = [
        ("01", "Tell us about yourself", "Create a profile with your education, experience and goals."),
        ("02", "Complete the assessment", "Answer quick questions about your interests and skills."),
        ("03", "Discover matching careers", "Get a transparent, scored list of your best-fit careers."),
        ("04", "Get your personalized roadmap", "Receive an AI-crafted learning plan and track your progress."),
    ]
    features = [
        ("wand-magic-sparkles", "AI Career Analysis", "Clear explanations of why a career fits you."),
        ("chart-column", "Skill Gap Analysis", "Know exactly what to learn next."),
        ("map-location-dot", "Personalized Roadmaps", "Phased plans with weekly goals."),
        ("gauge-high", "Progress Tracking", "Mark tasks done and watch your progress grow."),
        ("book-open", "Career Knowledge Base", "Structured data on 15+ careers."),
        ("diagram-project", "Project Recommendations", "Build portfolio projects that matter."),
    ]
    return render(request, "accounts/landing.html", {"steps": steps, "features": features})


def register(request):
    """Create a new account and log the user in."""
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome to CareerPath AI! Complete your profile to get started.")
            return redirect("accounts:profile")
    else:
        form = RegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")
    http_method_names = ["post"]


@login_required
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your password was updated successfully.")
            return redirect("accounts:profile")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, "accounts/change_password.html", {"form": form})


@login_required
def profile(request):
    """View and update the user's profile."""
    user_form = UserForm(request.POST or None, instance=request.user)
    profile_form = UserProfileForm(request.POST or None, instance=request.user.profile)

    if request.method == "POST" and user_form.is_valid() and profile_form.is_valid():
        user_form.save()
        profile_form.save()
        messages.success(request, "Your profile has been updated.")
        return redirect("accounts:profile")

    skills = request.user.user_skills.select_related("skill").order_by("skill__name")
    user_interests = request.user.user_interests.select_related("interest").order_by("interest__name")

    context = {
        "user_form": user_form,
        "profile_form": profile_form,
        "completeness": profile_completeness(request.user),
        "skills": skills,
        "user_interests": user_interests,
        "all_skills": Skill.objects.all(),
        "all_interests": Interest.objects.all(),
        "possessed_skill_ids": {us.skill_id for us in skills},
        "possessed_interest_ids": {ui.interest_id for ui in user_interests},
    }
    return render(request, "accounts/profile.html", context)


@login_required
@require_POST
def add_skill(request):
    skill = get_object_or_404(Skill, pk=request.POST.get("skill_id"))
    proficiency = max(1, min(int(request.POST.get("proficiency", 3)), 5))
    UserSkill.objects.update_or_create(
        user=request.user,
        skill=skill,
        defaults={"proficiency": proficiency},
    )
    messages.success(request, f"Added {skill.name} to your skills.")
    return redirect("accounts:profile")


@login_required
@require_POST
def remove_skill(request, skill_id: int):
    deleted, _ = UserSkill.objects.filter(user=request.user, id=skill_id).delete()
    messages.info(request, "Skill removed.") if deleted else messages.error(request, "Skill not found.")
    return redirect("accounts:profile")


@login_required
@require_POST
def add_interest(request):
    interest = get_object_or_404(Interest, pk=request.POST.get("interest_id"))
    level = max(1, min(int(request.POST.get("level", 3)), 5))
    UserInterest.objects.update_or_create(
        user=request.user,
        interest=interest,
        defaults={"level": level},
    )
    messages.success(request, f"Added {interest.name} to your interests.")
    return redirect("accounts:profile")


@login_required
@require_POST
def remove_interest(request, interest_id: int):
    deleted, _ = UserInterest.objects.filter(user=request.user, id=interest_id).delete()
    messages.info(request, "Interest removed.") if deleted else messages.error(request, "Interest not found.")
    return redirect("accounts:profile")


@login_required
def dashboard(request):
    """Personalized user dashboard."""
    context = build_dashboard_context(request.user)
    context["completeness"] = profile_completeness(request.user)
    return render(request, "accounts/dashboard.html", context)