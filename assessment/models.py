"""Models for the dynamic assessment engine: interests, skills, questions
and assessment answers.
"""
from django.conf import settings
from django.db import models

SCALE_LEVELS = list(range(1, 6))  # 1-5 rating scale used across the app

QUESTION_TYPES = [
    ("single_choice", "Single Choice"),
    ("multiple_choice", "Multiple Choice"),
    ("scale", "Scale (1-5)"),
    ("text", "Text"),
]

QUESTION_CATEGORIES = [
    ("interest", "Interest"),
    ("skill", "Skill"),
    ("personality", "Personality"),
    ("preference", "Preference"),
    ("career_style", "Career Style"),
]


class Interest(models.Model):
    """A career-related interest area, e.g. Web Development."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Skill(models.Model):
    """A competency a user may hold, e.g. Python, Git."""

    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=100, blank=True, default="")
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class UserInterest(models.Model):
    """A user's declared interest together with its strength (1-5)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_interests")
    interest = models.ForeignKey(Interest, on_delete=models.CASCADE, related_name="user_interests")
    level = models.PositiveSmallIntegerField(default=3, choices=((i, str(i)) for i in SCALE_LEVELS))

    class Meta:
        unique_together = ("user", "interest")
        ordering = ["interest__name"]

    def __str__(self) -> str:
        return f"{self.user.username}: {self.interest.name} ({self.level})"


class UserSkill(models.Model):
    """A user's skill with a self-reported proficiency (1-5)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_skills")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="user_skills")
    proficiency = models.PositiveSmallIntegerField(default=1, choices=((i, str(i)) for i in SCALE_LEVELS))

    class Meta:
        unique_together = ("user", "skill")
        ordering = ["skill__name"]

    def __str__(self) -> str:
        return f"{self.user.username}: {self.skill.name} ({self.proficiency})"


class Question(models.Model):
    """A single assessment question, fully configurable via admin."""

    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default="single_choice")
    category = models.CharField(max_length=30, choices=QUESTION_CATEGORIES, default="interest")
    weight = models.PositiveSmallIntegerField(default=1, help_text="Relative importance of this question.")
    order = models.PositiveIntegerField(default=0, help_text="Used to order questions in the assessment.")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return f"Q{self.order}: {self.question_text[:60]}"


class QuestionOption(models.Model):
    """A selectable option for a question. Can carry scores and map to an
    interest and/or skill for the recommendation engine."""

    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    option_text = models.CharField(max_length=255)
    score = models.PositiveSmallIntegerField(default=1, help_text="Points awarded when selected.")
    interest = models.ForeignKey(Interest, on_delete=models.SET_NULL, null=True, blank=True, related_name="question_options")
    skill = models.ForeignKey(Skill, on_delete=models.SET_NULL, null=True, blank=True, related_name="question_options")

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.option_text} ({self.score})"


class Assessment(models.Model):
    """A completed (or in-progress) assessment session for a user."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assessments")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        state = "completed" if self.is_completed else "in progress"
        return f"{self.user.username} assessment ({state})"

    @property
    def progress(self) -> float:
        """Percentage of active questions answered (0-100)."""
        questions = Question.objects.filter(is_active=True).count()
        if not questions:
            return 0
        answered = self.answers.count()
        return min(100.0, round(answered / questions * 100, 1))


class Answer(models.Model):
    """A single answer given within an assessment."""

    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    option = models.ForeignKey(QuestionOption, on_delete=models.SET_NULL, null=True, blank=True, related_name="answers")
    text_answer = models.TextField(blank=True, default="")
    score = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = ("assessment", "question")

    def __str__(self) -> str:
        return f"{self.assessment.user.username}: {self.question} → {self.option or self.text_answer[:30]}"