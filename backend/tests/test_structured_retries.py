import pytest

from app.ai.provider import ProviderError
from app.ai.schemas import AnswerEvaluation, QuestionSet
from app.ai.structured import AttemptLog, run_structured
from app.core.exceptions import AIQuotaError, AIServiceError
from tests.conftest import EVALUATION, FakeProvider, question_set


async def _run(
    provider: FakeProvider,
    model_cls: type = AnswerEvaluation,
    retries: int = 2,
    log: AttemptLog | None = None,
):  # type: ignore[no-untyped-def]
    op = "answer_evaluation" if model_cls is AnswerEvaluation else "question_generation"
    return await run_structured(
        provider,
        operation=op,
        system_prompt="sys",
        payload={"x": 1},
        model_cls=model_cls,
        max_retries=retries,
        backoff_base=0,
        attempt_log=log,
    )


async def test_malformed_json_is_repaired() -> None:
    p = FakeProvider()
    p.queue("answer_evaluation", "this is not json", EVALUATION)
    out = await _run(p)
    assert out.attempts == 2
    assert "previous response was rejected" in p.calls[1].user_message


async def test_wrong_question_count_triggers_repair_with_reason() -> None:
    p = FakeProvider()
    bad = question_set()
    bad["questions"] = bad["questions"][:6]
    p.queue("question_generation", bad, question_set())
    out = await _run(p, QuestionSet)
    assert len(out.value.questions) == 8
    assert "Expected exactly 8 questions" in p.calls[1].user_message


async def test_retries_are_bounded() -> None:
    p = FakeProvider()
    p.queue("answer_evaluation", *["{}"] * 10)
    log = AttemptLog()
    with pytest.raises(AIServiceError) as exc:
        await _run(p, retries=2, log=log)
    assert exc.value.code == "ai_invalid_output"
    assert len(p.calls) == 3 and log.attempts == 3


async def test_transient_error_retried() -> None:
    p = FakeProvider()
    p.queue("answer_evaluation", ProviderError("timeout", transient=True), EVALUATION)
    out = await _run(p)
    assert out.attempts == 2


async def test_permanent_error_not_retried() -> None:
    p = FakeProvider()
    p.queue("answer_evaluation", ProviderError("bad key", transient=False, status=401))
    with pytest.raises(AIServiceError):
        await _run(p)
    assert len(p.calls) == 1


async def test_quota_error_surfaces_as_quota() -> None:
    p = FakeProvider()
    p.queue("answer_evaluation", *[ProviderError("429", transient=True, quota=True, status=429)] * 3)
    with pytest.raises(AIQuotaError):
        await _run(p)
    assert len(p.calls) == 3


async def test_out_of_range_score_rejected_not_clamped() -> None:
    p = FakeProvider()
    p.queue(
        "answer_evaluation",
        {**EVALUATION, "clarity": 9},
        {**EVALUATION, "clarity": 9},
        {**EVALUATION, "clarity": 9},
    )
    with pytest.raises(AIServiceError):
        await _run(p)
