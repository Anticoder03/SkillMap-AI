"""Account, profile and preference models."""
from django.conf import settings
from django.db import models

EDUCATION_LEVELS = [
    ("high_school", "High School"),
    ("diploma", "Diploma"),
    ("bachelors", "Bachelor's Degree"),
    ("masters", "Master's Degree"),
    ("phd", "PhD / Doctorate"),
]

EXPERIENCE_LEVELS = [
    ("no_experience", "No Experience"),
    ("beginner", "Beginner (0-1 years)"),
    ("intermediate", "Intermediate (1-3 years)"),
    ("advanced", "Advanced (3-7 years)"),
    ("expert", "Expert (7+ years)"),
]

EDUCATION_ORDER = {level: idx for idx, (level, _label) in enumerate(EDUCATION_LEVELS)}
EXPERIENCE_ORDER = {level: idx for idx, (level, _label) in enumerate(EXPERIENCE_LEVELS)}


class UserProfile(models.Model):
    """Extended profile linked one-to-one with the built-in Django User."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    education_level = models.CharField(
        max_length=20,
        choices=EDUCATION_LEVELS,
        blank=True,
        default="",
        verbose_name="Highest education level",
    )
    degree = models.CharField(max_length=120, blank=True)
    college = models.CharField(max_length=120, blank=True)
    graduation_year = models.PositiveIntegerField(null=True, blank=True)
    experience_level = models.CharField(
        max_length=20,
        choices=EXPERIENCE_LEVELS,
        blank=True,
        default="",
    )
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Profile"

    def __str__(self) -> str:
        return f"{self.user.get_full_name() or self.user.username}"

    def is_complete(self) -> bool:
        """A profile is 'complete' enough for recommendations when at least
        the core fields are filled in."""
        return bool(self.education_level and self.education_level in EDUCATION_ORDER)