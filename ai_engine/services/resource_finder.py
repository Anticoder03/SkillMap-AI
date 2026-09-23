"""Finds real learning resources for every task in a roadmap.

**Resource links** (every task always gets one):
1. **Live Google results (SerpAPI)** — a real, currently-ranking result with
   a snippet for each task (best signal, optional).
2. **AI suggestion (configured provider)** — the AI proposes a well-known
   free resource per task; URLs are validated before use.
3. **Curated map** — a high-quality curated resource covering every seeded
   skill, guaranteed to exist offline.

**Video links** (bonus, best-effort): each task may also get a YouTube video:
1. **Live YouTube results (SerpAPI engine=youtube)** — a real video with its
   channel name.
2. **AI-suggested video** — returned alongside the resource in the same call.
Videos are optional; a task is never left without a resource link because a
video wasn't found.
"""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth.models import User

from careers.models import Career

from .prompt_builder import build_resources_prompt
from .providers.base import AIProviderError, InvalidAIResponseError
from .provider_registry import get_provider

logger = logging.getLogger(__name__)

MAX_URL_LENGTH = 500

# Curated (title, url) pairs keyed by skill name (lowercase). These are
# stable, well-known, free learning resources used when the AI is offline.
CURATED_LINKS: dict[str, list[tuple[str, str]]] = {
    "aws": [("AWS Getting Started", "https://aws.amazon.com/getting-started/"), ("AWS Skill Builder", "https://aws.amazon.com/training/learn-about/skillbuilder/")],
    "agile": [("Scrum.org: What is Agile?", "https://www.scrum.org/resources/what-is-agile"), ("Atlassian Agile Guide", "https://www.atlassian.com/agile")],
    "android": [("Android Developers Docs", "https://developer.android.com/docs"), ("Android Basics with Compose", "https://developer.android.com/courses/android-basics-compose/course")],
    "c#": [("Microsoft Learn C#", "https://learn.microsoft.com/dotnet/csharp/"), ("C# on W3Schools", "https://www.w3schools.com/cs/index.php")],
    "c++": [("cppreference.com", "https://en.cppreference.com/w/"), ("LearnCpp.com", "https://www.learncpp.com/")],
    "ci/cd": [("GitHub Actions Docs", "https://docs.github.com/actions"), ("Jenkins User Handbook", "https://www.jenkins.io/doc/")],
    "css": [("MDN CSS", "https://developer.mozilla.org/en-US/docs/Web/CSS"), ("CSS on freeCodeCamp", "https://www.freecodecamp.org/learn/2022/responsive-web-design/#learn-css")],
    "communication": [("Coursera Communication Courses", "https://www.coursera.org/courses?query=communication"), ("Toastmasters Resources", "https://www.toastmasters.org/resources")],
    "data visualization": [("Matplotlib Docs", "https://matplotlib.org/stable/tutorials/index.html"), ("Observable D3 Gallery", "https://observablehq.com/@d3/gallery")],
    "deep learning": [("fast.ai Course", "https://www.fast.ai/"), ("DeepLearning.AI", "https://www.deeplearning.ai/courses/")],
    "django": [("Django Docs", "https://docs.djangoproject.com/"), ("Django Girls Tutorial", "https://tutorial.djangogirls.org/")],
    "docker": [("Docker Get Started", "https://docs.docker.com/get-started/"), ("Play with Docker", "https://labs.play-with-docker.com/")],
    "ethical hacking": [("TryHackMe", "https://tryhackme.com/"), ("Hack The Box Academy", "https://academy.hackthebox.com/")],
    "figma": [("Figma Learn", "https://help.figma.com/hc/en-us"), ("Figma YouTube", "https://www.youtube.com/figma")],
    "git": [("Pro Git Book", "https://git-scm.com/book/en/v2"), ("GitHub Skills", "https://skills.github.com/")],
    "html": [("MDN HTML", "https://developer.mozilla.org/en-US/docs/Web/HTML"), ("W3Schools HTML", "https://www.w3schools.com/html/default.asp")],
    "java": [("JetBrains Academy", "https://www.jetbrains.com/academy/"), ("W3Schools Java", "https://www.w3schools.com/java/default.asp")],
    "javascript": [("MDN JavaScript", "https://developer.mozilla.org/en-US/docs/Web/JavaScript"), ("javascript.info", "https://javascript.info/")],
    "kotlin": [("Kotlin Docs", "https://kotlinlang.org/docs/home.html"), ("Android Kotlin Fundamentals", "https://developer.android.com/courses/kotlin-android-fundamentals/overview")],
    "kubernetes": [("Kubernetes Docs", "https://kubernetes.io/docs/"), ("Kubernetes Tutorials", "https://kubernetes.io/docs/tutorials/")],
    "linux": [("Linux Journey", "https://linuxjourney.com/"), ("Ubuntu Tutorials", "https://ubuntu.com/tutorials")],
    "machine learning": [("scikit-learn Tutorials", "https://scikit-learn.org/stable/tutorial/index.html"), ("Machine Learning Crash Course", "https://developers.google.com/machine-learning/crash-course")],
    "network security": [("TryHackMe", "https://tryhackme.com/"), ("Cybrary", "https://www.cybrary.it/")],
    "networking": [("Cisco Networking Academy", "https://www.netacad.com/"), ("Khan Academy Networking", "https://www.khanacademy.org/computing/computers-and-internet/xcae6f4a7ff015e7d:the-internet")],
    "node.js": [("Node.js Learn", "https://nodejs.org/en/learn"), ("Node.js Course (freeCodeCamp)", "https://www.freecodecamp.org/learn/back-end-development-and-apis/")],
    "numpy": [("NumPy Learn", "https://numpy.org/learn/"), ("NumPy Quickstart", "https://numpy.org/doc/stable/user/quickstart.html")],
    "pandas": [("pandas Getting Started", "https://pandas.pydata.org/docs/getting_started/index.html"), ("Pandas Tutorial (Real Python)", "https://realpython.com/pandas-python-explore-dataset/")],
    "problem solving": [("LeetCode", "https://leetcode.com/"), ("HackerRank", "https://www.hackerrank.com/")],
    "python": [("Python Official Tutorial", "https://docs.python.org/3/tutorial/index.html"), ("Real Python", "https://realpython.com/")],
    "react": [("React Docs", "https://react.dev/learn"), ("React Course (freeCodeCamp)", "https://www.freecodecamp.org/learn/front-end-development-libraries/")],
    "react native": [("React Native Docs", "https://reactnative.dev/docs/getting-started"), ("Expo Docs", "https://docs.expo.dev/")],
    "sql": [("Mode SQL Tutorial", "https://mode.com/sql-tutorial/"), ("SQLBolt", "https://sqlbolt.com/")],
    "statistics": [("Khan Academy Statistics", "https://www.khanacademy.org/math/statistics-probability"), ("Statistical Thinking (freeCodeCamp)", "https://www.freecodecamp.org/learn/data-analysis-with-python/#learn-pandas")],
    "swift": [("The Swift Programming Language", "https://docs.swift.org/swift-book/"), ("Apple Swift Resources", "https://developer.apple.com/swift/resources/")],
    "typescript": [("TypeScript Handbook", "https://www.typescriptlang.org/docs/"), ("TypeScript Tutorial", "https://www.typescriptlang.org/docs/handbook/intro.html")],
    "ui design": [("Figma Learn", "https://help.figma.com/hc/en-us"), ("MDN UX/UI Basics", "https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Design_and_accessibility")],
    "ux research": [("Nielsen Norman Group", "https://www.nngroup.com/articles/"), ("Google UX Design Certificate", "https://www.coursera.org/professional-certificates/google-ux-design")],
}

