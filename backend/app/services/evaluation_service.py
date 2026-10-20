"""Answer submission and rubric-based evaluation.

Guarantees:
- The answer is committed before any AI call, so it survives evaluation failures.
- One answer per question (DB unique constraint); identical resubmits are idempotent.
- Questions are answered in order.
- An atomic claim prevents concurrent evaluations of the same answer (two tabs,
  double clicks), so scores are never written twice.
- The overall score is computed here, never taken from the model.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompts import answer_evaluation
from app.ai.schemas import AnswerEvaluation
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.logging import get_logger
from app.core.rate_limit import RateLimiter
from app.core.security import CurrentUser
from app.models import Answer, InterviewSession, Question, utcnow
from app.repositories.answers import AnswerRepository
from app.repositories.sessions import SessionRepository
from app.schemas import AnswerOut, AnswerSubmit
from app.services.ai_gateway import AIGateway, redact_contact_details
from app.services.scoring import compute_average
from app.services.serializers import answer_out

log = get_logger(__name__)


def candidate_context(session: InterviewSession) -> str:
    """Compact, contact-free candidate context for evaluation prompts."""
    a = session.analysis_json or {}
    parts = [a.get("candidate_summary", "")]
    if a.get("candidate_skills"):
        parts.append("Skills: " + ", ".join(a["candidate_skills"][:25]))
    for p in (a.get("candidate_projects") or [])[:6]:
        parts.append(f"Project: {p.get('name', '')} - {p.get('summary', '')}")
    text = "\n".join(x for x in parts if x).strip()
    return text or redact_contact_details(session.resume_text[:4000])


class EvaluationService:
    def __init__(self, db: AsyncSession, gateway: AIGateway, limiter: RateLimiter) -> None:
        self.sessions = SessionRepository(db)
        self.answers = AnswerRepository(db)
        self.gateway = gateway
        self.limiter = limiter

    async def submit(
        self, user: CurrentUser, session_id: uuid.UUID, data: AnswerSubmit
    ) -> tuple[AnswerOut, bool]:
        session = await self.sessions.get_owned(user.id, session_id, with_children=True)
        questions = sorted(session.questions, key=lambda q: q.order_index)
        question = next((q for q in questions if q.id == data.question_id), None)
        if question is None:
            raise NotFoundError("Question not found in this session.")

        existing = next((a for a in session.answers if a.question_id == question.id), None)
        if existing is not None:
            if existing.answer_text.strip() == data.answer_text.strip():
                return answer_out(existing), False  # idempotent duplicate submit
            raise ConflictError(
                "An answer has already been submitted for this question.", code="answer_exists"
            )

        answered = {a.question_id for a in session.answers}
        expected = next((q for q in questions if q.id not in answered), None)
        if expected is None or expected.id != question.id:
            raise ConflictError(
                "Please answer the questions in order.",
                code="out_of_order",
                details={"expected_question_id": str(expected.id) if expected else None},
            )

        self.limiter.check(str(user.id))

        answer, created = await self.answers.insert(
            Answer(
                question_id=question.id,
                session_id=session.id,
                user_id=user.id,
                answer_text=data.answer_text,
                evaluation_status="pending",
                answered_at=utcnow(),
            )
        )
        if not created:
            # Lost a race with a concurrent identical request; return the stored answer.
            return answer_out(answer), False

        await self._evaluate(user, session, question, answer)
        return answer_out(answer), True

    async def retry(self, user: CurrentUser, answer_id: uuid.UUID) -> AnswerOut:
        answer = await self.answers.get_owned(user.id, answer_id)
        if answer.evaluation_status == "completed":
            raise ConflictError("This answer has already been evaluated.", code="already_evaluated")
        session = await self.sessions.get_owned(user.id, answer.session_id, with_children=True)
        question = next(q for q in session.questions if q.id == answer.question_id)
        self.limiter.check(str(user.id))
        await self._evaluate(user, session, question, answer)
        return answer_out(answer)

    async def list_for_session(self, user: CurrentUser, session_id: uuid.UUID) -> list[AnswerOut]:
        session = await self.sessions.get_owned(user.id, session_id, with_children=True)
        order = {q.id: q.order_index for q in session.questions}
        return [answer_out(a) for a in sorted(session.answers, key=lambda a: order.get(a.question_id, 0))]

    async def _evaluate(
        self, user: CurrentUser, session: InterviewSession, question: Question, answer: Answer
    ) -> None:
        if not await self.answers.claim_for_evaluation(answer.id):
            # Another request is evaluating (or already evaluated) this answer.
            await self.answers.refresh(answer)
            if answer.evaluation_status == "evaluating":
                raise ConflictError(
                    "This answer is already being evaluated. Refresh in a moment.",
                    code="evaluation_in_progress",
                )
            return
        await self.answers.refresh(answer)

        payload = answer_evaluation.build_payload(
            question_text=question.question_text,
            category=question.category,
            evaluation_focus=list(question.evaluation_focus or []),
            job_title=session.job_title,
            role_type=session.role_type,
            seniority=session.seniority_level,
            resume_excerpt=candidate_context(session),
            jd_excerpt=redact_contact_details(session.jd_text[:5000]),
            answer_text=answer.answer_text,
        )
        try:
            outcome = await self.gateway.run(
                user_id=user.id,
                operation="answer_evaluation",
                system_prompt=answer_evaluation.SYSTEM_PROMPT,
                payload=payload,
                model_cls=AnswerEvaluation,
                temperature=0.1,
            )
        except AppError as exc:
            # Preserve the answer; record the failure so the user can retry.
            answer.evaluation_status = "failed"
            answer.evaluation_error = exc.message
            await self.answers.commit()
            log.warning("evaluation_failed", extra={"answer_id": str(answer.id), "code": exc.code})
            return

        ev = outcome.value
        answer.score_clarity = ev.clarity
        answer.score_specificity = ev.specificity
        answer.score_result_orientation = ev.result_orientation
        answer.score_relevance = ev.relevance
        answer.overall_score = compute_average(
            ev.clarity, ev.specificity, ev.result_orientation, ev.relevance
        )
        answer.feedback_json = {
            "clarity_reason": ev.clarity_reason,
            "specificity_reason": ev.specificity_reason,
            "result_orientation_reason": ev.result_orientation_reason,
            "relevance_reason": ev.relevance_reason,
            "overall_feedback": ev.overall_feedback,
            "one_thing_to_fix": ev.one_thing_to_fix,
            "provider": self.gateway.provider.name,
            "model": outcome.model,
            "prompt_version": answer_evaluation.VERSION,
            "is_demo": self.gateway.is_demo,
        }
        answer.evaluation_status = "completed"
        answer.evaluation_error = None
        answer.evaluated_at = utcnow()
        await self.answers.commit()
        await self.sessions.mark_completed_if_done(session, utcnow())
