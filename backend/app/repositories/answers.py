"""Answer persistence, including the idempotency and evaluation-claim primitives."""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models import AIUsageEvent, Answer, Profile, utcnow

# An evaluation stuck in "evaluating" longer than this (e.g. the worker crashed) may be
# reclaimed by a retry. Must exceed the worst-case AI call duration with retries.
STALE_EVALUATION_AFTER = timedelta(minutes=4)


class AnswerRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_owned(self, user_id: uuid.UUID, answer_id: uuid.UUID) -> Answer:
        stmt = select(Answer).where(Answer.id == answer_id, Answer.user_id == user_id)
        answer = (await self.db.execute(stmt)).scalar_one_or_none()
        if answer is None:
            raise NotFoundError("Answer not found.")
        return answer

    async def get_for_question(self, question_id: uuid.UUID) -> Answer | None:
        stmt = (
            select(Answer).where(Answer.question_id == question_id).execution_options(populate_existing=True)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_for_session(self, user_id: uuid.UUID, session_id: uuid.UUID) -> list[Answer]:
        stmt = select(Answer).where(Answer.session_id == session_id, Answer.user_id == user_id)
        return list((await self.db.execute(stmt)).scalars().all())

    async def insert(self, answer: Answer) -> tuple[Answer, bool]:
        """Insert an answer. Returns (answer, created). If a concurrent request already
        stored an answer for the question, returns the existing row with created=False."""
        self.db.add(answer)
        try:
            await self.db.commit()
            return answer, True
        except IntegrityError:
            await self.db.rollback()
            existing = await self.get_for_question(answer.question_id)
            if existing is None:  # pragma: no cover - integrity error for another reason
                raise
            return existing, False

    async def claim_for_evaluation(self, answer_id: uuid.UUID, *, allow_completed: bool = False) -> bool:
        """Atomically move an answer into 'evaluating'. Returns False if another request
        holds the claim, so two tabs can never evaluate (and bill) the same answer twice."""
        now = utcnow()
        claimable = [
            Answer.evaluation_status.in_(("pending", "failed")),
            and_(
                Answer.evaluation_status == "evaluating",
                Answer.updated_at < now - STALE_EVALUATION_AFTER,
            ),
        ]
        if allow_completed:
            claimable.append(Answer.evaluation_status == "completed")
        result = await self.db.execute(
            update(Answer)
            .where(Answer.id == answer_id, or_(*claimable))
            .values(
                evaluation_status="evaluating",
                evaluation_error=None,
                evaluation_attempts=Answer.evaluation_attempts + 1,
                updated_at=now,
            )
            .execution_options(synchronize_session=False)
        )
        await self.db.commit()
        return bool(result.rowcount)

    async def refresh(self, answer: Answer) -> Answer:
        await self.db.refresh(answer)
        return answer

    async def commit(self) -> None:
        await self.db.commit()

    async def delete_user_data(self, user_id: uuid.UUID) -> None:
        await self.db.execute(delete(AIUsageEvent).where(AIUsageEvent.user_id == user_id))
        await self.db.execute(delete(Profile).where(Profile.id == user_id))

    @staticmethod
    def now() -> datetime:
        return utcnow()
