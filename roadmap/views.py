"""Views for roadmaps and progress tracking."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ai_engine.services.roadmap_generator import generate_roadmap
from careers.models import Career
from roadmap.models import Roadmap, RoadmapTask, TASK_STATUSES


@login_required
def roadmap_list(request):
    """List the user's roadmaps."""
    roadmaps = request.user.roadmaps.select_related("career").order_by("-created_at")
    return render(request, "roadmap/list.html", {"roadmaps": roadmaps})


@login_required
def roadmap_detail(request, pk: int):
    """Show one roadmap with phases, tasks and progress charts."""
    roadmap = get_object_or_404(
        Roadmap.objects.prefetch_related("phases__tasks", "career").filter(user=request.user),
        pk=pk,
    )
    phases = list(roadmap.phases.all())
    phase_progress = [
        {
            "phase": phase,
            "progress": phase.progress,
            "completed": phase.tasks.filter(status="completed").count(),
            "total": phase.tasks.count(),
        }
        for phase in phases
    ]

    return render(
        request,
        "roadmap/detail.html",
        {
            "roadmap": roadmap,
            "phases": phase_progress,
            "task_statuses": TASK_STATUSES,
            "chart": {
                "labels": [label[:20] for label in [p["phase"].title for p in phase_progress]],
                "data": [p["progress"] for p in phase_progress],
            },
        },
    )


@login_required
@require_POST
def update_task(request, pk: int, task_id: int):
    """Update the status of a roadmap task (owned by the current user)."""
    roadmap = get_object_or_404(Roadmap, pk=pk, user=request.user)
    task = get_object_or_404(RoadmapTask, pk=task_id, phase__roadmap=roadmap)

    new_status = request.POST.get("status", "").strip()
    valid_statuses = {s for s, _label in TASK_STATUSES}
    if new_status not in valid_statuses:
        messages.error(request, "Invalid task status.")
        return redirect("roadmap:detail", pk=roadmap.pk)

    task.status = new_status
    task.save(update_fields=["status"])
    messages.success(request, f"Task \"{task.title}\" marked as {new_status.replace('_', ' ')}.")
    return redirect("roadmap:detail", pk=roadmap.pk)


@login_required
@require_POST
def generate(request, career_id: int):
    """Generate (AI-first, DB-fallback) a roadmap for a career."""
    career = get_object_or_404(Career, pk=career_id)
    roadmap = generate_roadmap(request.user, career)
    messages.success(request, f"Your \"{roadmap.title}\" is ready. Let the learning begin!")
    return redirect("roadmap:detail", pk=roadmap.pk)


@login_required
@require_POST
def refresh_resources(request, pk: int):
    """Re-run resource lookup (live Google → AI → curated) on an existing roadmap."""
    roadmap = get_object_or_404(Roadmap, pk=pk, user=request.user)
    from ai_engine.services.resource_finder import enrich_roadmap_with_resources

    stats = enrich_roadmap_with_resources(request.user, roadmap.career, roadmap)
    if not stats["total"]:
        messages.success(request, "This roadmap has no tasks to enrich.")
    else:
        parts = [f"{stats['with_resources']} of {stats['total']} tasks"]
        if stats.get("from_search"):
            parts.append(f"{stats['from_search']} from live Google")
        if stats.get("from_ai"):
            parts.append(f"{stats['from_ai']} from AI")
        if stats.get("from_curated"):
            parts.append(f"{stats['from_curated']} curated")
        if stats.get("with_videos"):
            parts.append(f"{stats['with_videos']} with YouTube videos")
        message = "Found resources for " + ", ".join(parts)
        if stats.get("queries_used"):
            message += f" ({stats['queries_used']} searches)."
        else:
            message += "."
        messages.success(request, message)
    return redirect("roadmap:detail", pk=roadmap.pk)