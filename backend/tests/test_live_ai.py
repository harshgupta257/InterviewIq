"""Optional integration test against the real configured AI provider.

Skipped by default. Run with credentials in backend/.env:
    pytest -m live_ai
"""

import pytest

from app.ai.prompts import answer_evaluation
from app.ai.provider import build_provider
from app.ai.schemas import AnswerEvaluation
from app.ai.structured import run_structured
from app.core.config import Settings

pytestmark = pytest.mark.live_ai


async def test_real_provider_returns_valid_evaluation() -> None:
    settings = Settings()
    if settings.ai_provider == "demo":
        pytest.skip("Set AI_PROVIDER=gemini or openai with an API key to run live tests.")
    provider = build_provider(settings)
    try:
        out = await run_structured(
            provider,
            operation="answer_evaluation",
            system_prompt=answer_evaluation.SYSTEM_PROMPT,
            payload=answer_evaluation.build_payload(
                question_text="How did you make your FastAPI service reliable?",
                category="technical",
                evaluation_focus=["Reliability"],
                job_title="Backend Engineer",
                role_type="software_engineering",
                seniority="mid",
                resume_excerpt="Built a FastAPI document-processing service.",
                jd_excerpt="Design reliable production APIs.",
                answer_text="I validated inputs with Pydantic, retried OCR calls with backoff and "
                "added a dead-letter table. Errors dropped from 4% to under 1%.",
            ),
            model_cls=AnswerEvaluation,
            max_retries=settings.ai_max_retries,
        )
    finally:
        await provider.aclose()
    assert 1 <= out.value.clarity <= 5
    assert out.value.one_thing_to_fix
