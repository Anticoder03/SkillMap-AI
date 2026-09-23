"""Tests for the accounts app: auth, profile and dashboard."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from accounts.services import LEVEL_LABELS, get_current_level, profile_completeness
from assessment.models import Interest, Skill, UserInterest, UserSkill

PASSWORD = "Str0ng!pass123"


def create_user(username: str = "alice") -> User:
    return User.objects.create_user(username=username, email=f"{username}@example.com", password=PASSWORD)


class UserProfileSignalTests(TestCase):
    def test_profile_is_auto_created(self):
        user = create_user()
        self.assertTrue(UserProfile.objects.filter(user=user).exists())

    def test_profile_deleted_with_user(self):
        user = create_user()
        user.delete()
        self.assertFalse(UserProfile.objects.filter(user__username=user.username).exists())


class RegistrationViewTests(TestCase):
    def test_register_page_renders(self):
        response = self.client.get(reverse("accounts:register"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/register.html")

    def test_valid_registration_redirects_to_profile(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "username": "bob",
                "email": "bob@example.com",
                "first_name": "Bob",
                "last_name": "Builder",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("accounts:profile"))
        self.assertTrue(User.objects.filter(username="bob").exists())

    def test_registration_creates_profile_and_logs_in(self):
        self.client.post(
            reverse("accounts:register"),
            {
                "username": "carol",
                "email": "carol@example.com",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        user = User.objects.get(username="carol")
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
        # Logged in: session auth resolves to this user.
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["user"].username, "carol")

    def test_duplicate_email_is_rejected(self):
        create_user("dave")
        response = self.client.post(
            reverse("accounts:register"),
            {"username": "dave2", "email": "dave@example.com", "password1": PASSWORD, "password2": PASSWORD},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "email", "An account with this email already exists.")

    def test_authenticated_user_is_redirected_away(self):
        self.client.force_login(create_user())
        response = self.client.get(reverse("accounts:register"))
        self.assertRedirects(response, reverse("accounts:dashboard"))


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = create_user()

    def test_login_redirects_to_dashboard(self):
        response = self.client.post(
            reverse("accounts:login"), {"username": "alice", "password": PASSWORD}
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("accounts:dashboard"))

    def test_login_rejects_bad_password(self):
        response = self.client.post(
            reverse("accounts:login"), {"username": "alice", "password": "wrong"}
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertTrue(form.errors)

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        get_response = self.client.get(reverse("accounts:logout"))
        self.assertEqual(get_response.status_code, 405)

    def test_logout_ends_session(self):
        self.client.force_login(self.user)
        self.client.post(reverse("accounts:logout"))
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(response.status_code, 302)  # redirected (logged out)


class AuthRequiredViewTests(TestCase):
    """Security: no protected page should render without login."""

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_profile_requires_login(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 302)

    def test_change_password_requires_login(self):
        response = self.client.get(reverse("accounts:change_password"))
        self.assertEqual(response.status_code, 302)


class ProfileViewTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.client.force_login(self.user)

    def test_profile_page_renders(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/profile.html")

    def test_profile_update_persists(self):
        response = self.client.post(
            reverse("accounts:profile"),
            {
                "first_name": "Alice",
                "last_name": "Wonder",
                "email": "alice@example.com",
                "education_level": "bachelors",
                "degree": "BCA",
                "college": "Test College",
                "graduation_year": "2025",
                "experience_level": "beginner",
                "bio": "Learning to code",
                "location": "Pune",
            },
        )
        self.assertRedirects(response, reverse("accounts:profile"))
        self.user.refresh_from_db()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.first_name, "Alice")
        self.assertEqual(self.user.profile.education_level, "bachelors")
        self.assertEqual(self.user.profile.location, "Pune")

    def test_invalid_graduation_year_rejected(self):
        response = self.client.post(
            reverse("accounts:profile"),
            {
                "email": "alice@example.com",
                "education_level": "bachelors",
                "graduation_year": "1800",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["profile_form"], "graduation_year", "Enter a valid graduation year."
        )

    def test_skill_management(self):
        skill = Skill.objects.create(name="Python", category="programming")
        response = self.client.post(reverse("accounts:add_skill"), {"skill_id": skill.id, "proficiency": 4})
        self.assertRedirects(response, reverse("accounts:profile"))
        us = UserSkill.objects.get(user=self.user, skill=skill)
        self.assertEqual(us.proficiency, 4)

        # Re-add with new proficiency updates instead of duplicating.
        self.client.post(reverse("accounts:add_skill"), {"skill_id": skill.id, "proficiency": 5})
        self.assertEqual(UserSkill.objects.filter(user=self.user, skill=skill).count(), 1)
        self.assertEqual(UserSkill.objects.get(user=self.user, skill=skill).proficiency, 5)

        # Remove clears the record (URL takes the UserSkill id).
        self.client.post(reverse("accounts:remove_skill", args=[us.id]))
        self.assertFalse(UserSkill.objects.filter(user=self.user, skill=skill).exists())

    def test_interest_management(self):
        interest = Interest.objects.create(name="AI/ML", description="Artificial intelligence")
        self.client.post(reverse("accounts:add_interest"), {"interest_id": interest.id, "level": 5})
        ui = UserInterest.objects.get(user=self.user, interest=interest)
        self.assertEqual(ui.level, 5)
        self.client.post(reverse("accounts:remove_interest", args=[ui.id]))
        self.assertFalse(UserInterest.objects.filter(user=self.user, interest=interest).exists())


class ChangePasswordTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.client.force_login(self.user)

    def test_password_change_succeeds(self):
        response = self.client.post(
            reverse("accounts:change_password"),
            {"old_password": PASSWORD, "new_password1": "New!pass123", "new_password2": "New!pass123"},
        )
        # Password change invalidates the session, so we only assert the redirect.
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("New!pass123"))


class DashboardViewTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.client.force_login(self.user)

    def test_dashboard_renders_with_chart_data(self):
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(response.status_code, 200)
        context = response.context
        self.assertIn("recommendations", context)
        self.assertIn("chart_skills", context)
        self.assertIn("chart_matches", context)
        self.assertIn("chart_roadmap", context)
        self.assertEqual(context["chart_skills"]["labels"], [])

    def test_dashboard_aggregates_skills_and_roadmap_chart(self):
        Skill.objects.create(name="Django")
        s = Skill.objects.create(name="Git")
        UserSkill.objects.create(user=self.user, skill=s, proficiency=3)
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(response.context["chart_skills"]["data"], [3])


class ProfileCompletenessTests(TestCase):
    def test_empty_profile_is_zero_percent(self):
        user = create_user()
        data = profile_completeness(user)
        self.assertEqual(data["percent"], 0)

    def test_full_profile_is_fully_complete(self):
        user = create_user()
        user.profile.education_level = "bachelors"
        user.profile.save()
        UserSkill.objects.create(user=user, skill=Skill.objects.create(name="Git"), proficiency=3)
        UserInterest.objects.create(
            user=user, interest=Interest.objects.create(name="Data"), level=3
        )
        from assessment.models import Assessment
        Assessment.objects.create(user=user, is_completed=True)
        data = profile_completeness(user)
        self.assertEqual(data["percent"], 100)

    def test_get_current_level_falls_back_to_profile(self):
        user = create_user()
        user.profile.experience_level = "intermediate"
        user.profile.save()
        self.assertEqual(get_current_level(user), LEVEL_LABELS["intermediate"])

    def test_get_current_level_default_for_missing_profile(self):
        user = create_user()
        self.assertEqual(get_current_level(user), "Beginner")