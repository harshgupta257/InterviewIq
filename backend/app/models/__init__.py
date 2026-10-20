"""SQLAlchemy ORM models.

These mirror supabase/migrations/*.sql, which are the source of truth for the
production schema (including RLS policies). SQLite create_all is used only for
local development, demo mode and tests.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    """Timezone-aware timestamps on every backend (SQLite drops tzinfo)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value


JSONType = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    pass


SESSION_STATUSES = ("in_progress", "completed", "failed")
EVALUATION_STATUSES = ("pending", "evaluating", "completed", "failed")
QUESTION_CATEGORIES = (
    "technical",
    "behavioral",
    "project_deepdive",
    "system_design",
    "motivation",
    "case_study",
)


class Profile(Base):
    __tablename__ = "profiles"

    # References auth.users(id) in Supabase (see migration); no FK here for SQLite.
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)


class InterviewSession(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint(f"status IN {SESSION_STATUSES}", name="sessions_status_check"),
        Index("ix_sessions_user_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    job_title: Mapped[str] = mapped_column(String(200), nullable=False)
    company: Mapped[str | None] = mapped_column(String(200))
    jd_text: Mapped[str] = mapped_column(Text, nullable=False)
    resume_text: Mapped[str] = mapped_column(Text, nullable=False)
    role_type: Mapped[str] = mapped_column(String(64), nullable=False)
    seniority_level: Mapped[str | None] = mapped_column(String(32))
    difficulty: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="in_progress")
    analysis_json: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    ai_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    ai_model: Mapped[str] = mapped_column(String(64), nullable=False)
    # True when content came from the demo heuristic provider or demo seed data.
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    questions: Mapped[list["Question"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Question.order_index",
    )
    answers: Mapped[list["Answer"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", passive_deletes=True
    )


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        UniqueConstraint("session_id", "order_index", name="questions_session_order_key"),
        CheckConstraint(f"category IN {QUESTION_CATEGORIES}", name="questions_category_check"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    difficulty: Mapped[str | None] = mapped_column(String(16))
    why_this_question: Mapped[str] = mapped_column(Text, nullable=False)
    source_context: Mapped[list[str]] = mapped_column(JSONType, nullable=False)
    evaluation_focus: Mapped[list[str]] = mapped_column(JSONType, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    session: Mapped[InterviewSession] = relationship(back_populates="questions")


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (
        # One submitted answer per question: the core idempotency guarantee.
        UniqueConstraint("question_id", name="answers_question_id_key"),
        CheckConstraint(f"evaluation_status IN {EVALUATION_STATUSES}", name="answers_eval_status_check"),
        CheckConstraint("score_clarity BETWEEN 1 AND 5", name="answers_score_clarity_check"),
        CheckConstraint("score_specificity BETWEEN 1 AND 5", name="answers_score_specificity_check"),
        CheckConstraint("score_result_orientation BETWEEN 1 AND 5", name="answers_score_result_check"),
        CheckConstraint("score_relevance BETWEEN 1 AND 5", name="answers_score_relevance_check"),
        Index("ix_answers_user_answered", "user_id", "answered_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    evaluation_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    evaluation_error: Mapped[str | None] = mapped_column(Text)
    evaluation_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score_clarity: Mapped[int | None] = mapped_column(Integer)
    score_specificity: Mapped[int | None] = mapped_column(Integer)
    score_result_orientation: Mapped[int | None] = mapped_column(Integer)
    score_relevance: Mapped[int | None] = mapped_column(Integer)
    # Average of the four scores on a 1-5 scale; percentage is derived (avg / 5 * 100).
    overall_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    feedback_json: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    ideal_answer: Mapped[str | None] = mapped_column(Text)
    rewrite_json: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    answered_at: Mapped[datetime | None] = mapped_column(UTCDateTime, default=utcnow)
    evaluated_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)

    session: Mapped[InterviewSession] = relationship(back_populates="answers")


class AIUsageEvent(Base):
    """One row per AI operation, for cost/latency/failure tracking. Contains no user text."""

    __tablename__ = "ai_usage_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    estimated_cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 6))
    error_type: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class JobSearch(Base):
    """One job-finder search. Stores preferences, the provider queries that were run and a
    skills-only profile (no resume text, no personal details)."""

    __tablename__ = "job_searches"
    __table_args__ = (
        CheckConstraint(
            "status IN ('discovered', 'matched', 'match_failed')", name="job_searches_status_check"
        ),
        Index("ix_job_searches_user_created", "user_id", "created_at"),
        Index("ix_job_searches_user_cache", "user_id", "cache_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    cache_key: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    country: Mapped[str | None] = mapped_column(String(8))
    params: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    queries: Mapped[list[str]] = mapped_column(JSONType, nullable=False)
    profile: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="discovered")
    match_error: Mapped[str | None] = mapped_column(Text)
    total_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)

    results: Mapped[list["JobResult"]] = relationship(
        back_populates="search", cascade="all, delete-orphan", passive_deletes=True, order_by="JobResult.rank"
    )


class JobResult(Base):
    """A listing returned by the job-search provider (source data) plus optional match analysis."""

    __tablename__ = "job_results"
    __table_args__ = (
        UniqueConstraint("search_id", "provider_job_id", name="job_results_search_provider_key"),
        CheckConstraint(
            "description_source IN ('listing_summary', 'user_provided')", name="job_results_desc_source_check"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    search_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("job_searches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_job_id: Mapped[str] = mapped_column(String(300), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    company: Mapped[str | None] = mapped_column(String(200))
    location: Mapped[str | None] = mapped_column(String(200))
    work_mode: Mapped[str | None] = mapped_column(String(16))
    employment_type: Mapped[str | None] = mapped_column(String(64))
    experience_level: Mapped[str | None] = mapped_column(String(16))
    salary_min: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    salary_max: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    salary_currency: Mapped[str | None] = mapped_column(String(3))
    category: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    description_source: Mapped[str] = mapped_column(String(20), nullable=False, default="listing_summary")
    url: Mapped[str] = mapped_column(Text, nullable=False)
    posted_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    retrieved_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    match: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    interview_session_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("sessions.id", ondelete="SET NULL")
    )

    search: Mapped[JobSearch] = relationship(back_populates="results")
