"""Session and question persistence. Every method is scoped by the owner's user_id.

Ownership failures raise NotFoundError (404) rather than 403 so that the existence of
other users' records is never revealed (IDOR protection).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, case, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models import Answer, InterviewSession, Question


@dataclass
class SessionStats:
    total_questions: int
    answered_count: int
    evaluated_count: int
    failed_count: int
    average_overall: Decimal | None  # mean overall_score on the 1-5 scale


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class SessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_with_questions(
        self, session: InterviewSession, questions: list[Question]
    ) -> InterviewSession:
        """Insert a session and all of its questions in one transaction (all or nothing)."""
        self.db.add(session)
        await self.db.flush()
        for q in questions:
            q.session_id = session.id
            self.db.add(q)
        await self.db.commit()
        return await self.get_owned(session.user_id, session.id, with_children=True)

    async def get_owned(
        self, user_id: uuid.UUID, session_id: uuid.UUID, *, with_children: bool = False
    ) -> InterviewSession:
        stmt = select(InterviewSession).where(
            InterviewSession.id == session_id, InterviewSession.user_id == user_id
        )
        if with_children:
            stmt = stmt.options(
                selectinload(InterviewSession.questions), selectinload(InterviewSession.answers)
            ).execution_options(populate_existing=True)
        result = (await self.db.execute(stmt)).scalar_one_or_none()
        if result is None:
            raise NotFoundError("Interview session not found.")
        return result

    async def delete_owned(self, user_id: uuid.UUID, session_id: uuid.UUID) -> None:
        # Questions and answers are removed by ON DELETE CASCADE foreign keys.
        result = await self.db.execute(
            delete(InterviewSession).where(
                InterviewSession.id == session_id, InterviewSession.user_id == user_id
            )
        )
        await self.db.commit()
        if result.rowcount == 0:
            raise NotFoundError("Interview session not found.")

    async def stats_for(self, session_ids: list[uuid.UUID]) -> dict[uuid.UUID, SessionStats]:
        if not session_ids:
            return {}
        q_rows = (
            await self.db.execute(
                select(Question.session_id, func.count(Question.id))
                .where(Question.session_id.in_(session_ids))
                .group_by(Question.session_id)
            )
        ).all()
        q_counts: dict[uuid.UUID, int] = {row[0]: int(row[1]) for row in q_rows}
        answer_rows = (
            await self.db.execute(
                select(
                    Answer.session_id,
                    func.count(Answer.id),
                    func.count(Answer.overall_score),
                    func.sum(case((Answer.evaluation_status == "failed", 1), else_=0)),
                    func.avg(Answer.overall_score),
                )
                .where(Answer.session_id.in_(session_ids))
                .group_by(Answer.session_id)
            )
        ).all()
        by_session = {row[0]: row for row in answer_rows}
        stats = {}
        for sid in session_ids:
            row = by_session.get(sid)
            avg = row[4] if row else None
            stats[sid] = SessionStats(
                total_questions=int(q_counts.get(sid, 0)),
                answered_count=int(row[1]) if row else 0,
                evaluated_count=int(row[2]) if row else 0,
                failed_count=int(row[3] or 0) if row else 0,
                average_overall=Decimal(str(avg)) if avg is not None else None,
            )
        return stats

    def _filtered(
        self, user_id: uuid.UUID, search: str | None, role_type: str | None, status: str | None
    ) -> Select[Any]:
        stmt = select(InterviewSession).where(InterviewSession.user_id == user_id)
        if search:
            pattern = f"%{_escape_like(search.strip().lower())}%"
            stmt = stmt.where(
                or_(
                    func.lower(InterviewSession.job_title).like(pattern, escape="\\"),
                    func.lower(func.coalesce(InterviewSession.company, "")).like(pattern, escape="\\"),
                )
            )
        if role_type:
            stmt = stmt.where(InterviewSession.role_type == role_type)
        if status:
            stmt = stmt.where(InterviewSession.status == status)
        return stmt

    async def list_owned(
        self,
        user_id: uuid.UUID,
        *,
        search: str | None,
        role_type: str | None,
        status: str | None,
        sort: str,
        page: int,
        page_size: int,
    ) -> tuple[list[InterviewSession], int]:
        base = self._filtered(user_id, search, role_type, status)
        total = (await self.db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

        stmt = base
        if sort in ("score_desc", "score_asc"):
            avg_sq = (
                select(Answer.session_id, func.avg(Answer.overall_score).label("avg_score"))
                .where(Answer.user_id == user_id)
                .group_by(Answer.session_id)
                .subquery()
            )
            stmt = stmt.outerjoin(avg_sq, avg_sq.c.session_id == InterviewSession.id)
            score_col = func.coalesce(avg_sq.c.avg_score, -1)
            stmt = stmt.order_by(
                score_col.desc() if sort == "score_desc" else score_col.asc(),
                InterviewSession.created_at.desc(),
            )
        elif sort == "date_asc":
            stmt = stmt.order_by(InterviewSession.created_at.asc())
        else:
            stmt = stmt.order_by(InterviewSession.created_at.desc())

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        rows = list((await self.db.execute(stmt)).scalars().all())
        return rows, int(total)

    async def mark_completed_if_done(self, session: InterviewSession, now: datetime) -> bool:
        stats = (await self.stats_for([session.id]))[session.id]
        done = stats.total_questions > 0 and stats.evaluated_count == stats.total_questions
        if done and session.status != "completed":
            session.status = "completed"
            session.completed_at = now
            await self.db.commit()
        return done

    async def all_owned(self, user_id: uuid.UUID) -> list[InterviewSession]:
        stmt = (
            select(InterviewSession)
            .where(InterviewSession.user_id == user_id)
            .order_by(InterviewSession.created_at.asc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        await self.db.execute(delete(InterviewSession).where(InterviewSession.user_id == user_id))
