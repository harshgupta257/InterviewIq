"""'Show a stronger answer' generation. Results are persisted and reused."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompts import answer_rewriting
from app.ai.schemas import AnswerRewrite
from app.core.rate_limit import RateLimiter
from app.core.security import CurrentUser
from app.models import utcnow
from app.repositories.answers import AnswerRepository
from app.repositories.sessions import SessionRepository
from app.schemas import AnswerOut
from app.services.ai_gateway import AIGateway, redact_contact_details
from app.services.serializers import answer_out


class RewriteService:
    def __init__(self, db: AsyncSession, gateway: AIGateway, limiter: RateLimiter) -> None:
        self.sessions = SessionRepository(db)
        self.answers = AnswerRepository(db)
        self.gateway = gateway
        self.limiter = limiter

    async def rewrite(self, user: CurrentUser, answer_id: uuid.UUID, *, regenerate: bool) -> AnswerOut:
        answer = await self.answers.get_owned(user.id, answer_id)
        if answer.rewrite_json and not regenerate:
            return answer_out(answer)  # cached: no AI call, no cost

        session = await self.sessions.get_owned(user.id, answer.session_id, with_children=True)
        question = next(q for q in session.questions if q.id == answer.question_id)
        self.limiter.check(str(user.id))

        feedback = (answer.feedback_json or {}).get("overall_feedback")
        outcome = await self.gateway.run(
            user_id=user.id,
            operation="answer_rewriting",
            system_prompt=answer_rewriting.SYSTEM_PROMPT,
            payload=answer_rewriting.build_payload(
                question_text=question.question_text,
                category=question.category,
                job_title=session.job_title,
                role_type=session.role_type,
                resume_excerpt=redact_contact_details(session.resume_text),
                jd_excerpt=redact_contact_details(session.jd_text[:5000]),
                answer_text=answer.answer_text,
                evaluation_feedback=feedback,
            ),
            model_cls=AnswerRewrite,
            temperature=0.5,
        )
        rw = outcome.value
        answer.ideal_answer = rw.improved_answer
        answer.rewrite_json = {
            **rw.model_dump(),
            "generated_at": utcnow().isoformat(),
            "provider": self.gateway.provider.name,
            "model": outcome.model,
            "prompt_version": answer_rewriting.VERSION,
            "is_demo": self.gateway.is_demo,
        }
        await self.answers.commit()
        return answer_out(answer)
