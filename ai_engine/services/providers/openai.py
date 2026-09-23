"""OpenAI provider (Chat Completions REST API)."""
from .base import AIProvider, AIProviderError


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self, api_key: str = "", model: str = "", timeout: int = 45):
        super().__init__(api_key=api_key, model=model or "gpt-4o-mini", timeout=timeout)

    def generate(self, prompt: str, **kwargs) -> str:
        if not self.api_key:
            raise AIProviderError("AI_API_KEY is not configured for the OpenAI provider.")
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 3000,
            "response_format": {"type": "json_object"},
        }
        data = self._post_json(url, payload, headers={"Authorization": f"Bearer {self.api_key}"})
        return self._read_text(data)

    @staticmethod
    def _read_text(data: dict) -> str:
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIProviderError(f"Unexpected OpenAI response shape: {data}") from exc