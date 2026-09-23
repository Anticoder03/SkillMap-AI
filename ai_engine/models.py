"""Persisted results of the AI analysis layer."""
from django.conf import settings
from django.db import models

from careers.models import Career


class CareerAnalysis(models.Model):
    """Structured AI analysis of how a career fits a user's profile.

    The ``content`` field stores the *validated* JSON produced by the AI
    layer (summary, strengths, skill gaps, learning order, projects).
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="career_analyses")
    career = models.ForeignKey(Career, on_delete=models.CASCADE, related_name="analyses")
    content = models.JSONField(default=dict, blank=True)
    provider = models.CharField(max_length=50, blank=True, default="")
    source = models.CharField(
        max_length=20,
        choices=[("ai", "AI"), ("fallback", "Rule-based fallback")],
        default="ai",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "career"], name="unique_user_career_analysis"),
        ]

    def __str__(self) -> str:
        return f"{self.user.username}: {self.career.title} analysis"