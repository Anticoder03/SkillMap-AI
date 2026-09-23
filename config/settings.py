"""
Django settings for the CareerPath AI project.

Loads configuration from environment variables (via .env) and keeps
AI provider settings, recommendation weights, database and security
values in one place.
"""
import os
import sys
from pathlib import Path

from django.core.management.utils import get_random_secret_key
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env if present.
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    """Parse a boolean value from an environment variable."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int = 0) -> int:
    """Parse an integer value from an environment variable."""
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY") or get_random_secret_key()

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env_bool("DEBUG", True)

ALLOWED_HOSTS = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if host.strip()]

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    # Local apps
    "accounts",
    "assessment",
    "careers",
    "recommendations",
    "ai_engine",
    "roadmap",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "config.context_processors.active_page",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database
# --------------------------------------------------------------------------
# When DATABASE_NAME is provided, PostgreSQL is used (psycopg3). Otherwise the
# application falls back to a local SQLite database for zero-config setup.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

if os.getenv("DATABASE_NAME"):
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DATABASE_NAME"),
        "USER": os.getenv("DATABASE_USER", "postgres"),
        "PASSWORD": os.getenv("DATABASE_PASSWORD", ""),
        "HOST": os.getenv("DATABASE_HOST", "localhost"),
        "PORT": os.getenv("DATABASE_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Media files
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Authentication
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# Email backend (console in development)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# AI Provider configuration
# --------------------------------------------------------------------------
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").strip().lower()
AI_API_KEY = os.getenv("AI_API_KEY", "").strip()
AI_MODEL = os.getenv("AI_MODEL", "").strip()
AI_TIMEOUT_SECONDS = env_int("AI_TIMEOUT_SECONDS", 45)
AI_MAX_RETRIES = env_int("AI_MAX_RETRIES", 2)

AI_PROVIDERS = {
    "gemini": "ai_engine.services.providers.gemini.GeminiProvider",
    "openai": "ai_engine.services.providers.openai.OpenAIProvider",
    "nvidia": "ai_engine.services.providers.nvidia.NvidiaProvider",
    "ollama": "ai_engine.services.providers.ollama.OllamaProvider",
}

AI_MODELS = {
    "gemini": "gemini-2.0-flash",
    "openai": "gpt-4o-mini",
    "nvidia": "deepseek-ai/deepseek-r1",
    "ollama": "llama3.2",
}

# Google Search (SerpAPI) — used to find live learning resources for roadmap
# tasks. Optional: without a key, resource lookup falls back to AI/curated.
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "").strip()
SERPAPI_LOCATION = os.getenv("SERPAPI_LOCATION", "").strip()
SERPAPI_MAX_QUERIES = env_int("SERPAPI_MAX_QUERIES", 20)
SERPAPI_RESULTS_NUM = env_int("SERPAPI_RESULTS_NUM", 5)

# The test suite must stay hermetic: real keys from .env would otherwise fire
# live network calls (SerpAPI) mid-test and make results flaky/costly. Zero the
# API keys whenever the test runner is active; tests opt back in per-test via
# @override_settings.
if "test" in sys.argv:
    AI_API_KEY = ""
    SERPAPI_API_KEY = ""

# Recommendation engine weights (must sum to 1.0)
RECOMMENDATION_WEIGHTS = {
    "interest": 0.40,
    "skill": 0.35,
    "education": 0.15,
    "experience": 0.10,
}

RECOMMENDATION_LIMIT = env_int("RECOMMENDATION_LIMIT", 5)