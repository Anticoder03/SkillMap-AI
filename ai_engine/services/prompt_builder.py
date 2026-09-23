"""Builds the structured payloads and prompts sent to AI providers.

Business rules (what data is sent) live here so views never assemble
prompts or touch provider APIs directly.
"""
from __future__ import annotations

import json
from typing import Any

from django.contrib.auth.models import User


def build_profile_payload(user: User) -> dict:
    """Structured JSON describing a user for AI analysis."""
    profile = getattr(user, "profile", None)
    interests = [
        {"name": ui.interest.name, "level": ui.level}
        for ui in user.user_interests.select_related("interest").order_by("-level")
    ]
    skills = [
        {"name": us.skill.name, "proficiency": us.proficiency}
        for us in user.user_skills.select_related("skill").order_by("-proficiency")
    ]
    return {
        "education": profile.education_level if profile else "",
        "experience_level": profile.experience_level if profile else "",
        "degree": profile.degree if profile else "",
        "bio": profile.bio if profile else "",
        "interests": interests,
        "skills": skills,
    }


def build_career_facts(career) -> dict:
    """Structured, database-backed facts about a career.

    The AI is told to use these as the source of truth instead of
    inventing its own facts.
    """
    return {
        "title": career.title,
        "description": career.description,
        "category": career.category,
        "difficulty": career.difficulty_label,
        "salary_range": career.salary_range,
        "demand_level": career.demand_label,
        "required_education": career.education_label,
        "future_scope": career.future_scope,
        "required_skills": [
            {
                "name": cs.skill.name,
                "importance": cs.importance,
                "required_level": cs.required_level,
            }
            for cs in career.career_skills.select_related("skill").order_by("-importance")
        ],
        "related_interests": [
            {"name": ci.interest.name, "weight": ci.weight}
            for ci in career.career_interests.select_related("interest").order_by("-weight")
        ],
        "prerequisites": [p.description for p in career.prerequisites.order_by("priority")],
    }


def build_career_analysis_prompt(user: User, career, recommendation=None, analysis_facts: dict | None = None) -> str:
    """Prompt asking the AI for a structured career analysis.

    Database facts are injected so the AI explains rather than invents.
    """
    profile_payload = build_profile_payload(user)
    career_facts = analysis_facts or build_career_facts(career)
    match = recommendation.match_score if recommendation else None

    return f"""You are an expert career counselor for a learning platform.

Use ONLY the structured information below. Do not invent career facts,
salaries, or job statistics that are not present.

USER PROFILE (JSON):
{json.dumps(profile_payload, indent=2)}

CAREER FACTS (JSON):
{json.dumps(career_facts, indent=2)}

MATCH SCORE (0-100, engine result): {match}

Your task: analyze how well this career fits the user and produce a
personalized learning analysis.

Return STRICT JSON with EXACTLY this shape (no extra fields, no markdown):
{{
  "career": "{career.title}",
  "summary": "2-3 sentence personalized explanation of why this career fits the user.",
  "current_level": "Beginner | Intermediate | Advanced | Expert",
  "strengths": ["existing strength 1", "existing strength 2"],
  "skill_gaps": ["missing skill 1", "missing skill 2"],
  "learning_order": ["item 1", "item 2", "item 3"],
  "projects": [
    {{"title": "Project 1", "difficulty": "Beginner"}},
    {{"title": "Project 2", "difficulty": "Intermediate"}}
  ]
}}

Constraints:
- skill_gaps and learning_order must build on the career's required_skills.
- projects must be realistic for the user's current_level.
- Respond with valid JSON only."""


def build_roadmap_prompt(user: User, career, analysis: dict | None = None) -> str:
    """Prompt asking the AI for a structured learning roadmap."""
    profile_payload = build_profile_payload(user)
    career_facts = build_career_facts(career)
    analysis_summary = {
        key: (analysis or {}).get(key, [])
        for key in ["strengths", "skill_gaps", "learning_order", "projects", "current_level"]
    }

    return f"""You are a curriculum designer for a single user.

USER PROFILE (JSON):
{json.dumps(profile_payload, indent=2)}

CAREER FACTS (JSON):
{json.dumps(career_facts, indent=2)}

PRIOR ANALYSIS (JSON):
{json.dumps(analysis_summary, indent=2)}

Create a personalized learning roadmap to become a "{career.title}".

Return STRICT JSON with EXACTLY this shape:
{{
  "title": "Roadmap title",
  "description": "Short description of the journey",
  "duration_weeks": 24,
  "phases": [
    {{
      "title": "Phase 1 title",
      "description": "What the phase covers",
      "duration_weeks": 4,
      "tasks": ["concrete task A", "concrete task B", "concrete task C"]
    }}
  ]
}}

Rules:
- 4-6 phases, ordered from fundamentals to advanced, based on learning_order.
- Each phase has 3-8 concrete, actionable tasks.
- Total duration_weeks should roughly equal the sum of phase durations.
- Respond with valid JSON only."""


def build_resources_prompt(user: User, career, roadmap) -> str:
    """Prompt asking the AI for a real, free learning resource per task.

    The roadmap's phase/task titles are sent so resources match the plan
    exactly; the AI must never invent tasks or URLs. A YouTube video is
    requested as an optional best-effort extra per task.
    """
    career_facts = build_career_facts(career)
    phases = [
        {
            "phase": phase.title,
            "tasks": [task.title for task in phase.tasks.order_by("order", "id")],
        }
        for phase in roadmap.phases.order_by("order", "id")
    ]

    return f"""You are a learning-curation specialist for a single user.

CAREER FACTS (JSON, source of truth):
{json.dumps(career_facts, indent=2)}

LEARNING ROADMAP (JSON):
{json.dumps({"title": roadmap.title, "phases": phases}, indent=2)}

For EVERY task in EVERY phase, recommend ONE free, well-known learning
resource that teaches exactly that task's skill. Optionally also suggest ONE
well-known YouTube video tutorial that teaches the same task.

Return STRICT JSON with EXACTLY this shape (no extra fields, no markdown):
{{
  "resources": [
    {{
      "phase": "exact phase title from the roadmap",
      "task": "exact task title from the roadmap",
      "resource_title": "Human-readable name of the resource",
      "resource_url": "https://example.com/the-resource",
      "description": "One sentence on why this resource helps this task",
      "video_title": "Title of a well-known YouTube video, or leave empty",
      "video_url": "https://www.youtube.com/watch?v=VIDEO_ID or leave empty"
    }}
  ]
}}

Rules:
- One entry per task; include every task from the roadmap.
- Prefer official docs, MDN, freeCodeCamp, interactive tutorials, or reputable
  free courses. NO paywalled, unverified, or dead URLs.
- ``resource_url`` must be a real, direct https URL to the resource.
- ``video_url`` is OPTIONAL — only provide a real, well-known YouTube watch
  link you are sure exists (``youtube.com/watch`` or ``youtu.be``); otherwise
  leave it as an empty string.
- Use the exact titles from the roadmap for ``phase`` and ``task``.
- Respond with valid JSON only."""