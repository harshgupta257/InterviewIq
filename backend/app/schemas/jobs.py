"""API schemas for the AI Job Finder."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas import (
    MAX_JD_CHARS,
    MAX_RESUME_CHARS,
    MIN_JD_CHARS,
    MIN_RESUME_CHARS,
    RoleType,
    SessionDetail,
)

WorkMode = Literal["remote", "hybrid", "onsite"]
EmploymentFilter = Literal["full_time", "part_time", "contract", "permanent"]
Level = Literal["intern", "junior", "mid", "senior", "staff", "lead", "unknown"]
ShortItem = Annotated[str, Field(min_length=1, max_length=400)]


class _In(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class ResumeExtractOut(BaseModel):
    text: str
    file_type: Literal["pdf", "docx"]
    pages: int | None
    char_count: int
    truncated: bool
    warnings: list[str]


class JobProfile(BaseModel):
    """Skills-only professional profile. Contains no contact or personal details."""

    model_config = ConfigDict(extra="ignore")

    summary: Annotated[str, Field(max_length=800)] = ""
    skills: list[ShortItem] = Field(default_factory=list, max_length=50)
    tools: list[ShortItem] = Field(default_factory=list, max_length=40)
    job_titles: list[ShortItem] = Field(default_factory=list, max_length=15)
    education: list[ShortItem] = Field(default_factory=list, max_length=10)
    certifications: list[ShortItem] = Field(default_factory=list, max_length=15)
    projects: list[ShortItem] = Field(default_factory=list, max_length=12)
    experience_level: Level = "unknown"
    years_experience: float | None = Field(default=None, ge=0, le=60)
    suggested_roles: list[Annotated[str, Field(min_length=2, max_length=80)]] = Field(
        default_factory=list, max_length=5
    )


class JobProfileRequest(_In):
    resume_text: str = Field(min_length=MIN_RESUME_CHARS, max_length=MAX_RESUME_CHARS)


class JobProfileOut(JobProfile):
    is_demo: bool = False


class JobSearchCreate(_In):
    profile: JobProfile
    target_roles: list[Annotated[str, Field(min_length=2, max_length=80)]] = Field(
        default_factory=list, max_length=3
    )
    location: str | None = Field(default=None, max_length=100)
    experience_level: Level | None = None
    work_modes: list[WorkMode] = Field(default_factory=list, max_length=3)
    employment_types: list[EmploymentFilter] = Field(default_factory=list, max_length=4)
    refresh: bool = False

    @field_validator("location")
    @classmethod
    def _blank_to_none(cls, v: str | None) -> str | None:
        return v or None


class JobMatchRequest(_In):
    resume_text: str = Field(min_length=MIN_RESUME_CHARS, max_length=MAX_RESUME_CHARS)


class JobRematchRequest(JobMatchRequest):
    description: str | None = Field(default=None, min_length=MIN_JD_CHARS, max_length=MAX_JD_CHARS)


class PrepareInterviewRequest(JobMatchRequest):
    role_type: RoleType
    description: str | None = Field(default=None, min_length=MIN_JD_CHARS, max_length=MAX_JD_CHARS)
    new_session: bool = False


class MatchComponents(BaseModel):
    skills: float | None
    experience: float
    role: float
    responsibilities: float


class JobMatchOut(BaseModel):
    score: int
    label: str
    confidence: Literal["provisional", "full"]
    required_skills: list[str]
    matched_skills: list[str]
    missing_skills: list[str]
    relevant_experience: list[str]
    reasons: list[str]
    improvements: list[str]
    gaps: list[str]
    description_sufficient: bool
    components: MatchComponents
    scoring_version: str
    model: str | None
    is_demo: bool
    matched_at: datetime | None


class Attribution(BaseModel):
    label: str
    url: str


class JobResultOut(BaseModel):
    id: uuid.UUID
    rank: int
    title: str
    company: str | None
    location: str | None
    work_mode: str | None
    employment_type: str | None
    experience_level: str | None
    salary_min: float | None
    salary_max: float | None
    salary_currency: str | None
    category: str | None
    description: str | None
    description_source: Literal["listing_summary", "user_provided"]
    url: str
    source: str
    posted_at: datetime | None
    retrieved_at: datetime
    match: JobMatchOut | None
    interview_session_id: uuid.UUID | None


class JobSearchParams(BaseModel):
    target_roles: list[str]
    location: str | None
    experience_level: str | None
    work_modes: list[str]
    employment_types: list[str]


class JobSearchOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    expires_at: datetime
    provider: str
    attribution: Attribution | None
    params: JobSearchParams
    queries: list[str]
    profile: JobProfile
    status: Literal["discovered", "matched", "match_failed"]
    match_error: str | None
    total_found: int
    rejected: int
    cached: bool = False
    warnings: list[str] = Field(default_factory=list)
    results: list[JobResultOut]


class JobSearchSummary(BaseModel):
    id: uuid.UUID
    created_at: datetime
    queries: list[str]
    params: JobSearchParams
    status: str
    result_count: int


class PrepareInterviewOut(BaseModel):
    job_id: uuid.UUID
    created: bool
    session: SessionDetail
