"""Tests for roadmaps: generation (AI-first with fallback) and progress."""
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from ai_engine.services.provider_registry import get_provider
from ai_engine.services.providers.base import AIProviderError
from ai_engine.services.roadmap_generator import (
    MAX_PHASE_TASKS,
    _clean_phases,
    _clean_tasks,
    build_fallback_roadmap_data,
    generate_roadmap,
)
from assessment.models import Skill
from careers.models import Career, CareerSkill
from roadmap.models import Roadmap, RoadmapPhase, RoadmapTask, TASK_STATUSES
from roadmap.views import update_task

PASSWORD = "Str0ng!pass123"


def create_user(username: str = "mark") -> User:
    return User.objects.create_user(username=username, password=PASSWORD)


def create_career() -> Career:
    career = Career.objects.create(title="Frontend Engineer", required_education="diploma")
    for name in ["HTML", "CSS", "JavaScript", "React", "Git"]:
        skill = Skill.objects.create(name=name, category="web")
        CareerSkill.objects.create(career=career, skill=skill, importance=5, required_level=3)
    return career


def build_roadmap(user: User, career: Career) -> Roadmap:
    roadmap = Roadmap.objects.create(
        user=user, career=career, title=f"{career.title} Roadmap", duration_weeks=8
    )
    phase = RoadmapPhase.objects.create(roadmap=roadmap, title="Core", order=0, duration_weeks=2)
    for idx in range(3):
        RoadmapTask.objects.create(phase=phase, title=f"Task {idx}", order=idx)
    return roadmap


class RoadmapModelTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.career = create_career()
        self.roadmap = build_roadmap(self.user, self.career)

    def test_task_defaults_to_not_started(self):
        task = self.roadmap.phases.first().tasks.first()
        self.assertEqual(task.status, "not_started")
        self.assertFalse(task.is_completed)

    def test_task_completion_flag(self):
        task = self.roadmap.phases.first().tasks.first()
        task.status = "completed"
        self.assertTrue(task.is_completed)

    def test_total_and_completed_counts(self):
        self.assertEqual(self.roadmap.total_tasks, 3)
        self.assertEqual(self.roadmap.completed_tasks, 0)

    def test_progress_matches_completed_ratio(self):
        tasks = list(self.roadmap.phases.first().tasks.all())
        tasks[0].status = "completed"
        tasks[0].save(update_fields=["status"])
        self.roadmap = Roadmap.objects.get(pk=self.roadmap.pk)
        self.assertEqual(self.roadmap.progress, round(1 / 3 * 100, 1))
        self.assertEqual(self.roadmap.completed_tasks, 1)

    def test_phase_progress(self):
        phase = self.roadmap.phases.first()
        tasks = list(phase.tasks.all())
        tasks[0].status = "completed"
        tasks[0].save(update_fields=["status"])
        self.assertEqual(phase.progress, round(1 / 3 * 100, 1))

    def test_unique_user_career_roadmap(self):
        with self.assertRaises(Exception):
            Roadmap.objects.create(
                user=self.user, career=self.career, title="Duplicate", duration_weeks=4
            )

    def test_career_is_required(self):
        with self.assertRaises(Exception):
            Roadmap.objects.create(user=self.user, title="No career")


class RoadmapGenerationTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.career = create_career()

    def test_clean_tasks_normalizes_mixed_input(self):
        raw = [{"title": "Learn X"}, "Plain task", {"title": ""}, {"title": "Learn X"}]
        self.assertEqual(_clean_tasks(raw), ["Learn X", "Plain task"])

    def test_clean_tasks_respects_limit(self):
        raw = [f"task-{i}" for i in range(50)]
        self.assertEqual(len(_clean_tasks(raw)), MAX_PHASE_TASKS)

    def test_clean_phases_rejects_non_list(self):
        with self.assertRaises(Exception):
            _clean_phases({"phases": "nope"})

    def test_build_fallback_roadmap_data(self):
        data = build_fallback_roadmap_data(self.career, self.user)
        self.assertIn("phases", data)
        self.assertGreaterEqual(len(data["phases"]), 2)  # skill phases + portfolio phase
        tasks = [t for phase in data["phases"] for t in phase["tasks"]]
        self.assertIn("HTML", tasks)
        self.assertIn("Portfolio Projects", data["phases"][-1]["title"])

    def test_generate_roadmap_uses_database_fallback(self):
        # No provider key configured -> provider errors -> deterministic fallback.
        roadmap = generate_roadmap(self.user, self.career)
        self.assertEqual(roadmap.user, self.user)
        self.assertEqual(roadmap.career, self.career)
        self.assertGreater(roadmap.phases.count(), 0)
        self.assertGreater(roadmap.total_tasks, 0)
        self.assertEqual(roadmap.progress, 0.0)

    def test_generated_tasks_get_curated_resources(self):
        # Even without an AI key, every task should end up with a safe link.
        roadmap = generate_roadmap(self.user, self.career)
        tasks = list(RoadmapTask.objects.filter(phase__roadmap=roadmap))
        self.assertGreater(len(tasks), 0)
        for task in tasks:
            self.assertTrue(task.resource_url.startswith("https"))
            self.assertIsNotNone(task.resource_url)

    @override_settings(AI_PROVIDER="badname", AI_PROVIDERS={"good": "x.Y"}, AI_API_KEY="")
    def test_unconfigured_provider_still_falls_back(self):
        roadmap = generate_roadmap(self.user, self.career)
        self.assertGreater(roadmap.phases.count(), 0)

    @override_settings(AI_PROVIDER="fake", AI_PROVIDERS={"fake": "ai_engine.tests.FakeProvider"}, AI_API_KEY="k")
    def test_ai_roadmap_is_used_when_provider_succeeds(self):
        from ai_engine.tests import FakeProvider

        FakeProvider.error = None
        FakeProvider.payload = {
            "title": "Custom Roadmap",
            "description": "AI generated plan",
            "duration_weeks": 12,
            "phases": [
                {"title": "Phase One", "description": "Start", "duration_weeks": 3, "tasks": ["t1", "t2"]},
                {"title": "Phase Two", "description": "Next", "duration_weeks": 2, "tasks": ["t3"]},
            ],
        }
        roadmap = generate_roadmap(self.user, self.career)
        self.assertEqual(roadmap.title, "Custom Roadmap")
        self.assertEqual(roadmap.phases.count(), 2)
        self.assertEqual(roadmap.phases.first().tasks.count(), 2)
        self.assertEqual(roadmap.total_tasks, 3)

    @override_settings(AI_PROVIDER="fake", AI_PROVIDERS={"fake": "ai_engine.tests.FakeProvider"}, AI_API_KEY="k")
    def test_regeneration_replaces_phases(self):
        from ai_engine.tests import FakeProvider

        FakeProvider.error = None
        FakeProvider.payload = {
            "title": "First Roadmap",
            "phases": [{"title": "P1", "tasks": ["a", "b"]}],
        }
        first = generate_roadmap(self.user, self.career)
        first_phase_ids = set(first.phases.values_list("pk", flat=True))

        FakeProvider.payload = {
            "title": "Second Roadmap",
            "phases": [{"title": "P1", "tasks": ["a", "b", "c"]}],
        }
        second = generate_roadmap(self.user, self.career, force_refresh=True)

        self.assertEqual(second.pk, first.pk)  # same row updated
        self.assertEqual(second.title, "Second Roadmap")
        self.assertFalse(set(second.phases.values_list("pk", flat=True)) & first_phase_ids)  # phases replaced

    def test_generate_roadmap_same_career_updates_not_duplicates(self):
        build_roadmap(self.user, self.career)
        roadmap = generate_roadmap(self.user, self.career)
        self.assertEqual(Roadmap.objects.filter(user=self.user, career=self.career).count(), 1)
        self.assertEqual(roadmap.pk, self.user.roadmaps.first().pk)


class RoadmapViewTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.other = create_user("other")
        self.career = create_career()
        self.roadmap = build_roadmap(self.user, self.career)
        self.task = self.roadmap.phases.first().tasks.first()
        self.client.force_login(self.user)

    def test_list_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("roadmap:list"))
        self.assertEqual(response.status_code, 302)

    def test_list_lists_only_own_roadmaps(self):
        response = self.client.get(reverse("roadmap:list"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.roadmap, response.context["roadmaps"])

    def test_detail_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("roadmap:detail", args=[self.roadmap.id]))
        self.assertEqual(response.status_code, 302)

    def test_detail_renders_chart(self):
        response = self.client.get(reverse("roadmap:detail", args=[self.roadmap.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["phases"]), 1)

    def test_detail_blocks_other_users_roadmap(self):
        roadmap = build_roadmap(self.other, self.career)
        response = self.client.get(reverse("roadmap:detail", args=[roadmap.id]))
        self.assertEqual(response.status_code, 404)

    def test_update_task_marks_completed(self):
        response = self.client.post(
            reverse("roadmap:update_task", args=[self.roadmap.id, self.task.id]),
            {"status": "completed"},
        )
        self.assertRedirects(response, reverse("roadmap:detail", args=[self.roadmap.id]))
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "completed")

    def test_update_task_invalid_status_rejected(self):
        response = self.client.post(
            reverse("roadmap:update_task", args=[self.roadmap.id, self.task.id]),
            {"status": "bogus"},
        )
        self.assertRedirects(response, reverse("roadmap:detail", args=[self.roadmap.id]))
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "not_started")

    def test_update_task_requires_post(self):
        response = self.client.get(reverse("roadmap:update_task", args=[self.roadmap.id, self.task.id]))
        self.assertEqual(response.status_code, 405)

    def test_update_task_blocked_for_other_user(self):
        roadmap = build_roadmap(self.other, self.career)
        task = roadmap.phases.first().tasks.first()
        response = self.client.post(
            reverse("roadmap:update_task", args=[roadmap.id, task.id]), {"status": "completed"}
        )
        self.assertEqual(response.status_code, 404)

    @mock.patch("ai_engine.services.roadmap_generator.get_provider")
    def test_generate_redirects_to_detail(self, mock_provider):
        from ai_engine.services.providers.base import AIProviderError

        mock_provider.side_effect = AIProviderError("down")
        response = self.client.post(reverse("roadmap:generate", args=[self.career.id]))
        roadmap = Roadmap.objects.get(user=self.user, career=self.career)
        self.assertRedirects(response, reverse("roadmap:detail", args=[roadmap.id]))
        self.assertGreater(roadmap.total_tasks, 0)

    def test_refresh_resources_populates_links(self):
        # No AI configured: the endpoint falls back to curated resources.
        response = self.client.post(reverse("roadmap:refresh_resources", args=[self.roadmap.id]))
        self.assertRedirects(response, reverse("roadmap:detail", args=[self.roadmap.id]))
        self.task.refresh_from_db()
        self.assertTrue(self.task.resource_url.startswith("https"))

    def test_video_fields_default_empty(self):
        # Without SerpAPI/YouTube data, tasks have a resource but no video.
        self.assertEqual(self.task.video_url, "")
        self.assertEqual(self.task.video_title, "")
        self.client.post(reverse("roadmap:refresh_resources", args=[self.roadmap.id]))
        self.task.refresh_from_db()
        self.assertTrue(self.task.resource_url.startswith("https"))
        self.assertEqual(self.task.video_url, "")

    def test_refresh_resources_requires_login(self):
        self.client.logout()
        response = self.client.post(reverse("roadmap:refresh_resources", args=[self.roadmap.id]))
        self.assertEqual(response.status_code, 302)

    def test_refresh_resources_requires_post(self):
        response = self.client.get(reverse("roadmap:refresh_resources", args=[self.roadmap.id]))
        self.assertEqual(response.status_code, 405)

    def test_refresh_resources_blocked_for_other_user(self):
        roadmap = build_roadmap(self.other, self.career)
        response = self.client.post(reverse("roadmap:refresh_resources", args=[roadmap.id]))
        self.assertEqual(response.status_code, 404)

    def test_generate_requires_login(self):
        self.client.logout()
        response = self.client.post(reverse("roadmap:generate", args=[self.career.id]))
        self.assertEqual(response.status_code, 302)

    def test_task_statuses_choices_match(self):
        self.assertEqual(
            {s for s, _ in TASK_STATUSES}, {"not_started", "in_progress", "completed"}
        )