# Generic, category-agnostic resources used when nothing specific matches.
GENERAL_LINKS: list[tuple[str, str]] = [
    ("freeCodeCamp", "https://www.freecodecamp.org/learn/"),
    ("Coursera", "https://www.coursera.org/"),
]


def sanitize_url(url: Any) -> str | None:
    """Return a safe http/https URL string, or None if the value is unusable."""
    if not isinstance(url, str):
        return None
    url = url.strip()
    if not url or len(url) > MAX_URL_LENGTH or any(ch in url for ch in " \n\t"):
        return None
    try:
        parts = urlparse(url)
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return None
    return url


def sanitize_youtube_url(url: Any) -> str | None:
    """Like ``sanitize_url`` but only allows real YouTube watch links."""
    safe = sanitize_url(url)
    if not safe:
        return None
    if "youtube.com/watch" not in safe and "youtu.be" not in safe:
        return None
    return safe


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def curated_resources_for(task_title: str) -> list[tuple[str, str]]:
    """Curated (title, url) matches for a task title, else general links."""
    title = _normalize(task_title)
    for key, links in CURATED_LINKS.items():
        if key in title:
            return links
    return list(GENERAL_LINKS)


def parse_ai_resources(raw: Any) -> tuple[list[dict], dict[str, list[str]]]:
    """Normalize the AI's ``resources`` into validated entries.

    Returns ``(entries, errors)`` where each entry is
    ``{"phase", "task", "title", "url", "description", "video_url", "video_title"}``.
    Video fields are optional extras (sanitized to real YouTube links).
    Error keys are human-readable reasons for skipped items.
    """
    entries: list[dict] = []
    errors: dict[str, list[str]] = {"skipped": []}

    if not isinstance(raw, dict):
        raise InvalidAIResponseError("Resources response must be a JSON object.")

    resources = raw.get("resources")
    if not isinstance(resources, list):
        raise InvalidAIResponseError("Resources response must contain a 'resources' list.")

    for item in resources:
        if not isinstance(item, dict):
            continue
        phase = str(item.get("phase") or "").strip()
        task = str(item.get("task") or "").strip()
        url = sanitize_url(item.get("resource_url"))
        if not phase or not task:
            errors["skipped"].append("entry missing phase/task")
            continue
        if not url:
            errors["skipped"].append(f"unusable URL for '{task}'")
            continue
        video_url = sanitize_youtube_url(item.get("video_url"))
        entries.append(
            {
                "phase": phase,
                "task": task,
                "title": str(item.get("resource_title") or "Resource").strip()[:120],
                "url": url,
                "description": str(item.get("description") or "").strip()[:200],
                "video_url": video_url or "",
                "video_title": str(item.get("video_title") or "").strip()[:200] if video_url else "",
            }
        )
    return entries, errors


