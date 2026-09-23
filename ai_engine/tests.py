"""Tests for the AI engine: provider abstraction, JSON validation,
career analysis normalization and the fallback behaviour.
"""
import json
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from ai_engine.models import CareerAnalysis
from ai_engine.services.career_analyzer import (
    clean_projects,
    clean_string_list,
    analyze_career,
    normalize_analysis,
    normalize_level,
)
from ai_engine.services.google_search import (
    SerpAPIError,
    pick_best_result,
    pick_best_video,
    search_google,
    search_youtube,
    serpapi_configured,
)
from ai_engine.services.provider_registry import UnknownProviderError, get_provider, provider_is_configured
from ai_engine.services.providers.base import AIProvider, AIProviderError, InvalidAIResponseError
from ai_engine.services.providers.gemini import GeminiProvider
from ai_engine.services.resource_finder import (
    build_search_query,
    build_video_query,
    curated_resources_for,
    enrich_roadmap_with_resources,
    parse_ai_resources,
    sanitize_url,
    sanitize_youtube_url,
    search_resources_for_tasks,
    search_videos_for_tasks,
)

from assessment.models import Interest, Skill
from careers.models import Career, CareerSkill

PASSWORD = "Str0ng!pass123"


class FakeProvider(AIProvider):
    """Configurable stand-in registered under ``ai_engine.tests.FakeProvider``.

    ``payload`` and ``error`` are class-level so ``provider_registry`` can
    hand out fresh instances that still share the test's behaviour.
    """

    name = "fake"

    payload: dict = {}
    error: Exception | None = None
    raw_text: str | None = None

    def __init__(self, api_key: str = "", model: str = "", timeout: int = 45):
        self.api_key = api_key or "test-key"
        self.model = model or "fake-model"
        self.timeout = timeout

    def generate(self, prompt: str, **kwargs) -> str:
        if FakeProvider.error:
            raise FakeProvider.error
        if FakeProvider.raw_text is not None:
            return FakeProvider.raw_text
        return json.dumps(FakeProvider.payload)


FAKE_PROVIDERS = {"fake": "ai_engine.tests.FakeProvider"}


def create_user() -> User:
    return User.objects.create_user(username="ada", password=PASSWORD)


def create_career() -> Career:
    career = Career.objects.create(title="Backend Developer", required_education="bachelors")
    py = Skill.objects.create(name="Python", category="programming")
    go = Skill.objects.create(name="Go", category="programming")
    CareerSkill.objects.create(career=career, skill=py, importance=8, required_level=3)
    CareerSkill.objects.create(career=career, skill=go, importance=4, required_level=2)
    return career


class ProviderJsonValidationTests(TestCase):
    def setUp(self):
        FakeProvider.payload = {}
        FakeProvider.error = None
        FakeProvider.raw_text = None
        self.provider = FakeProvider(api_key="k", model="m")

    def test_get_json_parses_fenced_json(self):
        FakeProvider.raw_text = '```json\n{"answer": 42}\n```'
        self.assertEqual(self.provider.get_json("p"), {"answer": 42})

    def test_get_json_ignores_surrounding_prose(self):
        FakeProvider.raw_text = 'Here is the result:\n{"ok": true}\nHope it helps!'
        self.assertEqual(self.provider.get_json("p"), {"ok": True})

    def test_malformed_json_raises(self):
        FakeProvider.raw_text = "not json at all"
        with self.assertRaises(InvalidAIResponseError):
            self.provider.get_json("p")

    def test_non_object_json_raises(self):
        FakeProvider.raw_text = json.dumps([1, 2, 3])
        with self.assertRaises(InvalidAIResponseError):
            self.provider.get_json("p")

    def test_provider_error_propagates(self):
        FakeProvider.error = AIProviderError("boom")
        with self.assertRaises(AIProviderError):
            self.provider.get_json("p")

    def test_require_key_raises_when_missing(self):
        with self.assertRaises(InvalidAIResponseError):
            AIProvider.require_key({}, "projections")

    def test_require_key_returns_value(self):
        self.assertEqual(AIProvider.require_key({"a": "b"}, "a"), "b")

    def test_gemini_provider_requires_key(self):
        gemini = GeminiProvider(api_key="")
        with self.assertRaises(AIProviderError):
            gemini.generate("prompt")


