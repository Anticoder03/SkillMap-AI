"""Roadmap generation: AI-first with a database-driven fallback.

The AI may propose a rich roadmap; if it fails we build one straight
from the career knowledge base so users always get a usable plan.
"""
from __future__ import annotations

import logging
from typing import Any

from django.contrib.auth.models import User
from django.db import transaction

from careers.models import Career

from . import skill_analyzer
from .career_analyzer import analyze_career
from .prompt_builder import build_roadmap_prompt
from .providers.base import AIProviderError, InvalidAIResponseError
from .provider_registry import get_provider
from . import resource_finder

logger = logging.getLogger(__name__)

MAX_PHASES = 8
MAX_PHASE_TASKS = 12

DEFAULT_HOURS_PER_TASK = 3

# Semantic phase labels used by the deterministic fallback.
PHASE_NAMES = ["Foundations", "Core Skills", "Skill Building", "Advanced Topics", "Applied Projects"]


def _clean_tasks(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    tasks = []
    for item in value:
        if isinstance(item, dict):
            text = str(item.get("title") or item.get("name") or "").strip()
        else:
            text = str(item).strip()
        if text and text not in tasks and len(text) <= 180:
            tasks.append(text)
        if len(tasks) >= MAX_PHASE_TASKS:
            break
    return tasks


def _clean_phases(value: Any) -> list[dict]:
    """Normalize AI roadmap JSON into a strict internal structure."""
    if not isinstance(value, list):
        raise InvalidAIResponseError("Roadmap 'phases' must be a list.")
    phases = []
    for item in value[:MAX_PHASES]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()[:150]
        if not title:
            continue
        tasks = _clean_tasks(item.get("tasks"))
        if not tasks:
            continue
        phases.append(
            {
                "title": title,
                "description": str(item.get("description") or "").strip()[:500],
                "duration_weeks": int(item.get("duration_weeks") or 2) or 2,
                "tasks": tasks,
            }
        )
    if not phases:
        raise InvalidAIResponseError("Roadmap contained no usable phases.")
    return phases


def build_fallback_roadmap_data(career: Career, user: User | None = None) -> dict:
    """Deterministic roadmap built from the career's required skills."""
    career_skills = list(career.career_skills.select_related("skill").order_by("-importance"))
    total_weeks = max(4, len(career_skills) * 2)

    # Group skills into phases of ~4.
    chunk_size = 4 if len(career_skills) > 4 else max(len(career_skills), 1)
    skill_chunks = [career_skills[i : i + chunk_size] for i in range(0, len(career_skills), chunk_size)]

    phases = []
    for idx, chunk in enumerate(skill_chunks):
        name = PHASE_NAMES[idx] if idx < len(PHASE_NAMES) else f"Phase {idx + 1}"
        phases.append(
            {
                "title": f"{name}",
                "description": f"Build a solid foundation in the core skills required for {career.title}.",
                "duration_weeks": max(1, len(chunk) * 2),
                "tasks": [cs.skill.name for cs in chunk],
            }
        )

    # Final phase: apply everything through projects.
    phases.append(
        {
            "title": "Portfolio Projects",
            "description": "Consolidate your learning by building real projects you can show employers.",
            "duration_weeks": max(2, len(career_skills)),
            "tasks": [
                f"Build a beginner project using {career_skills[0].skill.name}" if career_skills else "Build your first portfolio project",
                "Publish your work to GitHub",
                "Write a short write-up explaining your project choices",
            ],
        }
    )

    return {
        "title": f"{career.title} Roadmap",
        "description": f"Personalized learning plan toward becoming a {career.title}.",
        "duration_weeks": total_weeks,
        "phases": phases,
    }


@transaction.atomic
def generate_roadmap(user: User, career: Career, force_refresh: bool = False):
    """Create or replace the user's roadmap for a career and return it."""
    from roadmap.models import Roadmap, RoadmapPhase, RoadmapTask

    # Get (or generate) the analysis first so the roadmap reflects it.
    analysis = analyze_career(user, career, force_refresh=force_refresh)

    data = None
    try:
        provider = get_provider()
        prompt = build_roadmap_prompt(user, career, analysis)
        raw = provider.get_json(prompt)
        data = {
            "title": str(raw.get("title") or f"{career.title} Roadmap")[:200],
            "description": str(raw.get("description") or "").strip()[:500],
            "duration_weeks": int(raw.get("duration_weeks") or 0),
            "phases": _clean_phases(raw.get("phases")),
        }
    except (AIProviderError, InvalidAIResponseError, ValueError) as exc:
        logger.warning("AI roadmap failed for %s/%s, using fallback: %s", user.username, career.title, exc)
        data = None

    if data is None:
        data = build_fallback_roadmap_data(career, user)

    total_weeks = sum(p["duration_weeks"] for p in data["phases"]) or data["duration_weeks"]
    if not total_weeks:
        total_weeks = len(data["phases"]) * 4

    roadmap, _created = Roadmap.objects.update_or_create(
        user=user,
        career=career,
        defaults={
            "title": data["title"],
            "description": data["description"] or f"Personalized learning plan toward {career.title}.",
            "duration_weeks": total_weeks,
        },
    )

    # Replace phases/tasks to keep them in sync with the latest generation.
    roadmap.phases.all().delete()
    for order, phase_data in enumerate(data["phases"]):
        phase = RoadmapPhase.objects.create(
            roadmap=roadmap,
            title=phase_data["title"],
            description=phase_data["description"],
            order=order,
            duration_weeks=phase_data["duration_weeks"],
        )
        RoadmapTask.objects.bulk_create(
            [
                RoadmapTask(
                    phase=phase,
                    title=task_title,
                    description="",
                    estimated_hours=DEFAULT_HOURS_PER_TASK,
                    order=idx,
                )
                for idx, task_title in enumerate(phase_data["tasks"])
            ]
        )

    # Attach a validated, real learning resource to every task (AI-first,
    # curated fallback). Never lets a roadmap return without resources.
    try:
        resource_finder.enrich_roadmap_with_resources(user, career, roadmap)
    except Exception as exc:  # noqa: BLE001 - enrichment must never break the roadmap
        logger.warning("Resource enrichment failed for %s/%s: %s", user.username, career.title, exc)

    return roadmap