def find_resources_with_ai(user: User, career: Career, roadmap) -> dict[str, dict[str, str]]:
    """Ask the AI for task resources and return ``{phase_title: {task_title: link_dict}}``.

    Raises ``AIProviderError`` when the provider cannot be used; returns an
    empty mapping when the response contains nothing usable.
    """
    prompt = build_resources_prompt(user, career, roadmap)
    raw = get_provider().get_json(prompt)
    entries, _errors = parse_ai_resources(raw)

    result: dict[str, dict[str, str]] = {}
    for entry in entries:
        result.setdefault(_normalize(entry["phase"]), {})[_normalize(entry["task"])] = entry
    return result


def build_search_query(career: Career, task_title: str) -> str:
    """Google query for the 'best resource to learn this task'."""
    return f"learn {task_title} for {career.title} - best free online course".strip()


def search_resources_for_tasks(career: Career, phase_tasks: dict[str, dict[str, Any]], max_queries: int | None = None) -> tuple[dict[str, dict[str, dict]], int]:
    """Live-Google every unique task and return ``(hits, queries_used)``.

    ``hits`` is ``{phase_title: {task_title: {url, title, description}}}``
    keyed exactly like the normalized task map. Queries are deduplicated and
    capped by ``max_queries`` so one refresh cannot burn the rate limit.
    """
    from . import google_search  # lazy import to avoid a circular dependency

    if not google_search.serpapi_configured():
        return {}, 0

    max_queries = max_queries or getattr(settings, "SERPAPI_MAX_QUERIES", 20)

    # Flatten unique queries in stable order.
    plan: list[tuple[str, str, str]] = []  # (phase_title, task_title, query)
    seen_queries: set[str] = set()
    for phase_title, task_map in phase_tasks.items():
        for task_title, task in task_map.items():
            query = build_search_query(career, task.title)
            if query in seen_queries:
                continue
            seen_queries.add(query)
            plan.append((phase_title, task_title, query))
            if len(plan) >= max_queries:
                break

    hits: dict[str, dict[str, dict]] = {}
    queries_used = 0
    for phase_title, task_title, query in plan:
        try:
            results = google_search.search_google(query)
        except google_search.SerpAPIError as exc:
            logger.warning("Google search failed for '%s': %s", query, exc)
            continue
        queries_used += 1
        best = google_search.pick_best_result(results, task_title)
        if not best:
            continue
        hits.setdefault(phase_title, {})[task_title] = {
            "url": best["url"],
            "title": best["title"],
            "description": best["snippet"],
        }
    return hits, queries_used


