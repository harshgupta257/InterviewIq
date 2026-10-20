"""Public API request/response schemas (distinct from AI output schemas)."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

RoleType = Literal[
    "software_engineering",
    "data_engineering",
    "data_science",
    "data_analytics",
    "ai_ml_engineering",
    "forward_deployed_engineering",
    "other",
]
SeniorityLevel = Literal["intern", "junior", "mid", "senior", "staff", "lead"]
DifficultyPref = Literal["easy", "medium", "hard", "mixed"]
SessionSort = Literal["date_desc", "date_asc", "score_desc", "score_asc"]

ROLE_LABELS: dict[str, str] = {
    "software_engineering": "Software Engineering",
    "data_engineering": "Data Engineering",
    "data_science": "Data Science",
    "data_analytics": "Data Analytics",
    "ai_ml_engineering": "AI/ML Engineering",
    "forward_deployed_engineering": "Forward Deployed Engineering",
    "other": "Other",
}

MAX_RESUME_CHARS = 15000
MAX_JD_CHARS = 12000
MAX_ANSWER_CHARS = 6000
MIN_RESUME_CHARS = 150
MIN_JD_CHARS = 100
MIN_ANSWER_CHARS = 20


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ------------------------------------------------------------------ requests
class SessionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    resume_text: str = Field(min_length=MIN_RESUME_CHARS, max_length=MAX_RESUME_CHARS)
    jd_text: str = Field(min_length=MIN_JD_CHARS, max_length=MAX_JD_CHARS)
    job_title: str = Field(min_length=2, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    role_type: RoleType
    seniority_level: SeniorityLevel | None = None
    difficulty: DifficultyPref | None = None
    # Fixed at eight for the MVP; accepted for forward compatibility.
    question_count: Literal[8] = 8

    @field_validator("company")
    @classmethod
    def _blank_company_to_none(cls, v: str | None) -> str | None:
        return v or None


class AnswerSubmit(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    question_id: uuid.UUID
    answer_text: str = Field(min_length=MIN_ANSWER_CHARS, max_length=MAX_ANSWER_CHARS)


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    display_name: str | None = Field(default=None, max_length=120)


# ------------------------------------------------------------------ responses
class QuestionOut(APIModel):
    id: uuid.UUID
    order_index: int
    question_text: str
    category: str
    difficulty: str | None
    why_this_question: str
    source_context: list[str]
    evaluation_focus: list[str]


class DimensionScore(BaseModel):
    score: int
    reason: str


class EvaluationOut(BaseModel):
    clarity: DimensionScore
    specificity: DimensionScore
    result_orientation: DimensionScore
    relevance: DimensionScore
    overall_feedback: str
    one_thing_to_fix: str
    average: float = Field(description="Mean of the four 1-5 scores.")
    percentage: float = Field(description="average / 5 * 100, computed by the backend.")
    is_demo: bool
    model: str | None = None


class RewriteOut(BaseModel):
    improved_answer: str
    improvements: list[str]
    missing_information: list[str]
    suggested_follow_up: str
    generated_at: datetime | None
    is_demo: bool


class AnswerOut(BaseModel):
    id: uuid.UUID
    question_id: uuid.UUID
    session_id: uuid.UUID
    answer_text: str
    evaluation_status: Literal["pending", "evaluating", "completed", "failed"]
    evaluation_error: str | None
    evaluation: EvaluationOut | None
    rewrite: RewriteOut | None
    answered_at: datetime | None
    evaluated_at: datetime | None


class SessionProgress(BaseModel):
    total_questions: int
    answered_count: int
    evaluated_count: int
    failed_evaluations: int
    current_question_index: int = Field(
        description="0-based index of the next unanswered question; equals total when all are answered."
    )
    is_complete: bool


class SessionSummary(BaseModel):
    id: uuid.UUID
    job_title: str
    company: str | None
    role_type: str
    role_label: str
    seniority_level: str | None
    status: str
    is_demo: bool
    created_at: datetime
    completed_at: datetime | None
    total_questions: int
    answered_count: int
    evaluated_count: int
    average_score: float | None = Field(description="Mean evaluated answer percentage (0-100).")
    completion_pct: float


class SessionDetail(SessionSummary):
    jd_text: str
    resume_text: str
    difficulty: str | None
    analysis: dict[str, Any] | None
    ai_provider: str
    ai_model: str
    questions: list[QuestionOut]
    answers: list[AnswerOut]
    progress: SessionProgress


class SessionList(BaseModel):
    items: list[SessionSummary]
    total: int
    page: int
    page_size: int


class DimensionAverages(BaseModel):
    clarity: float | None
    specificity: float | None
    result_orientation: float | None
    relevance: float | None


class AnalyticsOverview(BaseModel):
    total_sessions: int
    completed_interviews: int
    total_questions_answered: int
    evaluated_answers: int
    average_score: float | None
    most_recent_session_score: float | None
    most_recent_session_id: uuid.UUID | None
    dimension_averages: DimensionAverages
    includes_demo_data: bool


class ProgressPoint(BaseModel):
    session_id: uuid.UUID
    job_title: str
    company: str | None
    date: datetime
    average_score: float
    evaluated_count: int
    is_demo: bool


class AnalyticsProgress(BaseModel):
    points: list[ProgressPoint]


class ProfileOut(BaseModel):
    id: uuid.UUID
    email: str | None
    display_name: str | None
    is_demo: bool


class JobSearchConfig(BaseModel):
    enabled: bool
    provider: str
    country: str | None
    upload_max_mb: float


class PublicConfig(BaseModel):
    app_env: str
    demo_mode: bool
    ai_provider: str
    ai_model: str
    ai_is_demo: bool
    supabase_auth: bool
    limits: dict[str, int]
    job_search: JobSearchConfig


class DemoSessionOut(BaseModel):
    access_token: str
    expires_at: datetime
    user_id: uuid.UUID
