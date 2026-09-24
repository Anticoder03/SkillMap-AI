"""Google Gemini provider (REST API, stdlib HTTP)."""
from .base import AIProvider, AIProviderError


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self, api_key: str = "", model: str = "", timeout: int = 45):
        super().__init__(api_key=api_key, model=model or "gemini-3.6-flash", timeout=timeout)

    def generate(self, prompt: str, **kwargs) -> str:
        if not self.api_key:
            raise AIProviderError("AI_API_KEY is not configured for the Gemini provider.")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 4096,
            },
        }
        data = self._post_json(url, payload)
        return self._read_text(data)

    @staticmethod
    def _read_text(data: dict) -> str:
        try:
            parts = data["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIProviderError(f"Unexpected Gemini response shape: {data}") from exc
        return "".join(part.get("text", "") for part in parts if part.get("text"))