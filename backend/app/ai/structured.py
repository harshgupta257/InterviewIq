"""Structured-output runner: bounded retries, JSON repair and schema validation.

Failure handling:
- Transient provider errors (timeouts, 5xx, 429) are retried with exponential backoff.
- Invalid model output (malformed JSON, schema violations, wrong question count) is
  retried with a repair message describing the validation errors (never user data).
- Permanent provider errors (bad key, bad model) fail immediately.
Total attempts are capped at 1 + AI_MAX_RETRIES. Nothing is ever fabricated on failure.
"""

import asyncio
import json
import re
import time
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ValidationError

from app.ai.prompts import render_user_message
from app.ai.provider import AIProvider, AIRequest, AIUsage, ProviderError
from app.core.exceptions import AIQuotaError, AIServiceError
from app.core.logging import get_logger

log = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


@dataclass
class StructuredOutcome(Generic[T]):
    value: T
    attempts: int
    duration_ms: int
    usage: AIUsage
    # Model that produced the accepted output (a fallback model if the primary was overloaded).
    model: str = ""


@dataclass
class AttemptLog:
    attempts: int = 0
    duration_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    error_type: str | None = None


def extract_json(text: str) -> Any:
    """Parse a JSON object from model text, tolerating code fences and leading prose."""
    cleaned = _FENCE.sub("", text.strip())
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


def _summarise_validation(exc: ValidationError) -> str:
    lines = []
    for err in exc.errors()[:12]:
        loc = ".".join(str(p) for p in err.get("loc", ()))
        lines.append(f"- {loc or '(root)'}: {err.get('msg')}")
    return "\n".join(lines)


async def run_structured(
    provider: AIProvider,
    *,
    operation: str,
    system_prompt: str,
    payload: dict[str, Any],
    model_cls: type[T],
    max_retries: int,
    temperature: float = 0.4,
    attempt_log: AttemptLog | None = None,
    backoff_base: float = 1.0,
) -> StructuredOutcome[T]:
    schema = model_cls.model_json_schema()
    base_message = render_user_message(payload, schema)
    message = base_message
    total_attempts = 1 + max_retries
    usage = AIUsage(prompt_tokens=0, completion_tokens=0)
    started = time.perf_counter()
    last_error = "unknown error"
    record = attempt_log or AttemptLog()

    for attempt in range(1, total_attempts + 1):
        record.attempts = attempt
        try:
            result = await provider.complete(
                AIRequest(
                    operation=operation,
                    system_prompt=system_prompt,
                    user_message=message,
                    payload=payload,
                    temperature=temperature,
                )
            )
        except ProviderError as exc:
            last_error = str(exc)
            record.error_type = "quota" if exc.quota else ("transient" if exc.transient else "provider")
            log.warning(
                "ai_attempt_failed",
                extra={
                    "operation": operation,
                    "attempt": attempt,
                    "kind": record.error_type,
                    "status": exc.status,
                    "provider": provider.name,
                },
            )
            if not exc.transient or attempt == total_attempts:
                record.duration_ms = int((time.perf_counter() - started) * 1000)
                if exc.quota:
                    raise AIQuotaError(
                        "The AI provider's rate limit or quota has been reached. "
                        "Please try again in a few minutes."
                    ) from exc
                raise AIServiceError("The AI service is unavailable right now. Please try again.") from exc
            await asyncio.sleep(backoff_base * (2 ** (attempt - 1)))
            continue

        usage.prompt_tokens = (usage.prompt_tokens or 0) + (result.usage.prompt_tokens or 0)
        usage.completion_tokens = (usage.completion_tokens or 0) + (result.usage.completion_tokens or 0)
        record.prompt_tokens = usage.prompt_tokens or 0
        record.completion_tokens = usage.completion_tokens or 0

        try:
            value = model_cls.model_validate(extract_json(result.text))
        except (json.JSONDecodeError, ValueError) as exc:
            if isinstance(exc, ValidationError):
                problem = _summarise_validation(exc)
                record.error_type = "schema_validation"
            else:
                problem = "- The response was not a single valid JSON object."
                record.error_type = "malformed_json"
            last_error = problem
            log.warning(
                "ai_invalid_output",
                extra={
                    "operation": operation,
                    "attempt": attempt,
                    "kind": record.error_type,
                    "provider": provider.name,
                },
            )
            # Repair: resend the task plus the list of problems. User data is not echoed
            # back beyond the original payload.
            message = (
                base_message
                + "\n\nYour previous response was rejected for these reasons:\n"
                + problem
                + "\nReturn a corrected JSON object that satisfies every requirement."
            )
            continue

        duration_ms = int((time.perf_counter() - started) * 1000)
        record.duration_ms = duration_ms
        record.error_type = None
        log.info(
            "ai_call_succeeded",
            extra={
                "operation": operation,
                "provider": provider.name,
                "model": provider.model,
                "attempts": attempt,
                "duration_ms": duration_ms,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
            },
        )
        return StructuredOutcome(
            value=value,
            attempts=attempt,
            duration_ms=duration_ms,
            usage=usage,
            model=result.model or provider.model,
        )

    record.duration_ms = int((time.perf_counter() - started) * 1000)
    log.error("ai_output_invalid_after_retries", extra={"operation": operation, "attempts": total_attempts})
    raise AIServiceError(
        "The AI returned an invalid response after several attempts. Please try again.",
        code="ai_invalid_output",
        details={"reason": last_error[:500]},
    )
