"""Business logic for the accounts app (profile + dashboard aggregation)."""
from django.contrib.auth.models import User

# Keep reward lookups close to the UI so views stay thin.
LEVEL_LABELS = {
    "no_experience": "No Experience",
    "beginner": "Beginner",
    "intermediate": "Intermediate",
    "advanced": "Advanced",
    "expert": "Expert",
}


def get_current_level(user: User) -> str:
    """Determine the user's current level label.

    Prefers the AI-derived level for the top career when available,
    otherwise falls back to the profile experience level.
    """
    top = user.recommendations.select_related("career").order_by("-match_score").first()
    if top:
        analysis = user.career_analyses.filter(career=top.career).first()
        if analysis and analysis.content.get("current_level"):
            return analysis.content["current_level"]
    profile = getattr(user, "profile", None)
    if profile and profile.experience_level:
        return LEVEL_LABELS.get(profile.experience_level, profile.experience_level)
    return "Beginner"


def build_dashboard_context(user: User) -> dict:
    """Aggregate everything needed to render the user's dashboard."""
    recommendations = list(
        user.recommendations.select_related("career").order_by("-match_score")[:5]
    )
    top_recommendation = recommendations[0] if recommendations else None

    roadmap = (
        user.roadmaps.select_related("career")
        .prefetch_related("phases__tasks")
        .order_by("-created_at")
        .first()
    )

    analyses = {a.career_id: a for a in user.career_analyses.all()}

    skills = list(user.user_skills.select_related("skill").order_by("skill__name"))
    interests = list(user.user_interests.select_related("interest").order_by("interest__name"))

    return {
        "recommendations": recommendations,
        "top_recommendation": top_recommendation,
        "roadmap": roadmap,
        "analyses": analyses,
        "skills": skills,
        "interests": interests,
        "current_level": get_current_level(user),
        "chart_skills": {"labels": [s.skill.name for s in skills], "data": [s.proficiency for s in skills]},
        "chart_matches": {
            "labels": [r.career.title for r in recommendations],
            "data": [r.match_score for r in recommendations],
        },
        "chart_roadmap": {
            "completed": roadmap.completed_tasks if roadmap else 0,
            "total": roadmap.total_tasks if roadmap else 0,
            "percent": roadmap.progress if roadmap else 0.0,
        },
        "recent_tasks": _recent_tasks(roadmap),
    }


def _recent_tasks(roadmap) -> list:
    """Flatten the latest roadmap into ordered tasks for display."""
    if not roadmap:
        return []
    tasks = []
    for phase in roadmap.phases.all().prefetch_related("tasks"):
        for task in phase.tasks.all():
            tasks.append({"task": task, "phase": phase})
    return tasks[:10]


def profile_completeness(user: User) -> dict:
    """Return a checklist of profile/network readiness fields."""
    profile = getattr(user, "profile", None)
    checks = {
        "profile": bool(profile and profile.education_level),
        "interests": user.user_interests.exists(),
        "skills": user.user_skills.exists(),
        "assessment": user.assessments.filter(is_completed=True).exists(),
    }
    completed = sum(1 for v in checks.values() if v)
    return {"checks": checks, "percent": round(completed / len(checks) * 100), "count": f"{completed}/{len(checks)}"}