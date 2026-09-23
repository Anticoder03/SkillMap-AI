# CareerPath AI

An AI-powered career guidance platform built with Django. Users answer a short dynamic assessment, see transparently-scored career matches, receive AI-generated career analyses and skill-gap reports, and follow personalized learning roadmaps with progress tracking.

The key design decision: **the database is the source of truth, and AI is a feature on top of it.** If no AI key is configured (or the provider is down), the entire flow still works using structured, deterministic data — nothing breaks.

## Features

- **Multi-step assessment** — single-choice, multiple-choice, scale, and free-text questions, fully configurable in the Django admin.
- **Transparent career matching** — a rule-based engine scores every career against the user's interests, skills, education, and experience (weights: 40/35/15/10). Scores are *compatibility*, not guarantees.
- **AI career analysis** — strengths, skill gaps, learning order, suggested portfolio projects. Every AI response is validated, normalized, and merged with database facts.
- **Personalized roadmaps** — AI-proposed learning plans with phases and tasks, falling back to a knowledge-base-driven plan when the AI is unavailable.
- **Learning resources per task** — each task gets a real, live resource link recommended from **Google results via SerpAPI** (with a search snippet) **plus a YouTube video**, falling back to a Gemini suggestion, then to a curated map covering all seeded skills. URLs are validated before being saved, so every task always has a link.
- **Progress tracking** — mark tasks `not_started` / `in_progress` / `completed`; progress is calculated live for each phase and the whole roadmap.
- **Dashboard** — Chart.js visualizations of skills, match scores, and roadmap progress; profile completeness meter.
- **Pluggable AI providers** — Gemini, OpenAI, NVIDIA, and Ollama behind a single interface; swap via one environment variable.
- **Zero-config setup** — runs on SQLite out of the box; opt-in PostgreSQL via environment variables.
- **Fully offline frontend assets** — Tailwind (Play CDN build), Chart.js, and Font Awesome are vendored under `static/`.

## Tech Stack

| Layer       | Technology                                        |
|-------------|---------------------------------------------------|
| Backend     | Python 3.14, Django 6.1                           |
| API         | Django REST Framework (authentication-ready)       |
| Database    | SQLite (default) or PostgreSQL via psycopg3        |
| Frontend    | Django templates + Tailwind CSS + Chart.js + Font Awesome |
| AI          | Gemini / OpenAI / NVIDIA / Ollama REST (stdlib HTTP, no heavy deps) |
| Search      | SerpAPI Google Search for live learning-resource suggestions        |

## Architecture

The app is split into six Django apps that respect a strict dependency direction:

```
┌────────────┐   ┌────────────┐
│  accounts  │──▶│ assessment │──▶┌──────────────┐
│ (user/prof)│   │ (Q&A/blog) │   │   careers    │
└────────────┘   └────────────┘   │ (knowledge)  │
        │                         └──────┬───────┘
        │                                │
        ▼                                ▼
┌────────────────┐  ┌─────────────────────┐
│ recommendations│  │     ai_engine        │
│ (engine+score) │  │ (providers+analysis) │
└────────────────┘  └──────────┬──────────┘
        │                      │
        └──────────┬───────────┘
                   ▼
            ┌────────────┐
            │   roadmap  │
            │ (plans+track)│
            └────────────┘
```

**Hybrid matching pipeline** — for each career:

1. Structured data is scored by the rule engine (`recommendations/services/`).
2. The top matches are persisted as `Recommendation` rows.
3. When AI is configured, `ai_engine` adds analyses and refines roadmaps; failures fall back to the deterministic layer.

**AI provider abstraction** — every provider implements `generate()`; `get_json()` handles JSON extraction/validation, so malformed responses can never crash a request.

## Project Structure

```
config/                     # project settings, root URLs, context processors
accounts/                   # auth, profiles, dashboard, signals
assessment/                 # interests, skills, questions, answers, scoring
careers/                    # career knowledge base + seed command
recommendations/            # scorer (sub-scores) + matcher (weighted combine)
ai_engine/                  # provider registry, providers, analysis services
roadmap/                    # roadmaps, phases, tasks, progress
templates/                  # base + all app templates
static/                     # vendored Tailwind, Chart.js, Font Awesome, app.css/js
```

## Getting Started

### Prerequisites

- Python 3.12+ (developed on 3.14)

### 1. Clone and set up a virtual environment

```bash
git clone <repo-url> django-ai-path-finder
cd django-ai-path-finder

# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
copy .env.example .env     # Windows
cp .env.example .env       # macOS / Linux
```

