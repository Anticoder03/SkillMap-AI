"""NVIDIA NIM provider (OpenAI-compatible endpoint)."""
from .base import AIProvider, AIProviderError


class NvidiaProvider(AIProvider):
    name = "nvidia"

    def __init__(self, api_key: str = "", model: str = "", timeout: int = 45):
        super().__init__(api_key=api_key, model=model or "deepseek-ai/deepseek-r1", timeout=timeout)

    def generate(self, prompt: str, **kwargs) -> str:
        if not self.api_key:
            raise AIProviderError("AI_API_KEY is not configured for the Nvidia provider.")
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 2048,
            "stream": False,
        }
        data = self._post_json(url, payload, headers={"Authorization": f"Bearer {self.api_key}"})
        return self._read_text(data)

    @staticmethod
    def _read_text(data: dict) -> str:
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIProviderError(f"Unexpected NVIDIA response shape: {data}") from exc