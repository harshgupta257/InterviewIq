"""Verify the backend configuration against the real services. Never prints secret values.

Usage (from backend/):  python -m scripts.check_setup
Checks: config consistency, database + schema, Supabase JWT keys, AI provider round-trip.
"""

import asyncio
import sys

import asyncpg
import httpx

from app.ai.prompts import answer_evaluation
from app.ai.provider import build_provider
from app.ai.schemas import AnswerEvaluation
from app.ai.structured import run_structured
from app.core.config import get_settings

OK, WARN, FAIL = "  OK  ", " WARN ", " FAIL "
REQUIRED_TABLES = {
    "profiles",
    "sessions",
    "questions",
    "answers",
    "ai_usage_events",
    "job_searches",
    "job_results",
}


def line(status: str, msg: str) -> None:
    print(f"[{status}] {msg}")


async def main() -> int:
    s = get_settings()
    failures = 0

    problems = s.validate_for_startup()
    for p in problems:
        line(FAIL, p)
    failures += len(problems)
    if not problems:
        line(OK, f"Config valid (env={s.app_env}, ai={s.ai_provider}, demo_mode={s.demo_mode})")

    # Database
    if s.is_sqlite:
        line(WARN, "DATABASE_URL is SQLite (local/demo). Set your Supabase URL to use Postgres.")
    else:
        try:
            conn = await asyncpg.connect(
                s.database_url.replace("postgresql+asyncpg://", "postgresql://", 1),
                statement_cache_size=0,
                timeout=15,
            )
            rows = await conn.fetch(
                "select tablename, rowsecurity from pg_tables where schemaname = 'public'"
            )
            await conn.close()
            tables = {r["tablename"]: r["rowsecurity"] for r in rows}
            missing = REQUIRED_TABLES - tables.keys()
            if missing:
                line(FAIL, f"Tables missing: {sorted(missing)}. Run: python -m scripts.apply_migrations")
                failures += 1
            elif not all(tables[t] for t in REQUIRED_TABLES):
                line(FAIL, "Tables exist but Row Level Security is not enabled on all of them.")
                failures += 1
            else:
                line(OK, "Database reachable; all tables present with RLS enabled")
        except Exception as exc:  # noqa: BLE001
            line(FAIL, f"Cannot connect to database: {type(exc).__name__}: {str(exc)[:160]}")
            failures += 1

    # Supabase auth keys
    if s.supabase_url:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(s.supabase_url.rstrip("/") + "/auth/v1/.well-known/jwks.json")
            keys = r.json().get("keys", []) if r.status_code == 200 else []
            if keys:
                line(OK, f"Supabase signing keys found ({len(keys)}); JWTs will be verified via JWKS")
            elif s.supabase_jwt_secret:
                line(OK, "No JWKS keys (legacy project); SUPABASE_JWT_SECRET is set for HS256 tokens")
            else:
                line(
                    FAIL,
                    "Project has no JWT signing keys and SUPABASE_JWT_SECRET is empty. Copy the "
                    "legacy JWT secret from Supabase > Project Settings > JWT Keys into .env.",
                )
                failures += 1
        except Exception as exc:  # noqa: BLE001
            line(FAIL, f"Cannot reach SUPABASE_URL: {type(exc).__name__}")
            failures += 1
    else:
        line(WARN, "SUPABASE_URL not set (only demo login will work).")
    if not s.supabase_service_role_key:
        line(WARN, "SUPABASE_SERVICE_ROLE_KEY not set: account deletion can't remove the login itself.")

    # AI provider
    provider = build_provider(s)
    if provider.is_demo:
        line(WARN, "AI_PROVIDER=demo (offline heuristic, not real AI).")
    else:
        try:
            out = await run_structured(
                provider,
                operation="answer_evaluation",
                system_prompt=answer_evaluation.SYSTEM_PROMPT,
                payload=answer_evaluation.build_payload(
                    question_text="How did you make your API reliable?",
                    category="technical",
                    evaluation_focus=["Reliability"],
                    job_title="Backend Engineer",
                    role_type="software_engineering",
                    seniority="mid",
                    resume_excerpt="Built a FastAPI service.",
                    jd_excerpt="Design reliable APIs.",
                    answer_text="I added validation, retries with backoff and alerting; errors dropped.",
                ),
                model_cls=AnswerEvaluation,
                max_retries=1,
            )
            line(
                OK,
                f"{provider.name} ({out.model}) returned a valid evaluation "
                f"in {out.duration_ms} ms, {out.attempts} attempt(s)",
            )
        except Exception as exc:  # noqa: BLE001
            line(FAIL, f"{provider.name} call failed: {exc}")
            failures += 1
        finally:
            await provider.aclose()

    print("\nAll checks passed." if failures == 0 else f"\n{failures} problem(s) to fix.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
