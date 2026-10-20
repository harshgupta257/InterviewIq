"""Application configuration loaded from environment variables.

All secrets live here and never leave the backend. `validate_for_startup` fails fast
when the configuration is inconsistent (e.g. a real AI provider without an API key).
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AIProviderName = Literal["gemini", "openai", "demo"]

DEFAULT_MODELS: dict[str, str] = {
    "gemini": "gemini-flash-latest",
    "openai": "gpt-4o-mini",
    "demo": "demo-heuristic-v1",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    # Comma-separated allowlist of browser origins.
    frontend_origin: str = "http://localhost:5173"

    # Database. SQLite is used for local development, demo mode and tests;
    # production uses Supabase Postgres (postgresql+asyncpg://...).
    database_url: str = "sqlite+aiosqlite:///./interviewiq.db"
    # Create tables from SQLAlchemy metadata on startup. Only for SQLite/dev.
    # Production schema is managed by the SQL migrations in /supabase/migrations.
    db_auto_create: bool = True

    supabase_url: str = ""
    supabase_service_role_key: str = ""
    # Legacy HS256 JWT secret. Prefer asymmetric signing keys (verified via JWKS).
    supabase_jwt_secret: str = ""
    supabase_jwt_audience: str = "authenticated"

    # Demo mode: enables the passwordless demo login with isolated per-visitor accounts.
    demo_mode: bool = False
    demo_jwt_secret: str = "change-me-local-demo-secret-0123456789"
    # New demo accounts allowed per client IP per hour.
    demo_sessions_per_hour: int = Field(default=10, ge=1)

    ai_provider: AIProviderName = "demo"
    ai_model: str = ""
    # Comma-separated models tried in order when the primary model is overloaded (503/429/timeout).
    ai_fallback_models: str = ""
    gemini_api_key: str = ""
    openai_api_key: str = ""
    ai_timeout_seconds: float = 60.0
    ai_max_retries: int = Field(default=2, ge=0, le=5)
    ai_retry_backoff_seconds: float = Field(default=1.0, ge=0)

    rate_limit_per_minute: int = Field(default=10, ge=1)
    log_level: str = "INFO"

    # --- Job finder -------------------------------------------------------------
    # Discovery uses a licensed job-search API (Adzuna). Gemini's Google Search grounding
    # is deliberately NOT used: its terms forbid analysing, caching or altering grounded
    # results, which a job finder must do.
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    adzuna_country: str = Field(default="in", pattern=r"^[a-z]{2}$")
    job_search_cache_minutes: int = Field(default=360, ge=0)
    job_search_max_queries: int = Field(default=2, ge=1, le=5)
    job_search_results_per_query: int = Field(default=10, ge=1, le=50)
    job_search_max_matched: int = Field(default=12, ge=1, le=25)
    job_searches_per_hour: int = Field(default=10, ge=1)
    resume_upload_max_mb: float = Field(default=5, gt=0, le=20)

    @property
    def job_search_enabled(self) -> bool:
        return bool(self.adzuna_app_id and self.adzuna_app_key)

    @field_validator("database_url")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        # Accept the plain URL Supabase shows in its dashboard.
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://") :]
        if v.startswith("postgresql://"):
            v = "postgresql+asyncpg://" + v[len("postgresql://") :]
        return v

    @field_validator("supabase_url")
    @classmethod
    def _normalize_supabase_url(cls, v: str) -> str:
        # Accept common copy-paste variants such as ".../rest/v1/" or ".../auth/v1".
        v = v.strip().rstrip("/")
        for suffix in ("/rest/v1", "/auth/v1"):
            if v.endswith(suffix):
                v = v[: -len(suffix)]
        return v

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.frontend_origin.split(",") if o.strip()]

    @property
    def resolved_ai_model(self) -> str:
        return self.ai_model or DEFAULT_MODELS[self.ai_provider]

    @property
    def ai_models(self) -> list[str]:
        """Primary model followed by de-duplicated fallbacks."""
        models = [self.resolved_ai_model]
        for m in self.ai_fallback_models.split(","):
            m = m.strip()
            if m and m not in models:
                models.append(m)
        return models

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def supabase_auth_enabled(self) -> bool:
        return bool(self.supabase_url or self.supabase_jwt_secret)

    def validate_for_startup(self) -> list[str]:
        """Return a list of fatal configuration problems (empty when valid)."""
        problems: list[str] = []
        if self.ai_provider == "gemini" and not self.gemini_api_key:
            problems.append("AI_PROVIDER=gemini requires GEMINI_API_KEY.")
        if self.ai_provider == "openai" and not self.openai_api_key:
            problems.append("AI_PROVIDER=openai requires OPENAI_API_KEY.")
        if not self.supabase_auth_enabled and not self.demo_mode:
            problems.append(
                "No authentication configured. Set SUPABASE_URL (or SUPABASE_JWT_SECRET) "
                "or enable DEMO_MODE=true for local development."
            )
        if self.app_env == "production":
            if self.is_sqlite and not self.demo_mode:
                problems.append("Production requires DATABASE_URL pointing at Postgres.")
            if self.db_auto_create and not self.is_sqlite:
                problems.append("Set DB_AUTO_CREATE=false in production; use SQL migrations.")
            if self.demo_mode and self.demo_jwt_secret.startswith("change-me"):
                problems.append("DEMO_MODE in production requires a strong DEMO_JWT_SECRET.")
            if any("localhost" in o for o in self.allowed_origins):
                problems.append("FRONTEND_ORIGIN must not contain localhost in production.")
        if self.demo_mode and not self.is_sqlite:
            problems.append(
                "DEMO_MODE requires the SQLite database: demo visitors are not Supabase Auth "
                "users, so the auth.users foreign keys in Postgres would reject them."
            )
        if self.demo_mode and len(self.demo_jwt_secret) < 32:
            problems.append("DEMO_JWT_SECRET must be at least 32 characters.")
        return problems


@lru_cache
def get_settings() -> Settings:
    return Settings()