def _find_by_title(mapping: dict[str, dict[str, Any]], title: str) -> Any | None:
    """Look up an entry across all phases by normalized task title."""
    for tasks_map in mapping.values():
        if title in tasks_map:
            return tasks_map[title]
    return None


def build_video_query(career: Career, task_title: str) -> str:
    """YouTube query for the 'best video tutorial to learn this task'."""
    return f"{task_title} - tutorial for {career.title}".strip()


def search_videos_for_tasks(career: Career, phase_tasks: dict[str, dict[str, Any]], max_queries: int | None = None) -> tuple[dict[str, dict[str, dict]], int]:
    """Live-search YouTube for every unique task and return ``(hits, queries_used)``.

    ``hits`` is ``{phase_title: {task_title: {url, title, channel}}}`` keyed
    exactly like the normalized task map. Queries are deduplicated and capped
    like the Google tier.
    """
    from . import google_search  # lazy import to avoid a circular dependency

    if not google_search.serpapi_configured():
        return {}, 0

    max_queries = max_queries or getattr(settings, "SERPAPI_MAX_QUERIES", 20)

    plan: list[tuple[str, str, str]] = []  # (phase_title, task_title, query)
    seen_queries: set[str] = set()
    for phase_title, task_map in phase_tasks.items():
        for task_title, task in task_map.items():
            query = build_video_query(career, task.title)
            if query in seen_queries:
                continue
            seen_queries.add(query)
            plan.append((phase_title, task_title, query))
            if len(plan) >= max_queries:
                break

    hits: dict[str, dict[str, dict]] = {}
    queries_used = 0
    for phase_title, task_title, query in plan:
        try:
            results = google_search.search_youtube(query)
        except google_search.SerpAPIError as exc:
            logger.warning("YouTube search failed for '%s': %s", query, exc)
            continue
        queries_used += 1
        best = google_search.pick_best_video(results, task_title)
        if not best:
            continue
        hits.setdefault(phase_title, {})[task_title] = {
            "url": best["url"],
            "title": best["title"],
            "channel": best.get("channel", ""),
        }
    return hits, queries_used


