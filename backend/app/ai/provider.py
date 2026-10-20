"""AI provider abstraction.

A provider turns (system prompt, user message) into raw JSON text plus usage data.
It performs exactly one network call per `complete()`; retries, JSON parsing and
schema validation live in `app.ai.structured`.

Providers talk to vendor REST APIs directly over httpx so timeouts, error mapping and
logging are fully under our control and no API key ever reaches the browser.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import Settings
from app.core.logging import get_logger

log = get_logger(__name__)

# Estimated USD per 1M tokens (input, output). Update when vendor pricing changes;
# these are used only for an approximate cost column, never billed.
PRICING_PER_MTOK: dict[str, tuple[float, float]] = {
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-flash-lite": (0.10, 0.40),
    "gemini-2.0-flash": (0.10, 0.40),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1-mini": (0.40, 1.60),
}


@dataclass
class AIRequest:
    operation: str
    system_prompt: str
    user_message: str
    # Original structured payload; used only by the offline demo provider.
    payload: dict[str, Any] = field(default_factory=dict)
    temperature: float = 0.4
    max_output_tokens: int = 4096


@dataclass
class AIUsage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None

    def estimated_cost(self, model: str) -> float | None:
        price = PRICING_PER_MTOK.get(model)
        if price is None or self.prompt_tokens is None:
            return None
        return (self.prompt_tokens * price[0] + (self.completion_tokens or 0) * price[1]) / 1e6


@dataclass
class AIResult:
    text: str
    usage: AIUsage
    # The model that actually produced the output (may be a fallback model).
    model: str | None = None


class ProviderError(Exception):
    """Raised by providers. `transient` errors may be retried."""

    def __init__(self, message: str, *, transient: bool, quota: bool = False, status: int | None = None):
        super().__init__(message)
        self.transient = transient
        self.quota = quota
        self.status = status


class AIProvider(ABC):
    name: str
    model: str
    is_demo: bool = False

    @abstractmethod
    async def complete(self, request: AIRequest) -> AIResult: ...

    async def aclose(self) -> None:  # pragma: no cover - default no-op
        return None


class _HTTPProvider(AIProvider):
    """Base for vendor HTTP APIs, with model fallback.

    `models[0]` is the primary model. When it is overloaded or unreachable (transient
    error: 5xx, 429, timeout), the same request is tried on the next model in the list
    before the error is surfaced to the retry loop. Permanent errors (bad key, bad
    request) are raised immediately: another model would fail the same way.
    """

    def __init__(self, models: list[str], timeout: float, client: httpx.AsyncClient | None = None) -> None:
        if not models:
            raise ValueError("At least one model is required.")
        self.models = models
        self.model = models[0]
        self._client = client or httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=10.0))

    async def aclose(self) -> None:
        await self._client.aclose()

    @abstractmethod
    async def _complete_with(self, model: str, request: AIRequest) -> AIResult: ...

    async def complete(self, request: AIRequest) -> AIResult:
        last: ProviderError | None = None
        for i, model in enumerate(self.models):
            try:
                result = await self._complete_with(model, request)
            except ProviderError as exc:
                if not exc.transient:
                    raise
                last = exc
                if i + 1 < len(self.models):
                    log.warning(
                        "ai_model_fallback",
                        extra={
                            "provider": self.name,
                            "from_model": model,
                            "to_model": self.models[i + 1],
                            "status": exc.status,
                        },
                    )
                continue
            result.model = model
            return result
        assert last is not None
        raise last

    async def _post(self, url: str, *, headers: dict[str, str], body: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self._client.post(url, headers=headers, json=body)
        except httpx.TimeoutException as exc:
            raise ProviderError("AI provider timed out.", transient=True) from exc
        except httpx.TransportError as exc:
            raise ProviderError("Could not reach AI provider.", transient=True) from exc

        if response.status_code == 429:
            raise ProviderError(
                "AI provider rate limit or quota exceeded.", transient=True, quota=True, status=429
            )
        if response.status_code >= 500:
            raise ProviderError(
                f"AI provider error ({response.status_code}).", transient=True, status=response.status_code
            )
        if response.status_code >= 400:
            # Configuration problems (bad key, bad model name): not retryable.
            log.error(
                "ai_provider_rejected_request",
                extra={"provider": self.name, "status": response.status_code},
            )
            raise ProviderError(
                f"AI provider rejected the request ({response.status_code}).",
                transient=False,
                status=response.status_code,
            )
        try:
            data: dict[str, Any] = response.json()
        except ValueError as exc:
            raise ProviderError("AI provider returned a non-JSON response.", transient=True) from exc
        return data


class GeminiProvider(_HTTPProvider):
    name = "gemini"
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(
        self, api_key: str, models: list[str], timeout: float, client: httpx.AsyncClient | None = None
    ) -> None:
        super().__init__(models, timeout, client)
        self._api_key = api_key

    async def _complete_with(self, model: str, request: AIRequest) -> AIResult:
        body = {
            "systemInstruction": {"parts": [{"text": request.system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": request.user_message}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": request.temperature,
                "maxOutputTokens": request.max_output_tokens,
            },
        }
        data = await self._post(
            f"{self.BASE_URL}/{model}:generateContent",
            headers={"x-goog-api-key": self._api_key, "Content-Type": "application/json"},
            body=body,
        )
        candidates = data.get("candidates") or []
        if not candidates:
            reason = (data.get("promptFeedback") or {}).get("blockReason", "no candidates")
            raise ProviderError(f"Gemini returned no output ({reason}).", transient=False)
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        meta = data.get("usageMetadata") or {}
        usage = AIUsage(
            prompt_tokens=meta.get("promptTokenCount"),
            completion_tokens=(meta.get("candidatesTokenCount") or 0) + (meta.get("thoughtsTokenCount") or 0),
        )
        return AIResult(text=text, usage=usage)


class OpenAIProvider(_HTTPProvider):
    name = "openai"
    URL = "https://api.openai.com/v1/chat/completions"

    def __init__(
        self, api_key: str, models: list[str], timeout: float, client: httpx.AsyncClient | None = None
    ) -> None:
        super().__init__(models, timeout, client)
        self._api_key = api_key

    async def _complete_with(self, model: str, request: AIRequest) -> AIResult:
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_message},
            ],
            "response_format": {"type": "json_object"},
            "temperature": request.temperature,
            "max_tokens": request.max_output_tokens,
        }
        data = await self._post(
            self.URL,
            headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
            body=body,
        )
        choices = data.get("choices") or []
        if not choices:
            raise ProviderError("OpenAI returned no choices.", transient=True)
        text = (choices[0].get("message") or {}).get("content") or ""
        meta = data.get("usage") or {}
        return AIResult(
            text=text,
            usage=AIUsage(meta.get("prompt_tokens"), meta.get("completion_tokens")),
        )


def build_provider(settings: Settings) -> AIProvider:
    models = settings.ai_models
    if settings.ai_provider == "gemini":
        return GeminiProvider(settings.gemini_api_key, models, settings.ai_timeout_seconds)
    if settings.ai_provider == "openai":
        return OpenAIProvider(settings.openai_api_key, models, settings.ai_timeout_seconds)
    from app.ai.demo_provider import DemoProvider

    return DemoProvider()
