"""Google Search via SerpAPI, used to find real, live learning resources.

The client is deliberately stdlib-only (matching the AI providers) and every
result URL is sanitized before it can be stored. If the API key is missing,
rate-limited, or the network fails, callers fall back to the AI/providers and
the curated link map — so searches are always an enhancement, never a blocker.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from django.conf import settings

from .resource_finder import sanitize_url

logger = logging.getLogger(__name__)

SEARCH_URL = "https://serpapi.com/search.json"
USER_AGENT = "Mozilla/5.0 (compatible; CareerPathAI/1.0)"


class SerpAPIError(Exception):
    """Raised when the Google search API cannot complete a request."""


def serpapi_configured() -> bool:
    """Whether a SerpAPI key is configured (and thus searches are possible)."""
    return bool(getattr(settings, "SERPAPI_API_KEY", ""))


def _get_json(url: str, timeout: int) -> dict:
    """GET a URL and return parsed JSON, raising SerpAPIError on any failure."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise SerpAPIError(f"SerpAPI HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SerpAPIError(f"SerpAPI connection error: {exc.reason}") from exc
    except TimeoutError as exc:
        raise SerpAPIError(f"SerpAPI request timed out after {timeout}s") from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise SerpAPIError("SerpAPI returned a non-JSON response") from exc


def search_google(query: str, num: int | None = None, timeout: int | None = None) -> list[dict]:
    """Search Google and return sanitized organic results.

    Each result is ``{"title", "url", "snippet"}`` with a validated http(s)
    URL. Raises ``SerpAPIError`` when unconfigured or the API reports an error.
    """
    return _search("google", query, num, timeout)


def search_youtube(query: str, num: int | None = None, timeout: int | None = None) -> list[dict]:
    """Search YouTube and return sanitized video results.

    Each result is ``{"title", "url", "snippet", "channel"}`` with a validated
    ``youtube.com/watch`` (or ``youtu.be``) URL. Same error contract as
    ``search_google``.
    """
    return _search("youtube", query, num, timeout)


def _search(engine: str, query: str, num: int | None, timeout: int | None) -> list[dict]:
    """Shared SerpAPI search: builds the GET URL and parses the result list."""
    api_key = getattr(settings, "SERPAPI_API_KEY", "")
    if not api_key:
        raise SerpAPIError("SERPAPI_API_KEY is not configured.")

    params = {
        "api_key": api_key,
        "engine": engine,
    }
    if engine == "youtube":
        params["search_query"] = query  # YouTube engine uses search_query, not q
    else:
        params["q"] = query
    params["hl"] = "en"
    params["gl"] = "us"
    params["num"] = str(min(num or getattr(settings, "SERPAPI_RESULTS_NUM", 5), 10))
    location = getattr(settings, "SERPAPI_LOCATION", "")
    if location:
        params["location"] = location

    data = _get_json(
        f"{SEARCH_URL}?{urllib.parse.urlencode(params)}",
        timeout or getattr(settings, "AI_TIMEOUT_SECONDS", 45),
    )

    if data.get("error"):
        raise SerpAPIError(f"SerpAPI error: {data['error']}")

    items = data.get("organic_results") if engine == "google" else data.get("video_results")
    results = []
    for item in items or []:
        link = sanitize_url(item.get("link"))
        if not link:
            continue
        if engine == "youtube" and "youtube.com/watch" not in link and "youtu.be" not in link:
            continue  # video suggestions must be real YouTube links
        title = str(item.get("title") or "").strip()[:200]
        snippet = (
            str(
                item.get("snippet")
                or (item.get("snippet_highlighted_words") or [""])[0]
                or ""
            ).strip()[:200]
        )
        result: dict[str, Any] = {"title": title, "url": link, "snippet": snippet}
        if engine == "youtube":
            result["channel"] = str(item.get("channel") or "").strip()[:100]
        results.append(result)
    return results


# Simple signals for ranking which result is most useful for learning.
LEARNING_HINTS = (
    "docs", "tutorial", "learn", "official", "guide", "course",
    "w3schools", "mdn", "freecodecamp", "coursera", "khan academy",
    "geeksforgeeks", "realpython", "stackoverflow",
)
NOISE_HINTS = ("advertisement", "sign in", "login", "pricing", "subscribe")


def pick_best_video(results: list[dict], task_title: str) -> dict | None:
    """Pick the most relevant YouTube video for a task.

    Prefers a result whose title mentions the task topic; otherwise falls back
    to YouTube's own top-ranked result.
    """
    if not results:
        return None
    words = [w for w in task_title.lower().split() if w]
    for result in results:
        title = (result.get("title") or "").lower()
        if words and any(word in title for word in words):
            return result
    return results[0]


def pick_best_result(results: list[dict], task_title: str) -> dict | None:
    """Choose the most useful search result for a task.

    Prefers results that look like learning material and penalizes ads/login
    walls, nudged by Google's own ordering (earlier results rank higher).
    """
    if not results:
        return None
    lower = task_title.lower()

    def score(item: dict, index: int) -> int:
        combined = " ".join(
            str(item.get(key) or "") for key in ("title", "snippet", "url")
        ).lower()
        points = max(0, 6 - index)  # Google organic ordering is a strong signal
        if any(hint in combined for hint in LEARNING_HINTS):
            points += 4
        if any(hint in combined for hint in NOISE_HINTS):
            points -= 20
        if "youtube.com" in combined:
            points += 1  # video tutorials are fine learning material
        if lower and lower in combined:
            points += 2  # title matches the task topic
        return points

    ranked = sorted(range(len(results)), key=lambda i: score(results[i], i), reverse=True)
    return results[ranked[0]]