"""Dashboard statistics computed from persisted records only."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.models import Answer, InterviewSession
from app.repositories.sessions import SessionRepository
from app.schemas import (
    AnalyticsOverview,
    AnalyticsProgress,
    DimensionAverages,
    ProgressPoint,
)
from app.services.scoring import to_percentage

MAX_PROGRESS_POINTS = 50


def _round(v: object) -> float | None:
    return round(float(v), 2) if v is not None else None  # type: ignore[arg-type]


class AnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.sessions = SessionRepository(db)

    async def overview(self, user: CurrentUser) -> AnalyticsOverview:
        sessions = await self.sessions.all_owned(user.id)
        stats = await self.sessions.stats_for([s.id for s in sessions])

        row = (
            await self.db.execute(
                select(
                    func.avg(Answer.overall_score),
                    func.avg(Answer.score_clarity),
                    func.avg(Answer.score_specificity),
                    func.avg(Answer.score_result_orientation),
                    func.avg(Answer.score_relevance),
                ).where(Answer.user_id == user.id, Answer.evaluation_status == "completed")
            )
        ).one()

        recent = next(
            (
                s
                for s in sorted(sessions, key=lambda s: s.created_at, reverse=True)
                if stats[s.id].average_overall is not None
            ),
            None,
        )
        recent_avg = stats[recent.id].average_overall if recent else None

        return AnalyticsOverview(
            total_sessions=len(sessions),
            completed_interviews=sum(1 for s in sessions if s.status == "completed"),
            total_questions_answered=sum(st.answered_count for st in stats.values()),
            evaluated_answers=sum(st.evaluated_count for st in stats.values()),
            average_score=to_percentage(row[0]) if row[0] is not None else None,
            most_recent_session_score=to_percentage(recent_avg) if recent_avg is not None else None,
            most_recent_session_id=recent.id if recent else None,
            dimension_averages=DimensionAverages(
                clarity=_round(row[1]),
                specificity=_round(row[2]),
                result_orientation=_round(row[3]),
                relevance=_round(row[4]),
            ),
            includes_demo_data=any(s.is_demo for s in sessions),
        )

    async def progress(self, user: CurrentUser) -> AnalyticsProgress:
        stmt = (
            select(
                InterviewSession.id,
                InterviewSession.job_title,
                InterviewSession.company,
                InterviewSession.created_at,
                InterviewSession.is_demo,
                func.avg(Answer.overall_score),
                func.count(Answer.overall_score),
            )
            .join(Answer, Answer.session_id == InterviewSession.id)
            .where(
                InterviewSession.user_id == user.id,
                Answer.evaluation_status == "completed",
            )
            .group_by(
                InterviewSession.id,
                InterviewSession.job_title,
                InterviewSession.company,
                InterviewSession.created_at,
                InterviewSession.is_demo,
            )
            .order_by(InterviewSession.created_at.desc())
            .limit(MAX_PROGRESS_POINTS)
        )
        rows = (await self.db.execute(stmt)).all()
        points = [
            ProgressPoint(
                session_id=r[0],
                job_title=r[1],
                company=r[2],
                date=r[3],
                is_demo=r[4],
                average_score=to_percentage(r[5]),
                evaluated_count=r[6],
            )
            for r in reversed(rows)
        ]
        return AnalyticsProgress(points=points)