def enrich_roadmap_with_resources(user: User, career: Career, roadmap, use_ai: bool = True, use_search: bool = True) -> dict:
    """Attach a validated resource URL (and optional YouTube video) to every task.

    Resource priority: live Google result (SerpAPI) → AI suggestion → curated link.
    Video priority: live YouTube result (SerpAPI) → AI-suggested video → none.
    Returns stats about what was attached and where each link came from.
    """
    from roadmap.models import RoadmapTask  # local import to avoid cycles

    tasks = list(
        RoadmapTask.objects.filter(phase__roadmap=roadmap).select_related("phase").order_by("phase__order", "order")
    )
    if not tasks:
        return {
            "total": 0, "with_resources": 0, "with_videos": 0,
            "from_search": 0, "from_ai": 0, "from_curated": 0,
            "from_video_search": 0, "from_video_ai": 0, "queries_used": 0,
        }

    # Build {phase_title: {task_title: task}} map, tolerating case differences.
    phase_tasks: dict[str, dict[str, RoadmapTask]] = {}
    for task in tasks:
        phase_tasks.setdefault(_normalize(task.phase.title), {})[_normalize(task.title)] = task

    ai_map: dict[str, dict[str, str]] = {}
    if use_ai:
        try:
            ai_map = find_resources_with_ai(user, career, roadmap)
        except (AIProviderError, InvalidAIResponseError) as exc:
            logger.warning("AI resource lookup failed for %s/%s, using curated links: %s", user.username, career.title, exc)
        except Exception as exc:  # never let enrichment break the roadmap
            logger.warning("Unexpected AI resource error for %s/%s: %s", user.username, career.title, exc)

    search_map: dict[str, dict[str, dict]] = {}
    video_search_map: dict[str, dict[str, dict]] = {}
    queries_used = 0
    if use_search:
        try:
            search_map, google_queries = search_resources_for_tasks(career, phase_tasks)
            video_search_map, video_queries = search_videos_for_tasks(career, phase_tasks)
            queries_used = google_queries + video_queries
        except Exception as exc:  # searches are optional; never break enrichment
            logger.warning("Google/YouTube resource search failed for %s/%s: %s", user.username, career.title, exc)

    stat_search = stat_ai = stat_curated = 0
    stat_video_search = stat_video_ai = 0
    updates = []
    for phase_title, task_map in phase_tasks.items():
        for task_title, task in task_map.items():
            # ---- Resource link: Google → AI → curated ----
            candidate = search_map.get(phase_title, {}).get(task_title) or _find_by_title(search_map, task_title)
            source = "search"
            if not candidate:
                candidate = ai_map.get(phase_title, {}).get(task_title) or _find_by_title(ai_map, task_title)
                source = "ai"
            url = sanitize_url(candidate.get("url")) if candidate else None
            description = str(candidate.get("description") or candidate.get("snippet") or "")[:200] if candidate else ""

            if not url:
                title, url = curated_resources_for(task.title)[0]
                if not url:
                    continue
                source = "curated"
                description = description or title

            if source == "search":
                stat_search += 1
            elif source == "ai":
                stat_ai += 1
            else:
                stat_curated += 1

            task.resource_url = url
            if description:
                task.description = description[:200]

            # ---- Video: YouTube live → AI-suggested → none ----
            video = video_search_map.get(phase_title, {}).get(task_title) or _find_by_title(video_search_map, task_title)
            video_source = "search"
            if not video and candidate:
                video_url = sanitize_youtube_url(candidate.get("video_url"))
                if video_url:
                    video = {"url": video_url, "title": candidate.get("video_title", "")}
                    video_source = "ai"
            video_url = sanitize_youtube_url(video["url"]) if video else None

            if video_url:
                if video_source == "search":
                    stat_video_search += 1
                else:
                    stat_video_ai += 1
                task.video_url = video_url
                task.video_title = str(video.get("title") or "")[:200]

            updates.append(task)

    if updates:
        RoadmapTask.objects.bulk_update(updates, ["resource_url", "description", "video_url", "video_title"])

    return {
        "total": len(tasks),
        "with_resources": stat_search + stat_ai + stat_curated,
        "with_videos": stat_video_search + stat_video_ai,
        "from_search": stat_search,
        "from_ai": stat_ai,
        "from_curated": stat_curated,
        "from_video_search": stat_video_search,
        "from_video_ai": stat_video_ai,
        "queries_used": queries_used,
    }