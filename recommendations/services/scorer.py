"""Rule-based scoring engine.

Computes independent sub-scores (0.0 - 1.0) for how well a user profile
matches a career across interests, skills, education and experience.

Sub-scores are agnostic of the final weighting so the weights can stay
configurable in settings.
"""
from django.contrib.auth.models import User

from accounts.models import EDUCATION_ORDER, EXPERIENCE_ORDER
from assessment.models import UserInterest, UserSkill
from careers.models import Career


def interest_score(user: User, career: Career, user_interests: dict[int, int] | None = None) -> float:
    """Score 0-1 measuring how strongly the user's interests align with the
    career's interest profile (weighted by each interest's career weight)."""
    career_interests = list(career.career_interests.select_related("interest"))
    if not career_interests:
        return 0.5

    if user_interests is None:
        user_interests = {
            ui.interest_id: ui.level
            for ui in UserInterest.objects.filter(user=user).select_related("interest")
        }

    total_weight = 0
    matched = 0.0
    for ci in career_interests:
        total_weight += ci.weight
        level = user_interests.get(ci.interest_id, 0)
        matched += ci.weight * min(level / 5.0, 1.0)

    return matched / total_weight if total_weight else 0.5


def skill_score(user: User, career: Career, user_skills: dict[int, int] | None = None) -> float:
    """Score 0-1 measuring how much of the career's required skill set the
    user already covers, weighted by each skill's importance."""
    career_skills = list(career.career_skills.select_related("skill"))
    if not career_skills:
        return 0.4

    if user_skills is None:
        user_skills = {
            us.skill_id: us.proficiency
            for us in UserSkill.objects.filter(user=user).select_related("skill")
        }

    total_importance = 0
    covered = 0.0
    for cs in career_skills:
        total_importance += cs.importance
        proficiency = user_skills.get(cs.skill_id, 0)
        # Contribution is how much of the required proficiency is met.
        ratio = proficiency / cs.required_level if cs.required_level else 0.0
        covered += cs.importance * min(ratio, 1.0)

    return covered / total_importance if total_importance else 0.4


def education_score(user: User, career: Career, profile=None) -> float:
    """Score 0-1 for education level vs the career's required education."""
    profile = profile or getattr(user, "profile", None)
    if profile is None or not profile.education_level:
        return 0.5  # Neutral when we don't know.

    user_ordinal = EDUCATION_ORDER.get(profile.education_level)
    required_ordinal = EDUCATION_ORDER.get(career.required_education)
    if user_ordinal is None:
        return 0.5

    if user_ordinal >= required_ordinal:
        return 1.0
    # Partial credit for approaching the requirement.
    return (user_ordinal + 1) / (required_ordinal + 1)


def experience_score(user: User, career: Career, profile=None) -> float:
    """Score 0-1 for how well the user's experience level fits the career's
    typical entry difficulty."""
    profile = profile or getattr(user, "profile", None)
    if profile is None or not profile.experience_level:
        return 0.5  # Neutral when we don't know.

    user_ordinal = EXPERIENCE_ORDER.get(profile.experience_level)
    career_ordinal = EXPERIENCE_ORDER.get(career.difficulty)
    if user_ordinal is None or career_ordinal is None:
        return 0.5

    distance = abs(user_ordinal - career_ordinal)
    return max(0.0, 1.0 - distance / 4.0)


def preference_score(user: User, career: Career) -> float:
    """Placeholder preference sub-score (e.g. remote/preferred location).

    Kept extensible: currently returns a neutral 0.5 because no
    preference data is collected. Add criteria here without touching
    the matcher."""
    return 0.5