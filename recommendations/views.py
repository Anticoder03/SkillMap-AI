"""Views for the recommendation results."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Recommendation
from .services.matcher import generate_recommendations, get_recommendations


@login_required
def recommendation_list(request):
    """Show the user's top career matches as cards."""
    recommendations = get_recommendations(request.user)
    analyses = [a for a in request.user.career_analyses.filter(
        career_id__in=[r.career_id for r in recommendations]
    )]
    analysis_map = {a.career_id: a.content for a in analyses}

    return render(
        request,
        "recommendations/list.html",
        {
            "recommendations": recommendations,
            "analysis_map": analysis_map,
        },
    )


@login_required
@require_POST
def generate(request):
    """Re-run the matching engine and refresh stored recommendations."""
    count = len(generate_recommendations(request.user))
    messages.success(request, f"Generated {count} career matches for you.")
    return redirect("recommendations:list")


@login_required
def ai_analysis(request, recommendation_id: int):
    """Run (or fetch) the AI analysis for a single recommendation."""
    recommendation = get_object_or_404(Recommendation, pk=recommendation_id, user=request.user)
    from ai_engine.services.career_analyzer import analyze_career

    analyze_career(request.user, recommendation.career, recommendation)
    return redirect(request.META.get("HTTP_REFERER") or "recommendations:list")