"""Base class and shared helpers for AI providers."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Any


class AIProviderError(Exception):
    """Raised when an AI provider cannot complete a request."""


class InvalidAIResponseError(AIProviderError):
    """Raised when the provider returns content we cannot parse as JSON."""


class AIProvider(ABC):
    """Interface every AI provider must implement.

    Concrete providers only need to implement :meth:`generate`; the shared
    :meth:`get_json` handles JSON extraction/validation on top of it.
    """

    name = "base"

    def __init__(self, api_key: str = "", model: str = "", timeout: int = 45):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Send a prompt and return the raw text response."""

    def get_json(self, prompt: str, **kwargs: Any) -> dict:
        """Return a validated JSON object from the provider's response."""
        raw = self.generate(prompt, **kwargs)
        try:
            data = json.loads(self._extract_json(raw))
        except (json.JSONDecodeError, TypeError) as exc:
            raise InvalidAIResponseError(f"Provider returned malformed JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise InvalidAIResponseError("AI response is not a JSON object.")
        return data

    @staticmethod
    def _extract_json(raw: str) -> str:
        """Strip markdown code fences and trailing prose so ``json.loads`` works."""
        text = raw.strip()
        fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if fenced:
            text = fenced.group(1).strip()
        # Find the first balanced JSON object if there is surrounding text.
        if not text.startswith("{"):
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                text = text[start : end + 1]
        return text

    # -- Shared HTTP helper (stdlib-only, no extra dependencies) -----------
    def _post_json(self, url: str, payload: dict, headers: dict | None = None) -> dict:
        """POST a JSON payload and return the parsed JSON response."""
        headers = {"Content-Type": "application/json", **(headers or {})}
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:  # noqa: S310
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise AIProviderError(f"{self.name} HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise AIProviderError(f"{self.name} connection error: {exc.reason}") from exc
        except TimeoutError as exc:
            raise AIProviderError(f"{self.name} request timed out after {self.timeout}s") from exc

        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise AIProviderError(f"{self.name} returned non-JSON response") from exc

    # -- JSON safety -------------------------------------------------------

    @staticmethod
    def require_key(data: dict, key: str) -> str:
        """Raise if a required key is missing so malformed responses fail fast."""
        value = data.get(key)
        if value is None:
            raise InvalidAIResponseError(f"AI response missing required field: {key}")
        return str(value)