Edit `.env` and set `SECRET_KEY` at minimum. AI is optional — see [AI configuration](#ai-configuration).

### 4. Apply migrations

```bash
python manage.py migrate
```

### 5. Seed the knowledge base

Loads interests, skills, 16 careers with skill/interest mappings, and 22 assessment questions (idempotent):

```bash
python manage.py seed_careers
```

### 6. Run the server

```bash
python manage.py runserver
```

Open http://127.0.0.1:8000 — register an account, complete the assessment, and explore your recommendations and roadmap.

### Create an admin account (optional)

```bash
python manage.py createsuperuser
```

## AI Configuration

No AI key is required to run the app. To enable AI features, set these in `.env`:

| Variable           | Description                                              | Example                            |
|--------------------|----------------------------------------------------------|------------------------------------|
| `AI_PROVIDER`      | `gemini`, `openai`, `nvidia`, or `ollama`                | `gemini`                           |
| `AI_API_KEY`       | Provider API key (omit for Ollama)                       | `AIza...`                          |
| `AI_MODEL`         | Optional per-provider model override                     | (empty uses defaults)              |
| `AI_TIMEOUT_SECONDS` | Seconds before an AI call fails over to structured data | `45`                              |

### Learning Resources (SerpAPI, optional)

Resource lookup uses a three-tier priority:

1. **Live Google results** — SerpAPI searches `learn <task> for <career> - best free online course`, picks the most useful organic result (favouring docs/tutorials, penalising ads/login walls), and saves its URL + snippet.
2. **AI suggestion** — the configured provider proposes a well-known free resource per task.
3. **Curated map** — a curated resource covering every seeded skill (MDN, Django docs, Pro Git, freeCodeCamp, etc.) so nothing is ever left empty.

**YouTube videos (best-effort):** the same refresh also finds a real video per task:

1. **Live YouTube results** — SerpAPI `engine=youtube` search chooses a topic-matched video and saves its link + channel name.
2. **AI-suggested video** — returned in the same AI call as the resource (optional extra).
3. If neither finds one, the task simply shows no video — the resource link is always present.

Set these in `.env` to enable the live-search tiers:

| Variable              | Description                                                | Example           |
|-----------------------|------------------------------------------------------------|-------------------|
| `SERPAPI_API_KEY`     | API key from https://serpapi.com                           | `a1b2c...`        |
| `SERPAPI_LOCATION`    | Optional search location (country context)                 | `United States`   |
| `SERPAPI_MAX_QUERIES` | Max Google searches per resource refresh (rate-limit guard) | `20`             |
| `SERPAPI_RESULTS_NUM` | Organic results fetched per search                         | `5`               |

Without a key the tiers are skipped entirely and the flow falls back to AI/curated. Searches are deduplicated and capped (one Google + one YouTube query per unique task) so one refresh cannot burn your quota.

AI usage happens at three points — the **career analysis**, the **roadmap plan**, and the **per-task resource lookup**. All three degrade automatically: no key, a bad response, or a network failure simply drops that tier and keeps structured/curated data.

Defaults (in `config/settings.py`):

- Gemini → `gemini-2.0-flash`
- OpenAI → `gpt-4o-mini`
- NVIDIA → `deepseek-ai/deepseek-r1`
- Ollama → `llama3.2` (run locally: `ollama serve` with the model pulled)

## Recommendation Weights

Configured in `config/settings.py` (weights must sum to 1.0). The result limit is also configurable via `RECOMMENDATION_LIMIT` in `.env`:

```python
RECOMMENDATION_WEIGHTS = {
    "interest": 0.40,
    "skill": 0.35,
    "education": 0.15,
    "experience": 0.10,
}
RECOMMENDATION_LIMIT = 5  # top matches persisted per user (env var)
```

## Running Tests

The suite covers accounts/auth, the assessment flow, the scoring engine, AI JSON validation + fallback behaviour, roadmap generation and progress, SerpAPI/Search-tier resource lookup, and cross-user security:

```bash
python manage.py test
```

198+ tests, no AI key required (provider failures are exercised deliberately to prove the fallbacks).

## Using PostgreSQL

Install the driver and set env vars; the app switches automatically:

```bash
pip install "psycopg[binary]"
# .env
DATABASE_NAME=careerpath
DATABASE_USER=postgres
DATABASE_PASSWORD=secret
DATABASE_HOST=localhost
DATABASE_PORT=5432
python manage.py migrate
```

## Frequently Used Commands

```bash
python manage.py check                 # system checks
python manage.py makemigrations        # new model changes
python manage.py migrate               # apply migrations
python manage.py seed_careers          # (re)seed interests/skills/careers/questions
python manage.py seed_careers --reset  # wipe and reseed
python manage.py test                  # test suite
python manage.py createsuperuser       # admin access
```

## Limitations & Future Improvements

- **No real preference data** — the `preference_score` currently returns a neutral 0.5; the scorer is structured so preference criteria (e.g., work mode, location) can be added without touching the matcher.
- **Single highest-level caching** — `CareerAnalysis` is cached until `force_refresh` is passed; add a background refresh job for stale analyses.
- **Recommendation deck size** — the engine ranks all careers; for very large catalogs, add a candidate-retrieval stage before scoring.
- **Frontend** — current UI is server-rendered templates; the `ai_engine` JSON endpoint (`/ai/analysis/<career_id>/`) is ready for a React/SPA frontend.
- **Localization** — strings are English-only; consider Django i18n for multi-language support.
- **Rate limiting** — AI calls can be throttled per user to control costs.