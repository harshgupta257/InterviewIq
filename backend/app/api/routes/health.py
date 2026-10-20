from fastapi import APIRouter, Request
from sqlalchemy import text

from app.api.dependencies import SettingsDep
from app.schemas import (
    MAX_ANSWER_CHARS,
    MAX_JD_CHARS,
    MAX_RESUME_CHARS,
    MIN_ANSWER_CHARS,
    MIN_JD_CHARS,
    MIN_RESUME_CHARS,
    JobSearchConfig,
    PublicConfig,
)
from app.services.demo_data import SAMPLE_JD, SAMPLE_RESUME

router = APIRouter(tags=["health"])


@router.get("/", include_in_schema=False)
async def root(settings: SettingsDep) -> dict[str, str]:
    """The API has no web pages; point visitors at the web app and the API docs."""
    return {
        "service": "InterviewIQ API",
        "message": "This is the backend API. Open the web app instead.",
        "web_app": settings.allowed_origins[0] if settings.allowed_origins else "",
        "api_docs": "/docs",
        "health": "/health",
    }


@router.get("/health")
async def health(request: Request, settings: SettingsDep) -> dict[str, object]:
    """Liveness + database readiness. The AI provider is reported but deliberately does not
    make the service unhealthy: a vendor outage should not take the app (history, review)
    down with it."""
    db_ok = True
    try:
        async with request.app.state.session_factory() as db:
            await db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "unavailable",
        "ai_provider": settings.ai_provider,
        "environment": settings.app_env,
        "version": request.app.version,
    }


@router.get("/api/v1/config", response_model=PublicConfig)
async def public_config(settings: SettingsDep) -> PublicConfig:
    """Non-secret configuration the frontend needs (feature flags and limits)."""
    return PublicConfig(
        app_env=settings.app_env,
        demo_mode=settings.demo_mode,
        ai_provider=settings.ai_provider,
        ai_model=settings.resolved_ai_model,
        ai_is_demo=settings.ai_provider == "demo",
        supabase_auth=settings.supabase_auth_enabled,
        limits={
            "resume_min": MIN_RESUME_CHARS,
            "resume_max": MAX_RESUME_CHARS,
            "jd_min": MIN_JD_CHARS,
            "jd_max": MAX_JD_CHARS,
            "answer_min": MIN_ANSWER_CHARS,
            "answer_max": MAX_ANSWER_CHARS,
        },
        job_search=JobSearchConfig(
            enabled=settings.job_search_enabled,
            provider="adzuna" if settings.job_search_enabled else "none",
            country=settings.adzuna_country if settings.job_search_enabled else None,
            upload_max_mb=settings.resume_upload_max_mb,
        ),
    )


@router.get("/api/v1/samples")
async def samples() -> dict[str, str]:
    """Fictional sample resume and job description for trying the product."""
    return {
        "resume_text": SAMPLE_RESUME,
        "jd_text": SAMPLE_JD,
        "job_title": "Backend Engineer",
        "company": "Contoso Freight",
        "role_type": "software_engineering",
    }
