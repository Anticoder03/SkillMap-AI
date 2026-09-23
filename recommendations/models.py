"""Stored recommendation results from the matching engine."""
from django.conf import settings
from django.db import models

from careers.models import Career


class Recommendation(models.Model):
    """The persisted result of the career matching engine for a user."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recommendations")
    career = models.ForeignKey(Career, on_delete=models.CASCADE, related_name="recommendations")
    match_score = models.PositiveSmallIntegerField(
        default=0,
        help_text="Compatibility 0-100 with the application's stored criteria.",
    )
    reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-match_score"]
        constraints = [
            models.UniqueConstraint(fields=["user", "career"], name="unique_user_career_recommendation"),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} → {self.career.title} ({self.match_score}%)"