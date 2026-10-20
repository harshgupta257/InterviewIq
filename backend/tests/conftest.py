"""Shared fixtures. All AI calls are mocked; no credentials or network are required."""

import asyncio
import json
import os
import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient

from app.ai.provider import AIProvider, AIRequest, AIResult, AIUsage
from app.core.config import Settings
from app.main import create_app

JWT_SECRET = "test-supabase-jwt-secret-with-enough-length-123456"

RESUME = (
    "Jordan Lee - Backend engineer, jordan@example.com, +1 555 123 4567\n"
    "- Built a FastAPI service for document processing.\n"
    "- Used Databricks and PySpark for ETL pipelines.\n"
    "- Designed PostgreSQL schemas and Redis caching. 4 years of experience with Python.\n"
)
JD = (
    "Backend Engineer. Responsibilities: design reliable production APIs; build scalable data "
    "pipelines. Requirements: Python, SQL, Docker, AWS. Kafka is a plus."
)


def question_set(categories: list[str] | None = None) -> dict[str, Any]:
    cats = categories or [
        "technical",
        "technical",
        "project_deepdive",
        "project_deepdive",
        "behavioral",
        "behavioral",
        "system_design",
        "motivation",
    ]
    return {
        "questions": [
            {
                "question_text": f"Question {i + 1}: your resume mentions FastAPI; explain how you handled {c}.",
                "category": c,
                "why_this_question": "It probes a requirement from the job description.",
                "difficulty": "medium",
                "source_context": ["Resume: FastAPI service", "JD: reliable production APIs"],
                "evaluation_focus": ["Technical depth", "Trade-offs"],
            }
            for i, c in enumerate(cats)
        ]
    }


ANALYSIS = {
    "candidate_summary": "Backend engineer with Python, FastAPI and PySpark experience.",
    "candidate_skills": ["Python", "FastAPI", "PySpark"],
    "candidate_tools": ["Databricks", "Redis"],
    "candidate_projects": [{"name": "Document processing service", "summary": "FastAPI service."}],
    "years_experience_estimate": 4,
    "job_responsibilities": ["Design reliable production APIs"],
    "required_skills": ["Python", "SQL"],
    "preferred_qualifications": ["Kafka"],
    "matched_skills": ["Python"],
    "skill_gaps": ["Kafka"],
    "inferred_seniority": "mid",
    "inferred_role_type": "Backend Software Engineering",
}

EVALUATION = {
    "clarity": 4,
    "clarity_reason": "You opened with the context and followed a clear order.",
    "specificity": 3,
    "specificity_reason": "You named Pydantic but gave no example of a failure case.",
    "result_orientation": 4,
    "result_orientation_reason": "You explained the latency improvement.",
    "relevance": 5,
    "relevance_reason": "You directly addressed validation, failures and reliability.",
    "overall_feedback": "A focused answer that covers the main reliability concerns.",
    "one_thing_to_fix": "Describe one concrete failure you handled and how you detected it.",
}

REWRITE = {
    "improved_answer": "In the FastAPI document service I validated inputs with Pydantic models...",
    "improvements": ["Clearer structure", "Explicit trade-offs"],
    "missing_information": ["The error rate before and after"],
    "suggested_follow_up": "How did you monitor failures in production?",
}

PROFILE = {
    "summary": "Backend engineer with Python, FastAPI and PySpark experience.",
    "skills": ["Python", "SQL", "FastAPI", "PySpark"],
    "tools": ["Databricks", "Redis", "PostgreSQL"],
    "job_titles": ["Backend Engineer"],
    "education": ["BSc Computer Science"],
    "certifications": [],
    "projects": ["Document processing service"],
    "experience_level": "mid",
    "years_experience": 4,
    "suggested_roles": ["Backend Engineer", "Data Engineer"],
}


def job_matches(request: Any) -> dict[str, Any]:
    """Default job_matching output: one entry per job_ref in the request payload."""
    return {
        "matches": [
            {
                "job_ref": j["job_ref"],
                "required_skills": ["Python", "Kafka"],
                "experience_fit": 4,
                "role_alignment": 4,
                "responsibilities_fit": 3,
                "relevant_experience": ["FastAPI document service"],
                "reasons": ["Python and API experience match the listing."],
                "improvements": ["Add a measurable result for the FastAPI service."],
                "gaps": ["Kafka is not shown on the resume."],
                "description_sufficient": len(j["listing_text"]) > 200,
            }
            for j in request.payload["jobs"]
        ]
    }


DEFAULT_RESPONSES: dict[str, Any] = {
    "resume_profile": PROFILE,
    "job_matching": job_matches,
    "resume_job_analysis": ANALYSIS,
    "question_generation": question_set(),
    "answer_evaluation": EVALUATION,
    "answer_rewriting": REWRITE,
}