class ProviderRegistryTests(TestCase):
    @override_settings(AI_PROVIDER="nonexistent", AI_PROVIDERS=FAKE_PROVIDERS)
    def test_unknown_provider_raises(self):
        with self.assertRaises(UnknownProviderError):
            get_provider()

    @override_settings(
        AI_PROVIDER="fake",
        AI_PROVIDERS=FAKE_PROVIDERS,
        AI_API_KEY="secret",
        AI_MODEL="model-x",
    )
    def test_registry_builds_provider_with_credentials(self):
        provider = get_provider()
        self.assertIsInstance(provider, FakeProvider)
        self.assertEqual(provider.api_key, "secret")
        self.assertEqual(provider.model, "model-x")

    @override_settings(AI_PROVIDER="fake", AI_PROVIDERS=FAKE_PROVIDERS, AI_API_KEY="")
    def test_provider_is_configured_requires_key(self):
        self.assertFalse(provider_is_configured())

    @override_settings(AI_PROVIDER="fake", AI_PROVIDERS=FAKE_PROVIDERS, AI_API_KEY="k")
    def test_provider_is_configured_with_key(self):
        self.assertTrue(provider_is_configured())


class NormalizeAnalysisTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.career = create_career()

    def test_normalize_level_coercion(self):
        self.assertEqual(normalize_level("advanced"), "Advanced")
        self.assertEqual(normalize_level("bogus"), "Beginner")
        self.assertEqual(normalize_level(None), "Beginner")

    def test_clean_string_list_dedupes_and_caps(self):
        values = ["a", "a", "b", "x" * 200]
        self.assertEqual(clean_string_list(values, 10), ["a", "b"])
        many = [f"item-{i}" for i in range(30)]
        self.assertEqual(len(clean_string_list(many, 12)), 12)

    def test_clean_string_list_rejects_non_lists(self):
        self.assertEqual(clean_string_list("nope", 5), [])

    def test_clean_projects(self):
        projects = ["Just a string", {"title": "Build X", "difficulty": "hard"}, {"title": ""}]
        cleaned = clean_projects(projects)
        self.assertEqual(cleaned[0]["title"], "Just a string")
        self.assertEqual(cleaned[1]["difficulty"], "Hard")
        self.assertEqual(len(cleaned), 2)

    def test_normalize_analysis_merges_database_gaps(self):
        ai_data = {
            "summary": "Solid fit.",
            "current_level": "Intermediate",
            "strengths": ["Python"],
            "skill_gaps": ["Deployment"],
            "learning_order": ["Containers"],
            "projects": [],
        }
        result = normalize_analysis(ai_data, self.user, self.career)
        # Python is already covered by the profile? No - the user has no skills,
        # so Python stays a gap and is merged in.
        self.assertIn("Python", result["skill_gaps"])
        self.assertIn("Containers", result["learning_order"])
        self.assertEqual(result["current_level"], "Intermediate")

    def test_normalize_analysis_adds_learning_order_from_db(self):
        result = normalize_analysis({}, self.user, self.career)
        self.assertIn("Python", result["skill_gaps"])
        self.assertEqual(result["learning_order"][0], "Python")
        self.assertTrue(result["summary"])  # default summary present


class AnalyzeCareerTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.career = create_career()

    @override_settings(AI_PROVIDER="fake", AI_PROVIDERS=FAKE_PROVIDERS, AI_API_KEY="k")
    def test_ai_success_is_cached_with_source_ai(self):
        FakeProvider.error = None
        FakeProvider.payload = {
            "summary": "Excellent match.",
            "current_level": "Expert",
            "strengths": ["Python"],
            "skill_gaps": ["Go"],
            "learning_order": ["Go"],
            "projects": [{"title": "Build an API", "difficulty": "medium"}],
        }
        analysis = analyze_career(self.user, self.career)
        self.assertEqual(analysis["current_level"], "Expert")
        stored = CareerAnalysis.objects.get(user=self.user, career=self.career)
        self.assertEqual(stored.source, "ai")

        # Second call returns cached content without hitting the provider.
        FakeProvider.payload = {"summary": "CHANGED"}
        again = analyze_career(self.user, self.career)
        self.assertEqual(again["summary"], "Excellent match.")

    @override_settings(AI_PROVIDER="fake", AI_PROVIDERS=FAKE_PROVIDERS)
    def test_ai_failure_falls_back_to_database(self):
        FakeProvider.error = AIProviderError("provider down")
        analysis = analyze_career(self.user, self.career)
        self.assertIn("summary", analysis)
        self.assertIn("skill_gaps", analysis)
        self.assertIn("Python", analysis["skill_gaps"])
        stored = CareerAnalysis.objects.get(user=self.user, career=self.career)
        self.assertEqual(stored.source, "fallback")

    @override_settings(AI_PROVIDER="fake", AI_PROVIDERS=FAKE_PROVIDERS, AI_API_KEY="k")
    def test_no_key_at_all_still_falls_back(self):
        analysis = analyze_career(self.user, self.career)
        self.assertIn("summary", analysis)
        self.assertTrue(CareerAnalysis.objects.filter(user=self.user, career=self.career).exists())

    @override_settings(AI_PROVIDER="fake", AI_PROVIDERS=FAKE_PROVIDERS, AI_API_KEY="k")
    def test_force_refresh_regenerates(self):
        FakeProvider.payload = {"summary": "First pass."}
        analyze_career(self.user, self.career)
        FakeProvider.payload = {"summary": "Refreshed."}
        analyze_career(self.user, self.career, force_refresh=True)
        stored = CareerAnalysis.objects.get(user=self.user, career=self.career)
        self.assertEqual(stored.content["summary"], "Refreshed.")


class AnalysisJsonViewTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.career = create_career()
        self.client.force_login(self.user)

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("ai_engine:analysis_json", args=[self.career.id]))
        self.assertEqual(response.status_code, 302)

    def test_returns_json(self):
        response = self.client.get(reverse("ai_engine:analysis_json", args=[self.career.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"].startswith("application/json"), True)
        payload = response.json()
        self.assertIn("summary", payload)
        self.assertIn("skill_gaps", payload)


def build_roadmap_fixture(user, career):
    """Create a small roadmap with two phases and a handful of Python-ish tasks."""
    from roadmap.models import Roadmap, RoadmapPhase, RoadmapTask

    roadmap = Roadmap.objects.create(user=user, career=career, title="Test Roadmap", duration_weeks=6)
    phase = RoadmapPhase.objects.create(roadmap=roadmap, title="Foundations", order=0, duration_weeks=2)
    for idx, title in enumerate(["Learn Python basics", "Set up Git", "Understand Linux basics"]):
        RoadmapTask.objects.create(phase=phase, title=title, order=idx)
    return roadmap


class SanitizeUrlTests(TestCase):
    def test_valid_https_url_accepted(self):
        self.assertEqual(sanitize_url("https://docs.python.org/3/"), "https://docs.python.org/3/")

    def test_valid_http_url_accepted(self):
        self.assertEqual(sanitize_url("http://example.com/x"), "http://example.com/x")

    def test_non_http_schemes_rejected(self):
        self.assertIsNone(sanitize_url("javascript:alert(1)"))
        self.assertIsNone(sanitize_url("ftp://example.com/x"))
        self.assertIsNone(sanitize_url("file:///etc/passwd"))

    def test_empty_and_none_rejected(self):
        self.assertIsNone(sanitize_url(""))
        self.assertIsNone(sanitize_url(None))
        self.assertIsNone(sanitize_url("   "))

    def test_whitespace_in_url_rejected(self):
        self.assertIsNone(sanitize_url("https://exa mple.com/x"))

    def test_overlong_url_rejected(self):
        self.assertIsNone(sanitize_url("https://example.com/" + "a" * 600))

    def test_non_string_rejected(self):
        self.assertIsNone(sanitize_url(123))

    def test_youtube_url_accepted(self):
        self.assertEqual(
            sanitize_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )

    def test_youtube_short_link_accepted(self):
        self.assertEqual(sanitize_youtube_url("https://youtu.be/dQw4w9WgXcQ"), "https://youtu.be/dQw4w9WgXcQ")

    def test_youtube_rejects_non_youtube_links(self):
        self.assertIsNone(sanitize_youtube_url("https://docs.python.org/3/"))
        self.assertIsNone(sanitize_youtube_url("javascript:alert(1)"))


class CuratedResourcesTests(TestCase):
    def test_skill_keyword_matches_title(self):
        links = curated_resources_for("Practice Python programming")
        self.assertTrue(any("python" in url for _label, url in links))

    def test_unknown_task_falls_back_to_general(self):
        links = curated_resources_for("Completely unrelated brainstorming activity")
        self.assertEqual(links, [("freeCodeCamp", "https://www.freecodecamp.org/learn/"), ("Coursera", "https://www.coursera.org/")])

    def test_match_is_case_insensitive(self):
        links = curated_resources_for("DJANGO vs Flask")
        self.assertTrue(any("django" in url for _label, url in links))


class ParseAiResourcesTests(TestCase):
    def test_valid_entries_are_extracted(self):
        raw = {
            "resources": [
                {"phase": "Foundations", "task": "Learn Python basics", "resource_url": "https://docs.python.org/3/", "description": "Official docs"},
                {"phase": "Foundations", "task": "Set up Git", "resource_url": "javascript:bad", "description": "must be skipped"},
            ]
        }
        entries, errors = parse_ai_resources(raw)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["task"], "Learn Python basics")
        self.assertEqual(len(errors["skipped"]), 1)

    def test_missing_resources_key_rejected(self):
        with self.assertRaises(InvalidAIResponseError):
            parse_ai_resources({"foo": []})

    def test_non_list_resources_rejected(self):
        with self.assertRaises(InvalidAIResponseError):
            parse_ai_resources({"resources": "nope"})

    def test_entry_missing_phase_or_task_skipped(self):
        entries, errors = parse_ai_resources(
            {"resources": [{"task": "x", "resource_url": "https://a.io"}, {"phase": "p", "resource_url": "https://b.io"}]}
        )
        self.assertEqual(entries, [])
        self.assertGreaterEqual(len(errors["skipped"]), 2)

    def test_entry_includes_valid_video_fields(self):
        entries, _errors = parse_ai_resources(
            {"resources": [
                {
                    "phase": "Foundations",
                    "task": "Learn Python basics",
                    "resource_url": "https://docs.python.org/3/",
                    "video_title": "Python Full Course",
                    "video_url": "https://www.youtube.com/watch?v=abc123",
                }
            ]}
        )
        self.assertEqual(entries[0]["video_url"], "https://www.youtube.com/watch?v=abc123")
        self.assertEqual(entries[0]["video_title"], "Python Full Course")

    def test_invalid_video_url_is_dropped(self):
        entries, _errors = parse_ai_resources(
            {"resources": [
                {
                    "phase": "Foundations",
                    "task": "Learn Python basics",
                    "resource_url": "https://docs.python.org/3/",
                    "video_url": "https://notes.io/not-a-video",
                }
            ]}
        )
        self.assertEqual(entries[0]["video_url"], "")
        self.assertEqual(entries[0]["video_title"], "")


class EnrichRoadmapTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.career = create_career()
        self.roadmap = build_roadmap_fixture(self.user, self.career)

    @override_settings(AI_PROVIDER="fake", AI_PROVIDERS=FAKE_PROVIDERS, AI_API_KEY="k")
    def test_provider_success_uses_ai_resources(self):
        from ai_engine.tests import FakeProvider

        FakeProvider.error = None
        FakeProvider.payload = {
            "resources": [
                {"phase": "Foundations", "task": "Learn Python basics", "resource_url": "https://docs.python.org/3/tutorial/", "description": "The official Python tutorial."},
                {"phase": "Foundations", "task": "Set up Git", "resource_url": "https://git-scm.com/book/en/v2", "description": "Pro Git, free online."},
            ]
        }
        self.addCleanup(lambda: setattr(FakeProvider, "payload", {}))
        self.addCleanup(lambda: setattr(FakeProvider, "error", None))

        stats = enrich_roadmap_with_resources(self.user, self.career, self.roadmap)
        self.assertEqual(stats["with_resources"], 3)  # 2 AI + 1 curated fallback
        tasks = {t.title: t for t in self.roadmap.phases.first().tasks.all()}
        self.assertEqual(tasks["Learn Python basics"].resource_url, "https://docs.python.org/3/tutorial/")
        self.assertIn("official python tutorial", tasks["Learn Python basics"].description.lower())
        self.assertTrue(tasks["Understand Linux basics"].resource_url.startswith("https"))

    @override_settings(AI_PROVIDER="fake", AI_PROVIDERS=FAKE_PROVIDERS, AI_API_KEY="k")
    def test_provider_failure_falls_back_to_curated(self):
        from ai_engine.tests import FakeProvider

        FakeProvider.error = AIProviderError("provider down")
        FakeProvider.payload = {}
        self.addCleanup(lambda: setattr(FakeProvider, "error", None))

        stats = enrich_roadmap_with_resources(self.user, self.career, self.roadmap)
        self.assertEqual(stats["with_resources"], 3)
        for task in self.roadmap.phases.first().tasks.all():
            self.assertTrue(task.resource_url.startswith("https"))

    def test_unconfigured_provider_still_seeds_curated_links(self):
        # No AI key configured: provider raises and curated links are attached.
        stats = enrich_roadmap_with_resources(self.user, self.career, self.roadmap)
        self.assertEqual(stats["with_resources"], 3)
        for task in self.roadmap.phases.first().tasks.all():
            self.assertTrue(task.resource_url.startswith("https"))

    @override_settings(AI_PROVIDER="fake", AI_PROVIDERS=FAKE_PROVIDERS, AI_API_KEY="k")
    def test_ai_urls_are_sanitized_before_persist(self):
        from ai_engine.tests import FakeProvider

        FakeProvider.error = None
        FakeProvider.payload = {
            "resources": [
                {"phase": "Foundations", "task": "Learn Python basics", "resource_url": "javascript:alert(1)"},
                {"phase": "Foundations", "task": "Set up Git", "resource_url": "https://git-scm.com"},
            ]
        }
        self.addCleanup(lambda: setattr(FakeProvider, "payload", {}))
        self.addCleanup(lambda: setattr(FakeProvider, "error", None))

        enrich_roadmap_with_resources(self.user, self.career, self.roadmap)
        tasks = {t.title: t for t in self.roadmap.phases.first().tasks.all()}
        # javascript: URL must NOT be stored; curated fallback applies instead.
        self.assertTrue(tasks["Learn Python basics"].resource_url.startswith("https"))
        self.assertNotIn("javascript", tasks["Learn Python basics"].resource_url)
        self.assertEqual(tasks["Set up Git"].resource_url, "https://git-scm.com")


class GoogleSearchClientTests(TestCase):
    @override_settings(SERPAPI_API_KEY="")
    def test_not_configured_without_key(self):
        self.assertFalse(serpapi_configured())

    @override_settings(SERPAPI_API_KEY="k")
    def test_configured_with_key(self):
        self.assertTrue(serpapi_configured())

    @override_settings(SERPAPI_API_KEY="k")
    @mock.patch("ai_engine.services.google_search._get_json")
    def test_search_google_parses_organic_results(self, mock_get):
        mock_get.return_value = {
            "organic_results": [
                {"title": "Python Tutorial", "link": "https://docs.python.org/3/tutorial/", "snippet": "The best free python tutorial."},
                {"title": "Bad link", "link": "javascript:alert(1)", "snippet": "x"},
            ]
        }
        results = search_google("learn python", num=5)
        mock_get.assert_called_once()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Python Tutorial")
        self.assertEqual(results[0]["url"], "https://docs.python.org/3/tutorial/")
        self.assertIn("best free", results[0]["snippet"])

    @override_settings(SERPAPI_API_KEY="")
    def test_search_google_raises_when_unconfigured(self):
        with self.assertRaises(SerpAPIError):
            search_google("learn python")

    @override_settings(SERPAPI_API_KEY="k")
    @mock.patch("ai_engine.services.google_search._get_json")
    def test_search_google_raises_on_api_error(self, mock_get):
        mock_get.return_value = {"error": "Invalid API key"}
        with self.assertRaises(SerpAPIError):
            search_google("learn python")

    @override_settings(SERPAPI_API_KEY="k")
    @mock.patch("ai_engine.services.google_search._get_json")
    def test_search_google_propagates_network_errors(self, mock_get):
        mock_get.side_effect = SerpAPIError("boom")
        with self.assertRaises(SerpAPIError):
            search_google("learn python")

    def test_pick_best_result_prefers_learning_material(self):
        results = [
            {"title": "Sign in to continue", "url": "https://ad.example.com/", "snippet": "subscribe now"},
            {"title": "Learn Python — Free Tutorial", "url": "https://docs.python.org/3/tutorial/", "snippet": "get started"},
        ]
        picked = pick_best_result(results, "Learn Python basics")
        self.assertEqual(picked["url"], "https://docs.python.org/3/tutorial/")

    def test_pick_best_result_empty(self):
        self.assertIsNone(pick_best_result([], "Learn Python basics"))

    @override_settings(SERPAPI_API_KEY="k")
    @mock.patch("ai_engine.services.google_search._get_json")
    def test_search_youtube_parses_video_results(self, mock_get):
        mock_get.return_value = {
            "video_results": [
                {"title": "Learn Python — Full Course", "link": "https://www.youtube.com/watch?v=abc123", "snippet": "for beginners", "channel": "freeCodeCamp"},
                {"title": "Not a video", "link": "https://www.w3schools.com/python/", "snippet": "x"},
            ]
        }
        results = search_youtube("learn python tutorial")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["url"], "https://www.youtube.com/watch?v=abc123")
        self.assertEqual(results[0]["channel"], "freeCodeCamp")
        self.assertIn("Full Course", results[0]["title"])

    def test_pick_best_video_prefers_topic_match(self):
        results = [
            {"title": "Django overview", "url": "https://www.youtube.com/watch?v=1", "snippet": ""},
            {"title": "Learn Python for beginners", "url": "https://www.youtube.com/watch?v=2", "snippet": ""},
        ]
        picked = pick_best_video(results, "Learn Python basics")
        self.assertEqual(picked["url"], "https://www.youtube.com/watch?v=2")

    def test_pick_best_video_empty(self):
        self.assertIsNone(pick_best_video([], "Learn Python basics"))


class SearchTierTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.career = create_career()
        self.roadmap = build_roadmap_fixture(self.user, self.career)

    @override_settings(SERPAPI_API_KEY="")
    def test_enrich_without_serpapi_key_skips_search(self):
        stats = enrich_roadmap_with_resources(self.user, self.career, self.roadmap, use_search=True)
        self.assertEqual(stats.get("from_search", 0), 0)
        self.assertEqual(stats["with_resources"], 3)

    @override_settings(SERPAPI_API_KEY="k")
    @mock.patch("ai_engine.services.google_search.search_google")
    def test_enrich_uses_live_google_results_first(self, mock_search):
        mock_search.return_value = [
            {"title": "RealPython Tutorial", "url": "https://realpython.com/python-tutorial/", "snippet": "A great free tutorial."}
        ]
        stats = enrich_roadmap_with_resources(self.user, self.career, self.roadmap)
        self.assertEqual(stats["from_search"], 3)
        self.assertEqual(stats["with_resources"], 3)
        tasks = {t.title: t for t in self.roadmap.phases.first().tasks.all()}
        self.assertEqual(tasks["Learn Python basics"].resource_url, "https://realpython.com/python-tutorial/")
        self.assertIn("great free tutorial", tasks["Learn Python basics"].description.lower())

    @override_settings(
        AI_PROVIDER="fake",
        AI_PROVIDERS=FAKE_PROVIDERS,
        AI_API_KEY="k",
        SERPAPI_API_KEY="k",
    )
    @mock.patch("ai_engine.services.google_search.search_google")
    def test_google_outranks_ai_suggestion(self, mock_search):
        from ai_engine.tests import FakeProvider

        FakeProvider.error = None
        FakeProvider.payload = {
            "resources": [
                {"phase": "Foundations", "task": "Learn Python basics", "resource_url": "https://docs.python.org/3/", "description": "Official docs"},
            ]
        }
        self.addCleanup(lambda: setattr(FakeProvider, "payload", {}))
        self.addCleanup(lambda: setattr(FakeProvider, "error", None))

        mock_search.return_value = [
            {"title": "PEP Python", "url": "https://realpython.com/python-tutorial/", "snippet": "Tutorial"}
        ]
        stats = enrich_roadmap_with_resources(self.user, self.career, self.roadmap, use_ai=True)
        tasks = {t.title: t for t in self.roadmap.phases.first().tasks.all()}
        self.assertEqual(stats["from_search"], 3)
        self.assertEqual(tasks["Learn Python basics"].resource_url, "https://realpython.com/python-tutorial/")

    def test_build_search_query_contains_topic(self):
        query = build_search_query(self.career, "Set up Git")
        self.assertIn("Set up Git", query)
        self.assertIn("Backend Developer", query)

    @override_settings(SERPAPI_API_KEY="k")
    @mock.patch("ai_engine.services.google_search.search_google")
    def test_search_respects_query_cap(self, mock_search):
        from roadmap.models import RoadmapTask

        mock_search.return_value = [
            {"title": "T", "url": "https://example.com/t", "snippet": "s"}
        ]
        phase_tasks = {}
        for task in RoadmapTask.objects.filter(phase__roadmap=self.roadmap):
            phase_tasks.setdefault("foundations", {})[task.title.lower()] = task

        hits, used = search_resources_for_tasks(self.career, phase_tasks, max_queries=2)
        self.assertEqual(used, 2)
        self.assertEqual(mock_search.call_count, 2)
        self.assertEqual(len([n for phase in hits.values() for n in phase]), 2)


class VideoTierTests(TestCase):
    def setUp(self):
        self.user = create_user()
        self.career = create_career()
        self.roadmap = build_roadmap_fixture(self.user, self.career)

    @override_settings(AI_PROVIDER="fake", AI_PROVIDERS=FAKE_PROVIDERS, AI_API_KEY="k")
    def test_ai_video_is_saved_without_serpapi(self):
        from ai_engine.tests import FakeProvider

        FakeProvider.error = None
        FakeProvider.payload = {
            "resources": [
                {"phase": "Foundations", "task": "Learn Python basics", "resource_url": "https://docs.python.org/3/", "video_title": "Python Full Course", "video_url": "https://www.youtube.com/watch?v=abc123"},
            ]
        }
        self.addCleanup(lambda: setattr(FakeProvider, "payload", {}))
        self.addCleanup(lambda: setattr(FakeProvider, "error", None))

        stats = enrich_roadmap_with_resources(self.user, self.career, self.roadmap)
        tasks = {t.title: t for t in self.roadmap.phases.first().tasks.all()}
        self.assertEqual(stats["with_videos"], 1)
        self.assertEqual(stats["from_video_ai"], 1)
        self.assertEqual(tasks["Learn Python basics"].video_url, "https://www.youtube.com/watch?v=abc123")
        self.assertEqual(tasks["Learn Python basics"].video_title, "Python Full Course")

    @override_settings(AI_PROVIDER="fake", AI_PROVIDERS=FAKE_PROVIDERS, AI_API_KEY="k")
    def test_invalid_ai_video_url_is_ignored(self):
        from ai_engine.tests import FakeProvider

        FakeProvider.error = None
        FakeProvider.payload = {
            "resources": [
                {"phase": "Foundations", "task": "Learn Python basics", "resource_url": "https://docs.python.org/3/", "video_url": "javascript:alert(1)"},
            ]
        }
        self.addCleanup(lambda: setattr(FakeProvider, "payload", {}))
        self.addCleanup(lambda: setattr(FakeProvider, "error", None))

        stats = enrich_roadmap_with_resources(self.user, self.career, self.roadmap)
        tasks = {t.title: t for t in self.roadmap.phases.first().tasks.all()}
        self.assertEqual(stats["with_videos"], 0)
        self.assertEqual(tasks["Learn Python basics"].video_url, "")
        self.assertEqual(tasks["Learn Python basics"].resource_url, "https://docs.python.org/3/")

    @override_settings(SERPAPI_API_KEY="")
    def test_unconfigured_search_has_no_videos(self):
        stats = enrich_roadmap_with_resources(self.user, self.career, self.roadmap)
        self.assertEqual(stats["with_videos"], 0)
        for task in self.roadmap.phases.first().tasks.all():
            self.assertEqual(task.video_url, "")
            self.assertTrue(task.resource_url.startswith("https"))

    @override_settings(SERPAPI_API_KEY="k")
    @mock.patch("ai_engine.services.google_search.search_google")
    @mock.patch("ai_engine.services.google_search.search_youtube")
    def test_live_youtube_results_populate_videos(self, mock_video, mock_search):
        mock_search.return_value = [
            {"title": "A", "url": "https://example.com/a", "snippet": "s"}
        ]
        mock_video.return_value = [
            {"title": "Set up Git full tutorial", "url": "https://www.youtube.com/watch?v=git000", "snippet": "for beginners", "channel": "Tech Channel"}
        ]
        stats = enrich_roadmap_with_resources(self.user, self.career, self.roadmap)
        self.assertEqual(stats["with_videos"], 3)
        self.assertEqual(stats["from_video_search"], 3)
        tasks = {t.title: t for t in self.roadmap.phases.first().tasks.all()}
        self.assertEqual(tasks["Set up Git"].video_url, "https://www.youtube.com/watch?v=git000")
        self.assertEqual(tasks["Set up Git"].video_title, "Set up Git full tutorial")

    @override_settings(
        AI_PROVIDER="fake",
        AI_PROVIDERS=FAKE_PROVIDERS,
        AI_API_KEY="k",
        SERPAPI_API_KEY="k",
    )
    @mock.patch("ai_engine.services.google_search.search_google")
    @mock.patch("ai_engine.services.google_search.search_youtube")
    def test_live_youtube_outranks_ai_video(self, mock_video, mock_search):
        from ai_engine.tests import FakeProvider

        FakeProvider.error = None
        FakeProvider.payload = {
            "resources": [
                {"phase": "Foundations", "task": "Learn Python basics", "resource_url": "https://docs.python.org/3/", "video_title": "AI Video", "video_url": "https://www.youtube.com/watch?v=ai001"},
            ]
        }
        self.addCleanup(lambda: setattr(FakeProvider, "payload", {}))
        self.addCleanup(lambda: setattr(FakeProvider, "error", None))

        mock_search.return_value = []  # no live Google resource results
        mock_video.return_value = [
            {"title": "Learn Python basics live", "url": "https://www.youtube.com/watch?v=live9", "snippet": "s", "channel": "c"}
        ]
        stats = enrich_roadmap_with_resources(self.user, self.career, self.roadmap)
        tasks = {t.title: t for t in self.roadmap.phases.first().tasks.all()}
        self.assertEqual(stats["from_video_search"], 3)
        self.assertEqual(tasks["Learn Python basics"].video_url, "https://www.youtube.com/watch?v=live9")

    def test_build_video_query_contains_topic(self):
        query = build_video_query(self.career, "Set up Git")
        self.assertIn("Set up Git", query)
        self.assertIn("Backend Developer", query)

    @override_settings(SERPAPI_API_KEY="k")
    @mock.patch("ai_engine.services.google_search.search_youtube")
    def test_video_search_respects_query_cap(self, mock_video):
        from roadmap.models import RoadmapTask

        mock_video.return_value = [
            {"title": "T", "url": "https://www.youtube.com/watch?v=v1", "snippet": "s", "channel": "c"}
        ]
        phase_tasks = {}
        for task in RoadmapTask.objects.filter(phase__roadmap=self.roadmap):
            phase_tasks.setdefault("foundations", {})[task.title.lower()] = task

        hits, used = search_videos_for_tasks(self.career, phase_tasks, max_queries=2)
        self.assertEqual(used, 2)
        self.assertEqual(mock_video.call_count, 2)
        self.assertEqual(len([n for phase in hits.values() for n in phase]), 2)