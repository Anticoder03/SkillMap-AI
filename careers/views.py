"""Views for browsing the career knowledge base."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Career
from .services import career_categories, get_career_detail_data


def career_list(request):
    """Browse careers with optional text search and category filter."""
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()

    careers = Career.objects.all()
    if query:
        careers = careers.filter(
            Q(title__icontains=query)
            | Q(category__icontains=query)
            | Q(description__icontains=query)
            | Q(career_skills__skill__name__icontains=query)
        ).distinct()
    if category:
        careers = careers.filter(category=category)

    return render(
        request,
        "careers/list.html",
        {
            "careers": careers,
            "query": query,
            "active_category": category,
            "categories": career_categories(),
        },
    )


def career_detail(request, slug: str):
    """Full detail page for one career."""
    career = get_object_or_404(Career, slug=slug)
    data = get_career_detail_data(career)

    user_analysis = None
    user_roadmap = None
    if request.user.is_authenticated:
        user_analysis = request.user.career_analyses.filter(career=career).first()
        user_roadmap = request.user.roadmaps.filter(career=career).first()

    return render(
        request,
        "careers/detail.html",
        {
            "career": career,
            "data": data,
            "analysis": user_analysis.content if user_analysis else None,
            "user_roadmap": user_roadmap,
        },
    )


@login_required
@require_POST
def analyze(request, slug: str):
    """Run the AI analysis (with database fallback) for a career."""
    from ai_engine.services.career_analyzer import analyze_career

    career = get_object_or_404(Career, slug=slug)
    analyze_career(request.user, career, force_refresh="refresh" in request.POST)
    messages.success(request, f"Analysis ready for {career.title}.")
    return redirect("careers:detail", slug=slug)