class FakeProvider(AIProvider):
    """Scriptable provider. `script[operation]` is a list consumed per call; each item is a
    dict (returned as JSON), a str (returned raw) or an Exception (raised)."""

    name = "fake"
    model = "fake-model"

    def __init__(self) -> None:
        self.script: dict[str, list[Any]] = {}
        self.calls: list[AIRequest] = []

    def queue(self, operation: str, *items: Any) -> None:
        self.script.setdefault(operation, []).extend(items)

    def count(self, operation: str) -> int:
        return sum(1 for c in self.calls if c.operation == operation)

    async def complete(self, request: AIRequest) -> AIResult:
        self.calls.append(request)
        queued = self.script.get(request.operation)
        item = queued.pop(0) if queued else DEFAULT_RESPONSES[request.operation]
        if callable(item) and not isinstance(item, Exception):
            item = item(request)
        if isinstance(item, Exception):
            raise item
        text = item if isinstance(item, str) else json.dumps(item)
        return AIResult(text=text, usage=AIUsage(100, 50))


def make_token(user_id: uuid.UUID, *, expired: bool = False, secret: str = JWT_SECRET) -> str:
    now = datetime.now(UTC)
    exp = now - timedelta(minutes=5) if expired else now + timedelta(hours=1)
    return jwt.encode(
        {
            "sub": str(user_id),
            "aud": "authenticated",
            "role": "authenticated",
            "email": f"{user_id.hex[:6]}@example.com",
            "exp": exp,
            "iat": now,
        },
        secret,
        algorithm="HS256",
    )


@pytest.fixture
def provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
def settings_factory(tmp_path: Path) -> Callable[..., Settings]:
    def _make(**overrides: Any) -> Settings:
        values: dict[str, Any] = {
            "app_env": "test",
            "database_url": f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}",
            "supabase_jwt_secret": JWT_SECRET,
            "ai_provider": "demo",
            "ai_max_retries": 2,
            "ai_retry_backoff_seconds": 0,
            "rate_limit_per_minute": 1000,
            "demo_mode": False,
            "log_level": "WARNING",
        }
        # Optional: run the suite against Postgres, e.g.
        # TEST_DATABASE_URL=postgresql+asyncpg://postgres@127.0.0.1:5432/iq_test
        if os.environ.get("TEST_DATABASE_URL") and not overrides.get("demo_mode"):
            values["database_url"] = os.environ["TEST_DATABASE_URL"]
        values.update(overrides)
        return Settings(_env_file=None, **values)  # type: ignore[call-arg]

    return _make


def _reset_postgres(url: str) -> None:
    from app.db.database import build_engine
    from app.models import Base

    async def _go() -> None:
        engine = build_engine(Settings(_env_file=None, database_url=url))  # type: ignore[call-arg]
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    asyncio.run(_go())


@pytest.fixture
def make_client(
    settings_factory: Callable[..., Settings], provider: FakeProvider
) -> Iterator[Callable[..., TestClient]]:
    clients: list[TestClient] = []
    if os.environ.get("TEST_DATABASE_URL"):
        _reset_postgres(os.environ["TEST_DATABASE_URL"])

    def _make(**overrides: Any) -> TestClient:
        raise_errors = overrides.pop("raise_server_exceptions", True)
        job_provider = overrides.pop("job_provider", None)
        app = create_app(settings_factory(**overrides), provider=provider, job_provider=job_provider)
        client = TestClient(app, raise_server_exceptions=raise_errors)
        client.__enter__()
        clients.append(client)
        return client

    yield _make
    for c in clients:
        c.__exit__(None, None, None)


@pytest.fixture
def client(make_client: Callable[..., TestClient]) -> TestClient:
    return make_client()


@pytest.fixture
def user_a() -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(uuid.uuid4())}"}


@pytest.fixture
def user_b() -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(uuid.uuid4())}"}


def session_payload(**overrides: Any) -> dict[str, Any]:
    body = {
        "resume_text": RESUME * 2,
        "jd_text": JD,
        "job_title": "Backend Engineer",
        "company": "Contoso",
        "role_type": "software_engineering",
    }
    body.update(overrides)
    return body


def create_session(client: TestClient, headers: dict[str, str], **overrides: Any) -> dict[str, Any]:
    r = client.post("/api/v1/sessions", json=session_payload(**overrides), headers=headers)
    assert r.status_code == 201, r.text
    data: dict[str, Any] = r.json()
    return data


def answer_text(i: int = 0) -> str:
    return f"In my FastAPI service I validated inputs with Pydantic and added retries. Variant {i}."
