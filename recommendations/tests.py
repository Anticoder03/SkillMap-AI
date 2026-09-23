"""Tests for the recommendation engine (scorer, matcher) and its views."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from assessment.models import Interest, Skill, UserInterest, UserSkill
from careers.models import Career, CareerInterest, CareerSkill
from recommendations.models import Recommendation
from recommendations.services.matcher import (
    build_reason,
    generate_recommendations,
    get_recommendations,
    score_career,
)
from recommendations.services.scorer import (
    education_score,
    experience_score,
    interest_score,
    preference_score,
    skill_score,
)

PASSWORD = "Str0ng!pass123"


def create_user(username: str = "rick") -> User:
    return User.objects.create_user(username=username, password=PASSWORD)


def build_career_with_requirements(career_cls, skill_names, interest_names, **career_kwargs) -> Career:
    """Create a career with the given skills (required_level 3, importance 5)
    and interests (weight 5)."""
    career = Career.objects.create(title=career_cls, **career_kwargs)
    for name in skill_names:
        skill = Skill.objects.get_or_create(name=name)[0]
        CareerSkill.objects.create(career=career, skill=skill, required_level=3, importance=5)
    for name in interest_names:
        interest = Interest.objects.get_or_create(name=name)[0]
        CareerInterest.objects.create(career=career, interest=interest, weight=5)
    return career


class InterestScoreTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.career = build_career_with_requirements(
            "Software Engineer", ["Python"], ["Coding"]
        )

    def test_no_career_interests_returns_neutral(self):
        orphan = Career.objects.create(title="Mystery Career")
        self.assertEqual(interest_score(self.user, orphan), 0.5)

    def test_no_user_interests_returns_zero(self):
        self.assertEqual(interest_score(self.user, self.career), 0.0)

    def test_full_alignment_returns_one(self):
        UserInterest.objects.create(
            user=self.user,
            interest=self.career.career_interests.first().interest,
            level=5,
        )
        self.assertEqual(interest_score(self.user, self.career), 1.0)

    def test_half_level_scales_linearly(self):
        UserInterest.objects.create(
            user=self.user,
            interest=self.career.career_interests.first().interest,
            level=2,
        )
        self.assertEqual(round(interest_score(self.user, self.career), 2), 0.4)

    def test_supports_preloaded_user_interests(self):
        interest = self.career.career_interests.first().interest
        score = interest_score(self.user, self.career, user_interests={interest.id: 5})
        self.assertEqual(score, 1.0)


class SkillScoreTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.career = build_career_with_requirements(
            "Data Engineer", ["Python", "SQL"], "Coding"
        )

    def test_no_career_skills_returns_fallback(self):
        orphan = Career.objects.create(title="Mystery Career")
        self.assertEqual(skill_score(self.user, orphan), 0.4)

    def test_career_skill_weighting(self):
        sql = self.career.career_skills.get(skill__name="SQL")
        sql.importance = 10
        sql.save()
        python = self.career.career_skills.get(skill__name="Python")

        UserSkill.objects.create(user=self.user, skill=sql.skill, proficiency=3)
        UserSkill.objects.create(user=self.user, skill=python.skill, proficiency=1)

        score = skill_score(self.user, self.career)
        # SQL fully covered (importance 10), Python 1/3 (importance 5).
        expected = (10 * 1.0 + 5 * (1 / 3)) / 15
        self.assertAlmostEqual(score, expected, places=4)


class EducationAndExperienceScoreTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.profile = self.user.profile
        self.career = build_career_with_requirements(
            "Researcher", ["Python"], "Discovery", required_education="masters", difficulty="intermediate"
        )

    def test_missing_profile_is_neutral(self):
        profileless = User.objects.create_user(username="ghost", password=PASSWORD)
        self.assertEqual(education_score(profileless, self.career), 0.5)
        self.assertEqual(experience_score(profileless, self.career), 0.5)

    def test_education_at_requirement_is_full(self):
        self.profile.education_level = "masters"
        self.profile.save()
        self.assertEqual(education_score(self.user, self.career), 1.0)

    def test_education_above_requirement_is_full(self):
        self.profile.education_level = "phd"
        self.profile.save()
        self.assertEqual(education_score(self.user, self.career), 1.0)

    def test_education_below_requirement_is_partial(self):
        self.profile.education_level = "diploma"
        self.profile.save()
        partial = education_score(self.user, self.career)
        self.assertGreaterEqual(partial, 0.0)
        self.assertLess(partial, 1.0)

    def test_matching_experience_is_full(self):
        self.profile.experience_level = "intermediate"
        self.profile.save()
        self.assertEqual(experience_score(self.user, self.career), 1.0)

    def test_far_experience_is_low(self):
        self.profile.experience_level = "expert"
        self.profile.save()
        self.assertLess(experience_score(self.user, self.career), 1.0)

    def test_preference_score_is_neutral(self):
        self.assertEqual(preference_score(self.user, self.career), 0.5)


class MatchScoringTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.career = build_career_with_requirements(
            "ML Engineer", ["Python", "PyTorch"], ["Math", "CS"]
        )
        self.profile = self.user.profile
        self.profile.education_level = "bachelors"
        self.profile.experience_level = "beginner"
        self.profile.save()

        for cs in self.career.career_skills.all():
            UserSkill.objects.create(user=self.user, skill=cs.skill, proficiency=5)
        for ci in self.career.career_interests.all():
            UserInterest.objects.create(user=self.user, interest=ci.interest, level=5)

    def test_full_match_is_high(self):
        result = score_career(self.user, self.career, self.profile)
        self.assertEqual(result["match_score"], 100)
        self.assertEqual(
            [result["subscores"]["interest"], result["subscores"]["skill"]], [100, 100]
        )

    def test_match_score_stays_in_range(self):
        for level in range(6):  # exercise multiple data points
            uc = User.objects.create_user(username=f"u{level}", password=PASSWORD)
            UserInterest.objects.create(
                user=uc, interest=self.career.career_interests.first().interest, level=level
            )
            result = score_career(uc, self.career)
            self.assertGreaterEqual(result["match_score"], 0)
            self.assertLessEqual(result["match_score"], 100)

    def test_reason_mentions_strengths(self):
        result = score_career(self.user, self.career, self.profile)
        self.assertIn("Strong interest alignment", result["reason"])

    def test_empty_user_gets_balanced_reason(self):
        uc = User.objects.create_user(username="empty", password=PASSWORD)
        result = score_career(uc, self.career)
        self.assertIn("Developing match", result["reason"])

    def test_build_reason_empty_subscores(self):
        self.assertIn("Developing match", build_reason(self.career, {"interest": 0, "skill": 0, "education": 0, "experience": 0}))


class RecommendationPersistenceTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.career_a = build_career_with_requirements(
            "Career A", ["Python"], ["Coding"], difficulty="beginner"
        )
        self.career_b = build_career_with_requirements(
            "Career B", ["Bash"], ["Web"], difficulty="expert"
        )
        self.career_c = build_career_with_requirements(
            "Career C", ["Excel"], ["Admin"], difficulty="intermediate"
        )

    def test_generates_top_recommendations_sorted(self):
        # Give the user everything for career A so it wins.
        for cs in self.career_a.career_skills.all():
            UserSkill.objects.create(user=self.user, skill=cs.skill, proficiency=5)
        recs = generate_recommendations(self.user, limit=5)
        self.assertEqual(len(recs), 3)  # only 3 careers seeded
        self.assertEqual(recs[0].career, self.career_a)
        scores = [r.match_score for r in recs]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_respects_custom_limit(self):
        recs = generate_recommendations(self.user, limit=2)
        self.assertEqual(len(recs), 2)

    def test_regeneration_replaces_old_rows(self):
        generate_recommendations(self.user, limit=5)
        first_ids = set(Recommendation.objects.filter(user=self.user).values_list("pk", flat=True))
        generate_recommendations(self.user, limit=5)
        second_ids = set(Recommendation.objects.filter(user=self.user).values_list("pk", flat=True))
        self.assertEqual(len(first_ids), 3)
        self.assertEqual(len(second_ids), 3)
        self.assertFalse(first_ids & second_ids)  # fully replaced, not duplicated

    def test_get_recommendations_generates_on_demand(self):
        self.assertFalse(Recommendation.objects.filter(user=self.user).exists())
        self.assertEqual(len(get_recommendations(self.user)), 3)

    def test_get_recommendations_returns_stored(self):
        generate_recommendations(self.user)
        recs = get_recommendations(self.user, generate_if_missing=False)
        self.assertEqual(len(recs), 3)

    def test_empty_career_list_returns_empty(self):
        Career.objects.all().delete()
        self.assertEqual(generate_recommendations(self.user), [])


class RecommendationViewTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.career = build_career_with_requirements(
            "CareerView", ["Python"], ["Coding"]
        )
        self.client.force_login(self.user)
        generate_recommendations(self.user)
        self.rec = Recommendation.objects.filter(user=self.user).first()

    def test_list_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("recommendations:list"))
        self.assertEqual(response.status_code, 302)

    def test_list_renders(self):
        response = self.client.get(reverse("recommendations:list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["recommendations"]), 1)  # single seeded career

    def test_generate_refreshes(self):
        response = self.client.post(reverse("recommendations:generate"))
        self.assertRedirects(response, reverse("recommendations:list"))
        self.assertEqual(Recommendation.objects.filter(user=self.user).count(), 1)

    def test_ai_analysis_redirects(self):
        response = self.client.post(
            reverse("recommendations:ai_analysis", args=[self.rec.id]), HTTP_REFERER=reverse("recommendations:list")
        )
        self.assertRedirects(response, reverse("recommendations:list"))

    def test_ai_analysis_blocks_other_users_recommendation(self):
        other = User.objects.create_user(username="other", password=PASSWORD)
        other_rec = Recommendation.objects.create(user=other, career=self.career, match_score=50, reason="n/a")
        response = self.client.get(reverse("recommendations:ai_analysis", args=[other_rec.id]))
        self.assertEqual(response.status_code, 404)