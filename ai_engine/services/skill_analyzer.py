"""Deterministic (non-AI) skill-gap analysis.

Used both to enrich AI output with database facts and as an automatic
fallback when the AI provider is unavailable.
"""
from __future__ import annotations

from django.contrib.auth.models import User

from careers.models import Career


def user_skill_map(user: User) -> dict[int, int]:
    """{skill_id: proficiency} for the user."""
    return {us.skill_id: us.proficiency for us in user.user_skills.select_related("skill")}


def skills_covering(career: Career) -> list:
    """Career skills ordered by importance (most important first)."""
    return list(career.career_skills.select_related("skill").order_by("-importance", "skill__name"))


def compute_strengths(user: User, career: Career, user_map: dict[int, int] | None = None) -> list[str]:
    """Skills the user already has at or above the career's required level."""
    user_map = user_map or user_skill_map(user)
    strengths = []
    for cs in skills_covering(career):
        level = user_map.get(cs.skill_id, 0)
        if level >= cs.required_level:
            strengths.append(cs.skill.name)
    # Always include explicitly-listed user skills, even without career mapping.
    strengths += [
        us.skill.name
        for us in user.user_skills.select_related("skill").order_by("-proficiency")
        if us.skill.name not in strengths
    ]
    return strengths[:15]


def compute_skill_gaps(user: User, career: Career, user_map: dict[int, int] | None = None) -> list[str]:
    """Required career skills the user is missing or under-proficient in."""
    user_map = user_map or user_skill_map(user)
    return [
        cs.skill.name
        for cs in skills_covering(career)
        if user_map.get(cs.skill_id, 0) < cs.required_level
    ]


def learning_order(user: User, career: Career, user_map: dict[int, int] | None = None) -> list[str]:
    """A sensible curriculum order: required skills by importance, skipping
    ones the user already fully covers (they can review them)."""
    user_map = user_map or user_skill_map(user)
    order = [cs.skill.name for cs in skills_covering(career) if user_map.get(cs.skill_id, 0) < 5]
    # Keep stable but deduplicated.
    return list(dict.fromkeys(order))


def build_fallback_analysis(user: User, career: Career) -> dict:
    """Produce the standard analysis schema without calling any AI."""
    user_map = user_skill_map(user)
    strengths = compute_strengths(user, career, user_map)
    gaps = compute_skill_gaps(user, career, user_map)
    order = learning_order(user, career, user_map)

    profile = getattr(user, "profile", None)
    level_labels = {
        "no_experience": "Beginner",
        "beginner": "Beginner",
        "intermediate": "Intermediate",
        "advanced": "Advanced",
        "expert": "Expert",
    }
    current_level = level_labels.get(profile.experience_level, "Beginner") if profile else "Beginner"

    if strengths and gaps:
        summary = (
            f"You already have a solid base in {', '.join(strengths[:3])} for {career.title}. "
            f"The highest-value next steps are {', '.join(gaps[:3])}."
        )
    elif strengths:
        summary = f"Your background in {', '.join(strengths[:3])} gives you a strong start toward {career.title}."
    else:
        summary = f"{career.title} is an achievable goal. Start with the fundamentals below and build up steadily."

    return {
        "career": career.title,
        "summary": summary,
        "current_level": current_level,
        "strengths": strengths,
        "skill_gaps": gaps,
        "learning_order": order,
        "projects": [],
    }