"""Model fallback in HTTP providers and config normalisation (no network: httpx MockTransport)."""

import json

import httpx
import pytest

from app.ai.provider import AIRequest, GeminiProvider, ProviderError
from app.ai.schemas import AnswerEvaluation
from app.ai.structured import run_structured
from app.core.config import Settings
from tests.conftest import EVALUATION


def _gemini_ok(text: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "candidates": [{"content": {"parts": [{"text": text}]}}],
            "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5},
        },
    )


def _provider(responses: dict[str, httpx.Response], calls: list[str]) -> GeminiProvider:
    def handler(request: httpx.Request) -> httpx.Response:
        model = request.url.path.rsplit("/", 1)[1].split(":")[0]
        calls.append(model)
        assert request.headers["x-goog-api-key"] == "test-key"
        return responses[model]

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return GeminiProvider("test-key", ["primary", "backup-1", "backup-2"], timeout=5, client=client)


def _req() -> AIRequest:
    return AIRequest(operation="answer_evaluation", system_prompt="s", user_message="u")


async def test_overloaded_primary_falls_back_to_next_model() -> None:
    calls: list[str] = []
    p = _provider(
        {
            "primary": httpx.Response(503, json={"error": {"message": "high demand"}}),
            "backup-1": _gemini_ok('{"ok": true}'),
            "backup-2": _gemini_ok("unused"),
        },
        calls,
    )
    result = await p.complete(_req())
    assert result.model == "backup-1"
    assert result.text == '{"ok": true}'
    assert calls == ["primary", "backup-1"]


async def test_permanent_error_does_not_try_other_models() -> None:
    calls: list[str] = []
    p = _provider(
        {"primary": httpx.Response(400, json={}), "backup-1": _gemini_ok("x"), "backup-2": _gemini_ok("x")},
        calls,
    )
    with pytest.raises(ProviderError) as exc:
        await p.complete(_req())
    assert not exc.value.transient
    assert calls == ["primary"]


async def test_all_models_overloaded_raises_transient() -> None:
    calls: list[str] = []
    busy = httpx.Response(503, json={})
    p = _provider({"primary": busy, "backup-1": busy, "backup-2": busy}, calls)
    with pytest.raises(ProviderError) as exc:
        await p.complete(_req())
    assert exc.value.transient and exc.value.status == 503
    assert calls == ["primary", "backup-1", "backup-2"]


async def test_structured_outcome_reports_the_model_that_answered() -> None:
    calls: list[str] = []
    p = _provider(
        {
            "primary": httpx.Response(429, json={}),
            "backup-1": _gemini_ok(json.dumps(EVALUATION)),
            "backup-2": _gemini_ok("x"),
        },
        calls,
    )
    out = await run_structured(
        p,
        operation="answer_evaluation",
        system_prompt="s",
        payload={},
        model_cls=AnswerEvaluation,
        max_retries=0,
        backoff_base=0,
    )
    assert out.model == "backup-1"
    assert out.value.relevance == 5


def test_settings_model_list_and_url_normalisation() -> None:
    s = Settings(
        _env_file=None,  # type: ignore[call-arg]
        ai_provider="gemini",
        gemini_api_key="k",
        ai_model="gemini-flash-latest",
        ai_fallback_models=" gemini-3.5-flash, gemini-flash-latest ,,gemini-3.1-flash-lite",
        supabase_url=" https://abc.supabase.co/rest/v1/ ",
    )
    assert s.ai_models == ["gemini-flash-latest", "gemini-3.5-flash", "gemini-3.1-flash-lite"]
    assert s.supabase_url == "https://abc.supabase.co"
