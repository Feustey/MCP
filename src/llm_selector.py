import os
from typing import Any, Dict, Optional
import asyncio

import httpx


DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()


def ask_llm_choice() -> str:
    """Return the configured LLM provider.

    The project now only supports managed APIs (OpenAI by default).  Consumers that
    previously relied on interactive prompts or legacy local providers will now fall
    back to OpenAI automatically.  Behaviour can be overridden by exporting
    ``LLM_PROVIDER``.
    """
    return DEFAULT_PROVIDER


class OpenAILLM:
    """Minimal async wrapper around the OpenAI Chat and embedding endpoints."""

    def __init__(self, model: str = "gpt-3.5-turbo", **model_params: Any) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY must be defined to use the OpenAI client")

        self.api_key = api_key
        self.model = model
        self.model_params: Dict[str, Any] = {
            "temperature": 0.7,
            "max_tokens": 500,
            **model_params,
        }
        self.max_retries = 3
        self.retry_delay = 1  # seconds

    async def _post(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    return response.json()
            except Exception:  # pragma: no cover - logging handled upstream
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay)

        raise RuntimeError("OpenAI request failed after retries")

    async def generate(self, prompt: str) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            **self.model_params,
        }
        result = await self._post("https://api.openai.com/v1/chat/completions", payload)
        message = result["choices"][0]["message"]["content"]
        return {"text": message, "model": self.model, "success": True}

    async def acomplete(self, system_prompt: str, prompt: str) -> Any:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            **self.model_params,
        }
        result = await self._post("https://api.openai.com/v1/chat/completions", payload)
        message = result["choices"][0]["message"]["content"]
        return type("Response", (object,), {"text": message})

    async def get_embedding(self, text: str, *, model: str = "text-embedding-ada-002") -> list:
        payload = {"model": model, "input": text}
        result = await self._post("https://api.openai.com/v1/embeddings", payload)
        return result["data"][0]["embedding"]


def get_llm(llm_type: Optional[str] = None, **kwargs: Any) -> OpenAILLM:
    provider = (llm_type or DEFAULT_PROVIDER).lower()
    if provider != "openai":
        raise ValueError(f"Unsupported LLM provider '{provider}'. Only 'openai' is available.")
    return OpenAILLM(**kwargs)
