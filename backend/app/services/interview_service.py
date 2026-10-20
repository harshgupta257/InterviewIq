"""Interview session lifecycle: create, read, list, delete."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import QuestionCategory
from app.core.logging import get_logger
from app.core.security import CurrentUser
from app.models import InterviewSession, Question
from app.repositories.sessions import SessionRepository
from app.schemas import SessionCreate, SessionDetail, SessionList
from app.services.ai_gateway import AIGateway
from app.services.question_service import QuestionService
from app.services.serializers import session_detail, session_summary

log = get_logger(__name__)

# Present questions in a natural interview arc regardless of model output order.
CATEGORY_ORDER: dict[QuestionCategory, int] = {
    "motivation": 0,
    "technical": 1,
    "project_deepdive": 2,
    "behavioral": 3,
    "system_design": 4,
    "case_study": 4,
}


class InterviewService:
    def __init__(self, db: AsyncSession, gateway: AIGateway) -> None:
        self.repo = SessionRepository(db)
        self.gateway = gateway

    async def create(self, user: CurrentUser, data: SessionCreate) -> SessionDetail:
        # 1. AI work happens before any write: a failed generation leaves no partial rows.
        generated = await QuestionService(self.gateway).generate(user.id, data)

        session = InterviewSession(
            user_id=user.id,
            job_title=data.job_title,
            company=data.company,
            jd_text=data.jd_text,
            resume_text=data.resume_text,
            role_type=data.role_type,
            seniority_level=generated.seniority,
            difficulty=data.difficulty,
            status="in_progress",
            analysis_json=generated.analysis.model_dump(),
            ai_provider=self.gateway.provider.name,
            ai_model=generated.model,
            is_demo=self.gateway.is_demo,
        )
        ordered = sorted(generated.questions.questions, key=lambda q: CATEGORY_ORDER.get(q.category, 9))
        questions = [
            Question(
                question_text=q.question_text,
                category=q.category,
                difficulty=q.difficulty,
                why_this_question=q.why_this_question,
                source_context=list(q.source_context),
                evaluation_focus=list(q.evaluation_focus),
                order_index=i,
            )
            for i, q in enumerate(ordered)
        ]
        # 2. Session + questions persisted atomically.
        saved = await self.repo.create_with_questions(session, questions)
        log.info("session_created", extra={"session_id": str(saved.id), "questions": len(questions)})
        return await self.detail(user, saved.id)

    async def detail(self, user: CurrentUser, session_id: uuid.UUID) -> SessionDetail:
        session = await self.repo.get_owned(user.id, session_id, with_children=True)
        stats = (await self.repo.stats_for([session.id]))[session.id]
        return session_detail(session, stats)

    async def list(
        self,
        user: CurrentUser,
        *,
        search: str | None,
        role_type: str | None,
        status: str | None,
        sort: str,
        page: int,
        page_size: int,
    ) -> SessionList:
        rows, total = await self.repo.list_owned(
            user.id,
            search=search,
            role_type=role_type,
            status=status,
            sort=sort,
            page=page,
            page_size=page_size,
        )
        stats = await self.repo.stats_for([s.id for s in rows])
        return SessionList(
            items=[session_summary(s, stats[s.id]) for s in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def delete(self, user: CurrentUser, session_id: uuid.UUID) -> None:
        await self.repo.delete_owned(user.id, session_id)
        log.info("session_deleted", extra={"session_id": str(session_id)})
