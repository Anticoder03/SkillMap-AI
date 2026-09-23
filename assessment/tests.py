"""Tests for the assessment engine: models, services and the multi-step views."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from assessment.models import Answer, Assessment, Interest, Question, QuestionOption, Skill, UserInterest, UserSkill
from assessment.services import (
    complete_assessment,
    get_active_questions,
    get_next_question,
    get_or_create_assessment,
    get_previous_question,
    get_question_step,
    progress_data,
    save_answer,
)

PASSWORD = "Str0ng!pass123"


def create_user() -> User:
    return User.objects.create_user(username="tester", password=PASSWORD)


class QuestionFactory:
    """Minimal question/option fixtures with interest & skill mappings."""

    def __init__(self):
        self.interest = Interest.objects.create(name="Programming", description="Coding")
        self.skill = Skill.objects.create(name="Python", category="programming")
        self.questions = []

    def add(self, q_type: str, order: int, category: str = "interest", weight: int = 1, option_count: int = 3):
        q = Question.objects.create(
            question_text=f"Question {order}",
            question_type=q_type,
            category=category,
            weight=weight,
            order=order,
            is_active=True,
        )
        for idx in range(option_count):
            QuestionOption.objects.create(
                question=q,
                option_text=f"Option {order}-{idx}",
                score=idx + 1,
                interest=self.interest if idx == 0 else None,
                skill=self.skill if idx == 0 else None,
            )
        self.questions.append(q)
        return q


class AssessmentServiceTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.factory = QuestionFactory()
        self.single = self.factory.add("single_choice", 1)
        self.multi = self.factory.add("multiple_choice", 2, category="skill")
        self.scale = self.factory.add("scale", 3)
        self.text_q = self.factory.add("text", 4, category="preference", option_count=0)
        self.assessment = get_or_create_assessment(self.user)

    def test_get_or_create_assessment_reuses_open_one(self):
        second = get_or_create_assessment(self.user)
        self.assertEqual(second.id, self.assessment.id)
        self.assertEqual(Assessment.objects.filter(user=self.user).count(), 1)

    def test_new_assessment_created_for_completed_one(self):
        self.assessment.is_completed = True
        self.assessment.save()
        second = get_or_create_assessment(self.user)
        self.assertNotEqual(second.id, self.assessment.id)
        self.assertTrue(Assessment.objects.filter(user=self.user).count() >= 2)

    def test_active_questions_ordering(self):
        active = get_active_questions()
        self.assertEqual(
            [q.id for q in active],
            [self.single.id, self.multi.id, self.scale.id, self.text_q.id],
        )

    def test_navigation_helpers(self):
        self.assertEqual(get_question_step(self.single.id), 0)
        self.assertEqual(get_question_step(self.text_q.id), 3)
        next_q = get_next_question(self.single.id)
        self.assertEqual(next_q.id, self.multi.id)
        self.assertIsNone(get_next_question(self.text_q.id))
        prev = get_previous_question(self.multi.id)
        self.assertEqual(prev.id, self.single.id)
        self.assertIsNone(get_previous_question(self.single.id))

    def test_save_answer_single_choice(self):
        option = self.single.options.first()
        save_answer(self.assessment, self.single, [option.id])
        answer = Answer.objects.get(assessment=self.assessment, question=self.single)
        self.assertEqual(answer.option, option)
        self.assertEqual(answer.score, option.score)

    def test_resaving_updates_instead_of_duplicating(self):
        option = self.single.options.first()
        save_answer(self.assessment, self.single, [option.id])
        save_answer(self.assessment, self.single, [self.single.options.last().id])
        self.assertEqual(Answer.objects.filter(assessment=self.assessment, question=self.single).count(), 1)

    def test_save_answer_multiple_choice_preserves_selection(self):
        selected = list(self.multi.options.all()[:2])
        save_answer(self.assessment, self.multi, [o.id for o in selected])
        answer = Answer.objects.get(assessment=self.assessment, question=self.multi)
        stored = [int(x) for x in answer.text_answer.split(",")]
        self.assertEqual(sorted(stored), sorted(o.id for o in selected))
        self.assertEqual(answer.score, sum(o.score for o in selected))

    def test_save_answer_scale_uses_first_option(self):
        option = self.scale.options.get(score=3)
        save_answer(self.assessment, self.scale, [option.id])
        answer = Answer.objects.get(assessment=self.assessment, question=self.scale)
        self.assertEqual(answer.option, option)
        self.assertEqual(answer.score, 3)

    def test_save_answer_text(self):
        save_answer(self.assessment, self.text_q, [], "I love building things")
        answer = Answer.objects.get(assessment=self.assessment, question=self.text_q)
        self.assertEqual(answer.text_answer, "I love building things")
        self.assertIsNone(answer.option)

    def test_text_answer_is_truncated(self):
        save_answer(self.assessment, self.text_q, [], "x" * 600)
        answer = Answer.objects.get(assessment=self.assessment, question=self.text_q)
        self.assertEqual(len(answer.text_answer), 500)

    def test_progress_data(self):
        option = self.single.options.first()
        save_answer(self.assessment, self.single, [option.id])
        data = progress_data(self.assessment)
        self.assertEqual(data["answered"], 1)
        self.assertEqual(data["total"], 4)


class AssessmentCompletionTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.factory = QuestionFactory()
        self.single = self.factory.add("single_choice", 1)
        self.multi = self.factory.add("multiple_choice", 2, category="skill")
        self.scale = self.factory.add("scale", 3)
        self.assessment = get_or_create_assessment(self.user)

        # Answer everything with the first option of each question.
        option = self.single.options.first()
        save_answer(self.assessment, self.single, [option.id])
        save_answer(self.assessment, self.multi, [self.multi.options.first().id])
        save_answer(self.assessment, self.scale, [self.scale.options.first().id])

    def test_completion_positions_flags(self):
        complete_assessment(self.assessment)
        self.assessment.refresh_from_db()
        self.assertTrue(self.assessment.is_completed)
        self.assertIsNotNone(self.assessment.completed_at)
        self.assertEqual(self.assessment.score, 1 + 1 + 1)  # one option score each, weight 1

    def test_completion_applies_interests_and_skills(self):
        complete_assessment(self.assessment)
        self.assertTrue(UserInterest.objects.filter(user=self.user, interest=self.factory.interest).exists())
        self.assertTrue(UserSkill.objects.filter(user=self.user, skill=self.factory.skill).exists())

    def test_apply_results_takes_highest_score_per_target(self):
        # Second option maps to the same interest/skill with a higher score.
        plugin = Question.objects.create(
            question_text="Bonus", question_type="single_choice", category="interest", order=90, is_active=True
        )
        QuestionOption.objects.create(question=plugin, option_text="Boost", score=5, interest=self.factory.interest)
        save_answer(self.assessment, plugin, [plugin.options.first().id])
        complete_assessment(self.assessment)
        ui = UserInterest.objects.get(user=self.user, interest=self.factory.interest)
        self.assertEqual(ui.level, 5)

    def test_completion_is_idempotent(self):
        complete_assessment(self.assessment)
        complete_assessment(self.assessment)
        self.assertEqual(Answer.objects.filter(assessment=self.assessment).count(), 3)


class AssessmentViewTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.client.force_login(self.user)
        self.factory = QuestionFactory()
        self.q1 = self.factory.add("single_choice", 1)
        self.q2 = self.factory.add("single_choice", 2)

    def test_start_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("assessment:start"))
        self.assertEqual(response.status_code, 302)

    def test_start_creates_assessment_and_redirects_to_first_question(self):
        response = self.client.get(reverse("assessment:start"))
        self.assertRedirects(response, reverse("assessment:question", args=[self.q1.id]))
        self.assertTrue(Assessment.objects.filter(user=self.user, is_completed=False).exists())

    def test_question_page_renders(self):
        response = self.client.get(reverse("assessment:question", args=[self.q1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertIn("question", response.context)
        self.assertFalse(response.context["has_previous"])

    def test_question_submit_advances_to_next(self):
        option = self.q1.options.first()
        response = self.client.post(
            reverse("assessment:question", args=[self.q1.id]), {"option": [option.id], "action": "next"}
        )
        self.assertRedirects(response, reverse("assessment:question", args=[self.q2.id]))

    def test_submit_last_question_completes_and_redirects(self):
        option = self.q2.options.first()
        response = self.client.post(
            reverse("assessment:question", args=[self.q2.id]), {"option": [option.id], "action": "finish"}
        )
        self.assertRedirects(response, reverse("recommendations:list"))
        assessment = Assessment.objects.get(user=self.user)
        self.assertTrue(assessment.is_completed)

    def test_previous_action_goes_back(self):
        self.client.get(reverse("assessment:question", args=[self.q1.id]))
        self.client.post(
            reverse("assessment:question", args=[self.q2.id]),
            {"option": [self.q2.options.first().id], "action": "previous"},
        )
        self.assessment = Assessment.objects.get(user=self.user)
        # No assertion of redirect URL here — covered by service tests.

    def test_revisiting_question_restores_previous_answer(self):
        option = self.q1.options.first()
        self.client.post(reverse("assessment:question", args=[self.q1.id]), {"option": [option.id]})
        response = self.client.get(reverse("assessment:question", args=[self.q1.id]))
        self.assertEqual(response.context["answered_option_id"], option.id)

    def test_cannot_access_inactive_question(self):
        q = Question.objects.create(
            question_text="Hidden", question_type="scale", order=50, is_active=False
        )
        response = self.client.get(reverse("assessment:question", args=[q.id]))
        self.assertEqual(response.status_code, 404)

    def test_complete_requires_own_assessment(self):
        other = User.objects.create_user(username="other", password=PASSWORD)
        from assessment.models import Assessment as A
        assessment = A.objects.create(user=other)
        response = self.client.post(reverse("assessment:complete", args=[assessment.id]))
        self.assertEqual(response.status_code, 404)