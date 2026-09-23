"""Ollama provider (local, no API key required)."""
from .base import AIProvider, AIProviderError


class OllamaProvider(AIProvider):
    name = "ollama"

    def __init__(self, api_key: str = "", model: str = "", timeout: int = 120):
        # Local models can take a while on first generation.
        super().__init__(api_key=api_key, model=model or "llama3.2", timeout=timeout)

    def generate(self, prompt: str, **kwargs) -> str:
        url = f"{self.base_url.rstrip('/')}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        }
        data = self._post_json(url, payload)
        try:
            return data["response"]
        except KeyError as exc:
            raise AIProviderError(f"Unexpected Ollama response shape: {data}") from exc

    @property
    def base_url(self) -> str:
        import os

        return os.getenv("AI_PROVIDER_BASE_URL", "http://localhost:11434")