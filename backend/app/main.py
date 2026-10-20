"""FastAPI application factory."""

import asyncio
import re
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.ai.provider import AIProvider, build_provider
from app.api.routes import account, analytics, answers, health, jobs, sessions
from app.core.config import Settings, get_settings
from app.core.exceptions import _envelope, register_exception_handlers
from app.core.logging import configure_logging, get_logger, request_id_var
from app.core.rate_limit import RateLimiter
from app.db.database import build_engine, build_session_factory
from app.jobs.providers import JobSearchProvider, build_job_provider
from app.models import Base
from app.services.ai_gateway import AIGateway

log = get_logger(__name__)

VERSION = "1.0.0"
REQUEST_TIMEOUT_SECONDS = 240  # longer than the worst-case AI pipeline with retries
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")


def create_app(
    settings: Settings | None = None,
    provider: AIProvider | None = None,
    job_provider: JobSearchProvider | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    problems = settings.validate_for_startup()
    if problems:
        for p in problems:
            log.error("config_invalid", extra={"problem": p})
        raise RuntimeError("Invalid configuration:\n- " + "\n- ".join(problems))

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = build_engine(settings)
        if settings.db_auto_create:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        factory = build_session_factory(engine)
        ai = provider or build_provider(settings)
        app.state.settings = settings
        app.state.engine = engine
        app.state.session_factory = factory
        app.state.ai_gateway = AIGateway(
            ai, factory, settings.ai_max_retries, backoff_base=settings.ai_retry_backoff_seconds
        )
        app.state.rate_limiter = RateLimiter(settings.rate_limit_per_minute)
        app.state.job_provider = job_provider or build_job_provider(settings)
        app.state.job_search_limiter = RateLimiter(
            settings.job_searches_per_hour, window_seconds=3600, what="job searches"
        )
        app.state.demo_limiter = RateLimiter(
            settings.demo_sessions_per_hour, window_seconds=3600, what="demo accounts from this network"
        )
        if settings.demo_mode:
            log.warning("demo_mode_enabled", extra={"env": settings.app_env})
        log.info(
            "startup",
            extra={
                "env": settings.app_env,
                "ai_provider": ai.name,
                "ai_model": ai.model,
                "db": "sqlite" if settings.is_sqlite else "postgres",
                "job_search": app.state.job_provider.name,
            },
        )
        try:
            yield
        finally:
            await ai.aclose()
            await app.state.job_provider.aclose()
            await engine.dispose()

    app = FastAPI(
        title="InterviewIQ API",
        version=VERSION,
        description="AI interview preparation: tailored questions, rubric evaluation and coaching.",
        lifespan=lifespan,
    )
    register_exception_handlers(app)

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming = request.headers.get("x-request-id", "")
        rid = incoming if _REQUEST_ID_RE.match(incoming) else uuid.uuid4().hex
        token = request_id_var.set(rid)
        started = time.perf_counter()
        try:
            try:
                response = await asyncio.wait_for(call_next(request), REQUEST_TIMEOUT_SECONDS)
            except TimeoutError:
                log.error("request_timeout", extra={"path": request.url.path})
                response = _envelope(504, "timeout", "The request took too long. Please try again.")
            response.headers["X-Request-ID"] = rid
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["Cache-Control"] = "no-store"
            log.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": int((time.perf_counter() - started) * 1000),
                },
            )
            return response
        finally:
            request_id_var.reset(token)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,  # bearer tokens, no cookies
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )

    for router in (
        health.router,
        sessions.router,
        answers.router,
        analytics.router,
        account.router,
        jobs.router,
    ):
        app.include_router(router)
    return app
