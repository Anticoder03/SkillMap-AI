"""Roadmap models: a user's learning journey for a career."""
from django.conf import settings
from django.db import models

from careers.models import Career

TASK_STATUSES = [
    ("not_started", "Not Started"),
    ("in_progress", "In Progress"),
    ("completed", "Completed"),
]


class Roadmap(models.Model):
    """Top-level learning roadmap for a user + career."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="roadmaps")
    career = models.ForeignKey(Career, on_delete=models.CASCADE, related_name="roadmaps")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    duration_weeks = models.PositiveIntegerField(default=8)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "career"], name="unique_user_career_roadmap"),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def total_tasks(self) -> int:
        return self.phases.aggregate(total=models.Count("tasks"))["total"] or 0

    @property
    def completed_tasks(self) -> int:
        return self.phases.filter(tasks__status="completed").values("tasks").distinct().count() or 0

    @property
    def progress(self) -> float:
        """Overall progress percentage calculated from completed tasks."""
        total = self.total_tasks
        if not total:
            return 0.0
        return round(self.completed_tasks / total * 100, 1)


class RoadmapPhase(models.Model):
    """A phase of a roadmap containing a set of tasks."""

    roadmap = models.ForeignKey(Roadmap, on_delete=models.CASCADE, related_name="phases")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    order = models.PositiveIntegerField(default=0)
    duration_weeks = models.PositiveIntegerField(default=2)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["roadmap", "order"], name="unique_roadmap_phase_order"),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def progress(self) -> float:
        tasks = self.tasks.count()
        if not tasks:
            return 0.0
        completed = self.tasks.filter(status="completed").count()
        return round(completed / tasks * 100, 1)


class RoadmapTask(models.Model):
    """A single actionable learning task within a phase."""

    phase = models.ForeignKey(RoadmapPhase, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    resource_url = models.URLField(blank=True, default="")
    video_url = models.URLField(blank=True, default="")
    video_title = models.CharField(max_length=255, blank=True, default="")
    estimated_hours = models.PositiveSmallIntegerField(default=2)
    status = models.CharField(max_length=20, choices=TASK_STATUSES, default="not_started")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["phase", "order"], name="unique_phase_task_order"),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def is_completed(self) -> bool:
        return self.status == "completed"