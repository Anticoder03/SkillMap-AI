"""Views for the AI engine.

Exposes the analysis results as JSON so the templates, and a future React
frontend, consume the same endpoint.
"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from careers.models import Career


@login_required
def analysis_json(request, career_id: int):
    """Return (generating if needed) the structured analysis for a career."""
    from ai_engine.services.career_analyzer import analyze_career

    career = get_object_or_404(Career, pk=career_id)
    analysis = analyze_career(request.user, career)
    return JsonResponse(analysis, safe=False)