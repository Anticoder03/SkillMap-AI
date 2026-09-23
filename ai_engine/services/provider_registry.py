"""Registry that resolves the configured AI provider at runtime."""
from __future__ import annotations

import importlib

from django.conf import settings

from .providers.base import AIProvider, AIProviderError


class UnknownProviderError(AIProviderError):
    pass


def get_provider() -> AIProvider:
    """Instantiate the provider configured via ``AI_PROVIDER``."""
    name = getattr(settings, "AI_PROVIDER", "gemini")
    providers: dict = getattr(settings, "AI_PROVIDERS", {})
    models: dict = getattr(settings, "AI_MODELS", {})

    if name not in providers:
        raise UnknownProviderError(
            f"Unknown AI provider '{name}'. Choose from: {', '.join(providers)}"
        )

    path = providers[name]
    module_path, _, class_name = path.rpartition(".")
    module = importlib.import_module(module_path)
    provider_cls = getattr(module, class_name)

    return provider_cls(
        api_key=getattr(settings, "AI_API_KEY", ""),
        model=getattr(settings, "AI_MODEL", None) or models.get(name, ""),
        timeout=getattr(settings, "AI_TIMEOUT_SECONDS", 45),
    )


def provider_is_configured() -> bool:
    """Whether the provider setup is usable (key present for remote ones)."""
    name = getattr(settings, "AI_PROVIDER", "")
    if name == "ollama":
        return True
    return bool(getattr(settings, "AI_API_KEY", ""))