"""Pydantic schemas for every structured AI output.

Model output is untrusted: it is parsed and validated against these models before
anything is persisted or shown to the user.
"""

from collections import Counter
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

QuestionCategory = Literal[
    "technical", "behavioral", "project_deepdive", "system_design", "motivation", "case_study"
]
Difficulty = Literal["easy", "medium", "hard"]
Seniority = Literal["intern", "junior", "mid", "senior", "staff", "lead"]

QUESTION_COUNT = 8
# Required distribution. Slot "design_or_case" accepts system_design OR case_study.
REQUIRED_DISTRIBUTION = {
    "technical": 2,
    "project_deepdive": 2,
    "behavioral": 2,
    "design_or_case": 1,
    "motivation": 1,
}

Score = Annotated[int, Field(ge=1, le=5)]
ShortText = Annotated[str, Field(min_length=1, max_length=400)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


# ---------------------------------------------------------------- analysis
class CandidateProject(_Strict):
    name: Annotated[str, Field(min_length=1, max_length=200)]
    summary: Annotated[str, Field(max_length=600)] = ""
    technologies: list[ShortText] = Field(default_factory=list, max_length=20)


class ResumeJobAnalysis(_Strict):
    candidate_summary: Annotated[str, Field(min_length=1, max_length=1200)]
    candidate_skills: list[ShortText] = Field(default_factory=list, max_length=40)
    candidate_tools: list[ShortText] = Field(default_factory=list, max_length=40)
    candidate_projects: list[CandidateProject] = Field(default_factory=list, max_length=12)
    years_experience_estimate: float | None = Field(default=None, ge=0, le=60)
    job_responsibilities: list[ShortText] = Field(default_factory=list, max_length=30)
    required_skills: list[ShortText] = Field(default_factory=list, max_length=40)
    preferred_qualifications: list[ShortText] = Field(default_factory=list, max_length=30)
    matched_skills: list[ShortText] = Field(default_factory=list, max_length=40)
    skill_gaps: list[ShortText] = Field(default_factory=list, max_length=30)
    inferred_seniority: Seniority
    inferred_role_type: Annotated[str, Field(min_length=1, max_length=80)]


# ---------------------------------------------------------------- questions
class GeneratedQuestion(_Strict):
    question_text: Annotated[str, Field(min_length=20, max_length=1200)]
    category: QuestionCategory
    why_this_question: Annotated[str, Field(min_length=10, max_length=800)]
    difficulty: Difficulty
    source_context: list[ShortText] = Field(min_length=1, max_length=6)
    evaluation_focus: list[ShortText] = Field(min_length=1, max_length=6)

    @field_validator("source_context", "evaluation_focus", mode="before")
    @classmethod
    def _coerce_str_to_list(cls, v: object) -> object:
        # Models occasionally return a single string; accept it as a one-item list.
        return [v] if isinstance(v, str) else v


class QuestionSet(_Strict):
    questions: list[GeneratedQuestion]

    @model_validator(mode="after")
    def _check_count_and_distribution(self) -> "QuestionSet":
        if len(self.questions) != QUESTION_COUNT:
            raise ValueError(f"Expected exactly {QUESTION_COUNT} questions, received {len(self.questions)}.")
        counts = Counter(q.category for q in self.questions)
        actual = {
            "technical": counts["technical"],
            "project_deepdive": counts["project_deepdive"],
            "behavioral": counts["behavioral"],
            "design_or_case": counts["system_design"] + counts["case_study"],
            "motivation": counts["motivation"],
        }
        if actual != REQUIRED_DISTRIBUTION:
            raise ValueError(
                f"Category distribution must be {REQUIRED_DISTRIBUTION} "
                f"(design_or_case = system_design or case_study); received {actual}."
            )
        texts = [q.question_text.casefold() for q in self.questions]
        if len(set(texts)) != len(texts):
            raise ValueError("Questions must be unique.")
        return self


# ---------------------------------------------------------------- evaluation
class AnswerEvaluation(_Strict):
    clarity: Score
    clarity_reason: Annotated[str, Field(min_length=10, max_length=1000)]
    specificity: Score
    specificity_reason: Annotated[str, Field(min_length=10, max_length=1000)]
    result_orientation: Score
    result_orientation_reason: Annotated[str, Field(min_length=10, max_length=1000)]
    relevance: Score
    relevance_reason: Annotated[str, Field(min_length=10, max_length=1000)]
    overall_feedback: Annotated[str, Field(min_length=10, max_length=2000)]
    one_thing_to_fix: Annotated[str, Field(min_length=5, max_length=800)]


# ---------------------------------------------------------------- rewrite
class AnswerRewrite(_Strict):
    improved_answer: Annotated[str, Field(min_length=20, max_length=6000)]
    improvements: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(
        min_length=1, max_length=8
    )
    missing_information: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(
        default_factory=list, max_length=8
    )
    suggested_follow_up: Annotated[str, Field(max_length=800)] = ""


# ---------------------------------------------------------------- job finder
class ResumeProfile(_Strict):
    summary: Annotated[str, Field(min_length=1, max_length=800)]
    skills: list[ShortText] = Field(default_factory=list, max_length=50)
    tools: list[ShortText] = Field(default_factory=list, max_length=40)
    job_titles: list[ShortText] = Field(default_factory=list, max_length=15)
    education: list[ShortText] = Field(default_factory=list, max_length=10)
    certifications: list[ShortText] = Field(default_factory=list, max_length=15)
    projects: list[ShortText] = Field(default_factory=list, max_length=12)
    experience_level: Literal["intern", "junior", "mid", "senior", "staff", "lead", "unknown"]
    years_experience: float | None = Field(default=None, ge=0, le=60)
    suggested_roles: list[Annotated[str, Field(min_length=2, max_length=80)]] = Field(
        min_length=1, max_length=5
    )


Fit = Annotated[int, Field(ge=1, le=5)]


class JobMatchItem(_Strict):
    job_ref: Annotated[str, Field(min_length=1, max_length=10)]
    required_skills: list[ShortText] = Field(default_factory=list, max_length=25)
    experience_fit: Fit
    role_alignment: Fit
    responsibilities_fit: Fit
    relevant_experience: list[ShortText] = Field(default_factory=list, max_length=5)
    reasons: list[Annotated[str, Field(min_length=5, max_length=400)]] = Field(min_length=1, max_length=4)
    improvements: list[Annotated[str, Field(min_length=5, max_length=400)]] = Field(
        default_factory=list, max_length=3
    )
    gaps: list[Annotated[str, Field(min_length=3, max_length=400)]] = Field(
        default_factory=list, max_length=4
    )
    description_sufficient: bool


class JobMatchBatch(_Strict):
    matches: list[JobMatchItem]

    @model_validator(mode="after")
    def _unique_refs(self) -> "JobMatchBatch":
        refs = [m.job_ref for m in self.matches]
        if len(set(refs)) != len(refs):
            raise ValueError("Each job_ref must appear exactly once.")
        return self
