"""Career knowledge base models."""
from django.db import models
from django.utils.text import slugify

from accounts.models import EDUCATION_LEVELS, EXPERIENCE_LEVELS
from assessment.models import Interest, Skill

DEMAND_LEVELS = [
    ("low", "Low"),
    ("medium", "Medium"),
    ("high", "High"),
    ("very_high", "Very High"),
]


class Career(models.Model):
    """A career entry in the knowledge base with its requirements."""

    title = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True, default="")
    difficulty = models.CharField(max_length=20, choices=EXPERIENCE_LEVELS, default="beginner")
    salary_range = models.CharField(max_length=120, blank=True, default="")
    future_scope = models.TextField(blank=True, default="")
    demand_level = models.CharField(max_length=20, choices=DEMAND_LEVELS, default="medium")
    required_education = models.CharField(max_length=20, choices=EDUCATION_LEVELS, default="bachelors")
    skills = models.ManyToManyField(Skill, through="CareerSkill", related_name="careers")
    interests = models.ManyToManyField(Interest, through="CareerInterest", related_name="careers")

    class Meta:
        ordering = ["title"]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            base = slugify(self.title)
            slug, counter = base, 1
            while Career.objects.filter(slug=slug).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def difficulty_label(self) -> str:
        return self.get_difficulty_display() or self.difficulty

    @property
    def education_label(self) -> str:
        return self.get_required_education_display() or self.required_education

    @property
    def demand_label(self) -> str:
        return self.get_demand_level_display() or self.demand_level


class CareerSkill(models.Model):
    """Maps a skill to a career with importance and required proficiency."""

    career = models.ForeignKey(Career, on_delete=models.CASCADE, related_name="career_skills")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="career_skills")
    importance = models.PositiveSmallIntegerField(default=5, help_text="Weight 1-10, higher is more important.")
    required_level = models.PositiveSmallIntegerField(default=3, help_text="Minimum proficiency 1-5 expected.")

    class Meta:
        unique_together = ("career", "skill")
        ordering = ["-importance"]

    def __str__(self) -> str:
        return f"{self.career.title} → {self.skill.name}"


class CareerInterest(models.Model):
    """Maps an interest to a career with a relative weight."""

    career = models.ForeignKey(Career, on_delete=models.CASCADE, related_name="career_interests")
    interest = models.ForeignKey(Interest, on_delete=models.CASCADE, related_name="career_interests")
    weight = models.PositiveSmallIntegerField(default=5, help_text="Weight 1-10, higher is more relevant.")

    class Meta:
        unique_together = ("career", "interest")
        ordering = ["-weight"]

    def __str__(self) -> str:
        return f"{self.career.title} ↔ {self.interest.name}"


class CareerPrerequisite(models.Model):
    """A prerequisite/precondition for pursuing a career."""

    career = models.ForeignKey(Career, on_delete=models.CASCADE, related_name="prerequisites")
    description = models.CharField(max_length=255)
    priority = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ["priority", "id"]

    def __str__(self) -> str:
        return f"{self.career.title}: {self.description}"