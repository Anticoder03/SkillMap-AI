"""Orchestrates AI career analysis with graceful degradation.

So the app never depends on the AI being online:

1. Ask the AI provider for a structured analysis.
2. Validate + normalize the JSON.
3. Merge back database facts (ensures the DB is the source of truth).
4. On any failure, produce a deterministic analysis from the database.
"""
from __future__ import annotations

import logging
from typing import Any

from django.contrib.auth.models import User

from careers.models import Career
from recommendations.models import Recommendation

from . import skill_analyzer
from .prompt_builder import build_career_analysis_prompt
from .providers.base import AIProviderError, InvalidAIResponseError
from .provider_registry import get_provider

logger = logging.getLogger(__name__)

STATUS_LEVELS = {"Beginner", "Intermediate", "Advanced", "Expert"}

MAX_LIST_ITEMS = 12
MAX_PROJECTS = 5


def normalize_analysis(data: dict, user: User, career: Career) -> dict:
    """Validate the AI response and merge in database-derived facts."""
    analysis = {
        "career": career.title,
        "summary": str(data.get("summary") or "").strip()[:600],
        "current_level": normalize_level(data.get("current_level")),
        "strengths": clean_string_list(data.get("strengths"), MAX_LIST_ITEMS),
        "skill_gaps": clean_string_list(data.get("skill_gaps"), MAX_LIST_ITEMS),
        "learning_order": clean_string_list(data.get("learning_order"), MAX_LIST_ITEMS * 2),
        "projects": clean_projects(data.get("projects")),
    }

    user_map = skill_analyzer.user_skill_map(user)

    # The database is the source of truth: make sure key gaps and the
    # learning order always reflect the career's required skills.
    gaps = set(analysis["skill_gaps"]) | set(skill_analyzer.compute_skill_gaps(user, career, user_map))
    strengths = set(analysis["strengths"]) | set(skill_analyzer.compute_strengths(user, career, user_map))
    order = list(analysis["learning_order"])
    for skill in skill_analyzer.learning_order(user, career, user_map):
        if skill not in order:
            order.append(skill)

    analysis["strengths"] = list(dict.fromkeys(strengths))[:MAX_LIST_ITEMS]
    analysis["skill_gaps"] = list(dict.fromkeys(gaps))[:MAX_LIST_ITEMS]
    analysis["learning_order"] = list(dict.fromkeys(order))

    if not analysis["summary"]:
        analysis["summary"] = f"{career.title} matches several of your interests and skills."

    return analysis


def normalize_level(value: Any) -> str:
    """Coerce an arbitrary level value into one of the known buckets."""
    if isinstance(value, str) and value.strip().title() in STATUS_LEVELS:
        return value.strip().title()
    return "Beginner"


def clean_string_list(value: Any, limit: int) -> list[str]:
    """Return a deduplicated list of short, non-empty strings."""
    if not isinstance(value, list):
        return []
    cleaned = []
    for item in value:
        text = str(item).strip()
        if text and text not in cleaned and len(text) <= 120:
            cleaned.append(text)
        if len(cleaned) >= limit:
            break
    return cleaned


def clean_projects(value: Any) -> list[dict]:
    """Normalize the projects list into [{title, difficulty}]."""
    if not isinstance(value, list):
        return []
    projects = []
    for item in value:
        if isinstance(item, str):
            projects.append({"title": str(item)[:120], "difficulty": "Beginner"})
        elif isinstance(item, dict):
            title = str(item.get("title") or "").strip()[:120]
            difficulty = str(item.get("difficulty") or "Beginner").strip().title()
            if title:
                projects.append({"title": title, "difficulty": difficulty})
        if len(projects) >= MAX_PROJECTS:
            break
    return projects


def analyze_career(user: User, career: Career, recommendation: Recommendation | None = None, force_refresh: bool = False) -> dict:
    """Return a validated career analysis, using AI when possible.

    Results are cached in ``CareerAnalysis`` (source: 'ai' or 'fallback')
    so repeated calls only hit the provider when explicitly requested.
    """
    from ai_engine.models import CareerAnalysis

    existing = CareerAnalysis.objects.filter(user=user, career=career).first()
    if existing and existing.content and not force_refresh:
        return existing.content

    source = "ai"
    try:
        provider = get_provider()
        prompt = build_career_analysis_prompt(user, career, recommendation)
        data = provider.get_json(prompt)
        analysis = normalize_analysis(data, user, career)
    except (AIProviderError, InvalidAIResponseError) as exc:
        logger.warning("AI analysis failed for %s/%s: %s", user.username, career.title, exc)
        analysis = skill_analyzer.build_fallback_analysis(user, career)
        source = "fallback"

    if existing:
        existing.content = analysis
        existing.source = source
        existing.provider = source
        existing.save(update_fields=["content", "source", "provider", "updated_at"])
    else:
        CareerAnalysis.objects.create(
            user=user,
            career=career,
            content=analysis,
            provider=source,
            source=source,
        )
    return analysis