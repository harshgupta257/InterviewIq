"""Single entry point for AI calls: runs structured generation and records usage metrics."""

import re
import uuid
from decimal import Decimal
from typing import Any, TypeVar

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.provider import AIProvider
from app.ai.structured import AttemptLog, StructuredOutcome, run_structured
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.models import AIUsageEvent

log = get_logger(__name__)
T = TypeVar("T", bound=BaseModel)

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
_URL = re.compile(r"https?://\S+|(?:www\.)?(?:linkedin|github)\.com/\S+", re.IGNORECASE)


def redact_contact_details(text: str) -> str:
    """Strip contact details that the AI never needs (data minimisation)."""
    text = _EMAIL.sub("[email]", text)
    text = _URL.sub("[link]", text)
    return _PHONE.sub("[phone]", text)


class AIGateway:
    def __init__(
        self,
        provider: AIProvider,
        usage_session_factory: async_sessionmaker[AsyncSession],
        max_retries: int,
        backoff_base: float = 1.0,
    ) -> None:
        self.provider = provider
        self._usage_factory = usage_session_factory
        self.max_retries = max_retries
        self.backoff_base = backoff_base

    @property
    def is_demo(self) -> bool:
        return self.provider.is_demo

    async def run(
        self,
        *,
        user_id: uuid.UUID,
        operation: str,
        system_prompt: str,
        payload: dict[str, Any],
        model_cls: type[T],
        temperature: float = 0.4,
        provider: AIProvider | None = None,
    ) -> StructuredOutcome[T]:
        active = provider or self.provider
        attempt_log = AttemptLog()
        status = "success"
        model = active.model
        try:
            outcome = await run_structured(
                active,
                operation=operation,
                system_prompt=system_prompt,
                payload=payload,
                model_cls=model_cls,
                max_retries=self.max_retries,
                temperature=temperature,
                attempt_log=attempt_log,
                backoff_base=self.backoff_base,
            )
            model = outcome.model or model
            return outcome
        except AppError:
            status = "failed"
            raise
        finally:
            await self._record(user_id, operation, active, model, status, attempt_log)

    async def _record(
        self,
        user_id: uuid.UUID,
        operation: str,
        provider: AIProvider,
        model: str,
        status: str,
        a: AttemptLog,
    ) -> None:
        from app.ai.provider import AIUsage

        cost = AIUsage(a.prompt_tokens or None, a.completion_tokens or None).estimated_cost(model)
        try:
            async with self._usage_factory() as db:
                db.add(
                    AIUsageEvent(
                        user_id=user_id,
                        operation=operation,
                        provider=provider.name,
                        model=model,
                        status=status,
                        attempts=a.attempts,
                        duration_ms=a.duration_ms,
                        prompt_tokens=a.prompt_tokens or None,
                        completion_tokens=a.completion_tokens or None,
                        estimated_cost_usd=Decimal(str(round(cost, 6))) if cost is not None else None,
                        error_type=a.error_type,
                    )
                )
                await db.commit()
        except Exception:  # noqa: BLE001 - usage tracking must never break the request
            log.warning("ai_usage_record_failed", extra={"operation": operation})
