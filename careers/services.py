"""Business logic for the careers app."""
from careers.models import Career


def get_career_detail_data(career: Career) -> dict:
    """Build a serializable dict of a career's knowledge-base facts.

    Used by the detail view and ready to be re-used by a future REST API.
    """
    return {
        "title": career.title,
        "slug": career.slug,
        "description": career.description,
        "category": career.category,
        "difficulty": career.difficulty_label,
        "salary_range": career.salary_range,
        "demand_level": career.demand_label,
        "required_education": career.education_label,
        "future_scope": career.future_scope,
        "skills": [
            {
                "name": cs.skill.name,
                "importance": cs.importance,
                "required_level": cs.required_level,
            }
            for cs in career.career_skills.select_related("skill").order_by("-importance")
        ],
        "interests": [
            {"name": ci.interest.name, "weight": ci.weight}
            for ci in career.career_interests.select_related("interest").order_by("-weight")
        ],
        "prerequisites": [
            {"description": p.description, "priority": p.priority}
            for p in career.prerequisites.order_by("priority")
        ],
    }


def career_categories() -> list[str]:
    """Distinct career categories for the browse filters."""
    return list(Career.objects.exclude(category="").values_list("category", flat=True).distinct().order_by("category"))