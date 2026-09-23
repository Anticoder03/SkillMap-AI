"""Career matching engine: combines weighted sub-scores into a final
0-100 match score and persists the top recommendations.

The score represents compatibility with the application's stored criteria.
It does NOT predict the user's future success in the career.
"""
from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction

from careers.models import Career
from recommendations.models import Recommendation

from . import scorer


def _weights() -> dict:
    default = {"interest": 0.40, "skill": 0.35, "education": 0.15, "experience": 0.10}
    weights = getattr(settings, "RECOMMENDATION_WEIGHTS", default)
    return {**default, **weights}


def score_career(user: User, career: Career, profile=None, user_interests=None, user_skills=None) -> dict:
    """Compute the full breakdown for a single user-career pair."""
    weights = _weights()

    subscores = {
        "interest": scorer.interest_score(user, career, user_interests),
        "skill": scorer.skill_score(user, career, user_skills),
        "education": scorer.education_score(user, career, profile),
        "experience": scorer.experience_score(user, career, profile),
    }

    total = sum(subscores[k] * weights[k] for k in subscores)
    final_score = round(total * 100)

    return {
        "career": career,
        "match_score": final_score,
        "subscores": {k: round(v * 100) for k, v in subscores.items()},
        "reason": build_reason(career, subscores, user_interests, user_skills),
    }


def build_reason(career: Career, subscores: dict, user_interests=None, user_skills=None) -> str:
    """Create a short human-readable explanation for a match.

    Phrases are built from the user's actual strengths rather than from
    descriptions of the career, keeping the wording honest.
    """
    parts = []
    if subscores["interest"] >= 0.6:
        parts.append("Strong interest alignment")
    if subscores["skill"] >= 0.6:
        parts.append("Good existing skill coverage")
    elif subscores["skill"] >= 0.35:
        parts.append("Foundational skills relevant to this field")
    if subscores["education"] >= 0.8:
        parts.append("Education level meets the requirements")
    if subscores["experience"] >= 0.7:
        parts.append("Experience level fits well")

    if parts:
        return "; ".join(parts) + "."
    return "Developing match — reviewing the roadmap below can help you build the required profile."


@transaction.atomic
def generate_recommendations(user: User, limit: int | None = None) -> list[Recommendation]:
    """Score every career for the user and persist the top matches.

    Existing recommendations for the user are replaced so the results
    always reflect the latest profile/assessment state.
    """
    limit = limit or int(getattr(settings, "RECOMMENDATION_LIMIT", 5))

    # Pre-load user data once for performance.
    profile = getattr(user, "profile", None)
    user_interests = {
        ui.interest_id: ui.level for ui in user.user_interests.select_related("interest").all()
    }
    user_skills = {us.skill_id: us.proficiency for us in user.user_skills.select_related("skill").all()}

    careers = Career.objects.prefetch_related("career_interests", "career_skills", "prerequisites").all()

    scored = [
        score_career(user, career, profile, user_interests, user_skills)
        for career in careers
    ]
    scored.sort(key=lambda item: item["match_score"], reverse=True)

    top = scored[:limit]

    # Replace existing recommendations.
    Recommendation.objects.filter(user=user).delete()
    recommendations = [
        Recommendation(
            user=user,
            career=item["career"],
            match_score=item["match_score"],
            reason=item["reason"],
        )
        for item in top
    ]
    Recommendation.objects.bulk_create(recommendations)

    return recommendations


def get_recommendations(user: User, generate_if_missing: bool = True) -> list[Recommendation]:
    """Fetch stored recommendations, generating them on demand if needed."""
    recommendations = list(user.recommendations.select_related("career")[: int(getattr(settings, "RECOMMENDATION_LIMIT", 5))])
    if not recommendations and generate_if_missing:
        recommendations = generate_recommendations(user)
    return recommendations