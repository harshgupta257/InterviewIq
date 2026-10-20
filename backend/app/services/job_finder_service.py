"""AI Job Finder orchestration.

Stages map to separate API calls so the UI's progress reflects real work:
  1. profile  - Gemini extracts a skills-only profile from the resume (no web access).
  2. search   - the job-search provider is queried with role/location keywords only
                (never resume text); results are validated, de-duplicated and cached.
  3. match    - one batched Gemini call rates every listing; the score is computed here.
Interview preparation reuses the existing InterviewService unchanged.
"""

import hashlib
import json
import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.prompts import job_matching, resume_profile
from app.ai.schemas import JobMatchBatch, JobMatchItem, ResumeProfile
from app.core.config import Settings
from app.core.exceptions import AppError, NotFoundError
from app.core.logging import get_logger
from app.core.rate_limit import RateLimiter
from app.core.security import CurrentUser
from app.jobs.matching import SCORING_VERSION, compute_score, score_label, skill_coverage
from app.jobs.normalize import normalize
from app.jobs.providers import ADZUNA_LOCAL_SITES, JobProviderError, JobQuery, JobSearchProvider
from app.models import JobResult, JobSearch, utcnow
from app.repositories.sessions import SessionRepository
from app.schemas import MIN_JD_CHARS, SessionCreate
from app.schemas.jobs import (
    Attribution,
    JobMatchOut,
    JobProfile,
    JobProfileOut,
    JobResultOut,
    JobSearchCreate,
    JobSearchOut,
    JobSearchParams,
    JobSearchSummary,
    MatchComponents,
    PrepareInterviewOut,
    PrepareInterviewRequest,
)
from app.services.ai_gateway import AIGateway, redact_contact_details
from app.services.interview_service import InterviewService
from app.services.serializers import session_detail

log = get_logger(__name__)

CURRENCY = {
    "in": "INR",
    "gb": "GBP",
    "us": "USD",
    "au": "AUD",
    "ca": "CAD",
    "de": "EUR",
    "fr": "EUR",
    "nl": "EUR",
    "sg": "SGD",
    "nz": "NZD",
    "za": "ZAR",
}
SOURCE_NAMES = {"adzuna": "Adzuna"}


def build_queries(data: JobSearchCreate, max_queries: int) -> list[str]:
    """Role keywords only. The resume never leaves the server for search."""
    roles = data.target_roles or data.profile.suggested_roles
    out: list[str] = []
    for role in roles:
        q = role.strip()
        low = q.lower()
        if data.experience_level == "intern" and "intern" not in low:
            q += " internship"
        if data.work_modes == ["remote"] and "remote" not in low:
            q += " remote"
        if q.lower() not in {x.lower() for x in out}:
            out.append(q)
        if len(out) >= max_queries:
            break
    return out


def _cache_key(provider: str, country: str | None, queries: list[str], data: JobSearchCreate) -> str:
    blob = json.dumps(
        {
            "p": provider,
            "c": country,
            "q": [q.lower() for q in queries],
            "l": (data.location or "").lower(),
            "e": sorted(data.employment_types),
            "w": sorted(data.work_modes),
        },
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode()).hexdigest()


def attribution_for(provider: str, country: str | None) -> Attribution | None:
    """Source attribution required by the provider's terms, shown next to its listings."""
    if provider == "adzuna":
        return Attribution(
            label="Jobs by Adzuna", url=ADZUNA_LOCAL_SITES.get(country or "", "https://www.adzuna.com")
        )
    return None


def _f(v: Decimal | None) -> float | None:
    return float(v) if v is not None else None


def result_out(r: JobResult) -> JobResultOut:
    return JobResultOut(
        id=r.id,
        rank=r.rank,
        title=r.title,
        company=r.company,
        location=r.location,
        work_mode=r.work_mode,
        employment_type=r.employment_type,
        experience_level=r.experience_level,
        salary_min=_f(r.salary_min),
        salary_max=_f(r.salary_max),
        salary_currency=r.salary_currency,
        category=r.category,
        description=r.description,
        description_source=r.description_source,
        url=r.url,
        source=SOURCE_NAMES.get(r.provider, r.provider),
        posted_at=r.posted_at,
        retrieved_at=r.retrieved_at,
        match=JobMatchOut.model_validate(r.match) if r.match else None,
        interview_session_id=r.interview_session_id,
    )


class JobFinderService:
    def __init__(
        self,
        db: AsyncSession,
        gateway: AIGateway,
        provider: JobSearchProvider,
        settings: Settings,
        ai_limiter: RateLimiter,
        search_limiter: RateLimiter,
    ) -> None:
        self.db = db
        self.gateway = gateway
        self.provider = provider
        self.settings = settings
        self.ai_limiter = ai_limiter
        self.search_limiter = search_limiter

    # ------------------------------------------------------------------ stage 1
    async def profile(self, user: CurrentUser, resume_text: str) -> JobProfileOut:
        self.ai_limiter.check(str(user.id))
        out = await self.gateway.run(
            user_id=user.id,
            operation="resume_profile",
            system_prompt=resume_profile.SYSTEM_PROMPT,
            payload=resume_profile.build_payload(resume_text=redact_contact_details(resume_text)),
            model_cls=ResumeProfile,
            temperature=0.1,
        )
        return JobProfileOut(**out.value.model_dump(), is_demo=self.gateway.is_demo)

    # ------------------------------------------------------------------ stage 2
    async def search(self, user: CurrentUser, data: JobSearchCreate) -> JobSearchOut:
        queries = build_queries(data, self.settings.job_search_max_queries)
        if not queries:
            raise AppError("Add at least one target role to search for.", code="job_search_no_roles")
        country = getattr(self.provider, "country", None)
        key = _cache_key(self.provider.name, country, queries, data)
        now = utcnow()

        if not data.refresh and self.settings.job_search_cache_minutes > 0:
            cached = (
                await self.db.execute(
                    select(JobSearch)
                    .where(
                        JobSearch.user_id == user.id, JobSearch.cache_key == key, JobSearch.expires_at > now
                    )
                    .order_by(JobSearch.created_at.desc())
                    .limit(1)
                    .options(selectinload(JobSearch.results))
                )
            ).scalar_one_or_none()
            if cached:
                return self._out(cached, cached_hit=True)

        # Only uncached searches consume provider quota, so only they are rate limited.
        self.search_limiter.check(str(user.id))

        filters = set(data.employment_types)
        raw = []
        warnings: list[str] = []
        for q in queries:
            try:
                raw.extend(
                    await self.provider.search(
                        JobQuery(
                            keywords=q,
                            location=data.location,
                            full_time="full_time" in filters,
                            part_time="part_time" in filters,
                            contract="contract" in filters,
                            permanent="permanent" in filters,
                            results=self.settings.job_search_results_per_query,
                        )
                    )
                )
            except JobProviderError as exc:
                # No retry: a retry would spend more provider quota.
                if not raw:
                    raise
                warnings.append(f"Results are incomplete: the search for “{q}” failed ({exc.message})")
                break

        jobs, rejected = normalize(raw)
        if data.work_modes:
            # Keep listings whose arrangement is unknown: the listing may simply not say.
            jobs = [j for j in jobs if j.work_mode is None or j.work_mode in data.work_modes]

        search = JobSearch(
            user_id=user.id,
            cache_key=key,
            provider=self.provider.name,
            country=country,
            params=JobSearchParams(
                target_roles=data.target_roles,
                location=data.location,
                experience_level=data.experience_level,
                work_modes=list(data.work_modes),
                employment_types=list(data.employment_types),
            ).model_dump(),
            queries=queries,
            profile=data.profile.model_dump(),
            status="discovered",
            total_found=len(jobs),
            rejected=rejected,
            created_at=now,
            expires_at=now + timedelta(minutes=self.settings.job_search_cache_minutes),
        )
        self.db.add(search)
        await self.db.flush()
        currency = CURRENCY.get(country or "")
        for rank, j in enumerate(jobs):
            self.db.add(
                JobResult(
                    search_id=search.id,
                    user_id=user.id,
                    rank=rank,
                    provider=j.provider,
                    provider_job_id=j.provider_job_id[:300],
                    title=j.title,
                    company=j.company,
                    location=j.location,
                    work_mode=j.work_mode,
                    employment_type=j.employment_type,
                    experience_level=j.experience_level,
                    salary_min=Decimal(str(j.salary_min)) if j.salary_min is not None else None,
                    salary_max=Decimal(str(j.salary_max)) if j.salary_max is not None else None,
                    salary_currency=currency if (j.salary_min or j.salary_max) else None,
                    category=j.category,
                    description=j.description,
                    url=j.url,
                    posted_at=j.posted_at,
                    retrieved_at=now,
                )
            )
        await self.db.commit()
        log.info(
            "job_search_completed",
            extra={"search_id": str(search.id), "results": len(jobs), "rejected": rejected},
        )
        loaded = await self._get_owned(user, search.id)
        return self._out(loaded, warnings=warnings)

    # ------------------------------------------------------------------ stage 3
    async def match(self, user: CurrentUser, search_id: uuid.UUID, resume_text: str) -> JobSearchOut:
        search = await self._get_owned(user, search_id)
        targets = search.results[: self.settings.job_search_max_matched]
        if not targets:
            return self._out(search)
        self.ai_limiter.check(str(user.id))
        try:
            await self._match_results(user, search, targets, resume_text)
            search.status = "matched"
            search.match_error = None
        except AppError as exc:
            search.status = "match_failed"
            search.match_error = exc.message
            log.warning("job_match_failed", extra={"search_id": str(search.id), "code": exc.code})
        await self.db.commit()
        return self._out(await self._get_owned(user, search_id))

    async def rematch(
        self, user: CurrentUser, job_id: uuid.UUID, resume_text: str, description: str | None
    ) -> JobResultOut:
        job = await self._get_job(user, job_id)
        if description:
            job.description = description
            job.description_source = "user_provided"
        self.ai_limiter.check(str(user.id))
        await self._match_results(user, job.search, [job], resume_text)
        await self.db.commit()
        await self.db.refresh(job)
        return result_out(job)

    async def _match_results(
        self, user: CurrentUser, search: JobSearch, targets: list[JobResult], resume_text: str
    ) -> None:
        profile = ResumeProfile.model_validate(
            {
                **search.profile,
                "suggested_roles": search.profile.get("suggested_roles") or ["(not specified)"],
                "summary": search.profile.get("summary") or "(not provided)",
            }
        )
        refs = {f"J{i + 1}": r for i, r in enumerate(targets)}
        payload = job_matching.build_payload(
            candidate_profile={k: v for k, v in search.profile.items() if k != "summary"}
            | {"summary": profile.summary},
            resume_excerpt=redact_contact_details(resume_text)[:6000],
            jobs=[
                {
                    "job_ref": ref,
                    "title": r.title,
                    "company": r.company or "Not listed",
                    "location": r.location or "Not listed",
                    "employment_type": r.employment_type or "Not listed",
                    "listing_text": r.description or "(The listing provided no description.)",
                    "listing_text_kind": "full description provided by the candidate"
                    if r.description_source == "user_provided"
                    else "short summary from a job-search listing",
                }
                for ref, r in refs.items()
            ],
        )
        outcome = await self.gateway.run(
            user_id=user.id,
            operation="job_matching",
            system_prompt=job_matching.SYSTEM_PROMPT,
            payload=payload,
            model_cls=JobMatchBatch,
            temperature=0.1,
        )
        now = utcnow()
        by_ref: dict[str, JobMatchItem] = {m.job_ref: m for m in outcome.value.matches}
        for ref, r in refs.items():
            item = by_ref.get(ref)
            if item is None:
                continue  # model skipped it: leave unmatched rather than guess
            cov = skill_coverage(item.required_skills, profile, resume_text)
            score = compute_score(item, cov)
            full = r.description_source == "user_provided" and item.description_sufficient
            r.match = JobMatchOut(
                score=score,
                label=score_label(score),
                confidence="full" if full else "provisional",
                required_skills=[s.strip() for s in item.required_skills],
                matched_skills=cov.matched,
                missing_skills=cov.missing,
                relevant_experience=item.relevant_experience,
                reasons=item.reasons,
                improvements=item.improvements,
                gaps=item.gaps,
                description_sufficient=item.description_sufficient,
                components=MatchComponents(
                    skills=round(cov.ratio, 3) if cov.ratio is not None else None,
                    experience=item.experience_fit,
                    role=item.role_alignment,
                    responsibilities=item.responsibilities_fit,
                ),
                scoring_version=SCORING_VERSION,
                model=outcome.model,
                is_demo=self.gateway.is_demo,
                matched_at=now,
            ).model_dump(mode="json")

    # ------------------------------------------------------- interview handoff
    async def prepare_interview(
        self, user: CurrentUser, job_id: uuid.UUID, data: PrepareInterviewRequest
    ) -> PrepareInterviewOut:
        job = await self._get_job(user, job_id)
        if data.description:
            job.description = data.description
            job.description_source = "user_provided"
            await self.db.commit()

        if job.interview_session_id and not data.new_session and not data.description:
            try:
                existing = await SessionRepository(self.db).get_owned(
                    user.id, job.interview_session_id, with_children=True
                )
                stats = (await SessionRepository(self.db).stats_for([existing.id]))[existing.id]
                return PrepareInterviewOut(
                    job_id=job.id, created=False, session=session_detail(existing, stats)
                )
            except NotFoundError:
                pass  # session was deleted; create a new one

        description = job.description or ""
        if len(description) < MIN_JD_CHARS:
            raise AppError(
                "This listing doesn't include enough of the job description to prepare an interview. "
                "Open the job, copy its full description, and paste it here.",
                code="job_description_insufficient",
            )
        header = "\n".join(
            x
            for x in (
                f"Role: {job.title}",
                f"Company: {job.company}" if job.company else None,
                f"Location: {job.location}" if job.location else None,
                f"Employment type: {job.employment_type}" if job.employment_type else None,
            )
            if x
        )
        level = job.search.params.get("experience_level")
        session_in = SessionCreate(
            resume_text=data.resume_text,
            jd_text=f"{header}\n\n{description}"[:12000],
            job_title=job.title[:200],
            company=(job.company or None),
            role_type=data.role_type,
            seniority_level=level
            if level in {"intern", "junior", "mid", "senior", "staff", "lead"}
            else None,
        )
        self.ai_limiter.check(str(user.id))
        detail = await InterviewService(self.db, self.gateway).create(user, session_in)
        job.interview_session_id = detail.id
        await self.db.commit()
        return PrepareInterviewOut(job_id=job.id, created=True, session=detail)

    # ------------------------------------------------------------------ reads
    async def list_searches(self, user: CurrentUser, limit: int = 20) -> list[JobSearchSummary]:
        rows = (
            (
                await self.db.execute(
                    select(JobSearch)
                    .where(JobSearch.user_id == user.id)
                    .order_by(JobSearch.created_at.desc())
                    .limit(limit)
                    .options(selectinload(JobSearch.results))
                )
            )
            .scalars()
            .all()
        )
        return [
            JobSearchSummary(
                id=s.id,
                created_at=s.created_at,
                queries=s.queries,
                params=JobSearchParams(**s.params),
                status=s.status,
                result_count=len(s.results),
            )
            for s in rows
        ]

    async def get(self, user: CurrentUser, search_id: uuid.UUID) -> JobSearchOut:
        return self._out(await self._get_owned(user, search_id))

    async def delete(self, user: CurrentUser, search_id: uuid.UUID) -> None:
        res = await self.db.execute(
            delete(JobSearch).where(JobSearch.id == search_id, JobSearch.user_id == user.id)
        )
        await self.db.commit()
        if not res.rowcount:
            raise NotFoundError("Job search not found.")

    async def _get_owned(self, user: CurrentUser, search_id: uuid.UUID) -> JobSearch:
        s = (
            await self.db.execute(
                select(JobSearch)
                .where(JobSearch.id == search_id, JobSearch.user_id == user.id)
                .options(selectinload(JobSearch.results))
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        if s is None:
            raise NotFoundError("Job search not found.")
        return s

    async def _get_job(self, user: CurrentUser, job_id: uuid.UUID) -> JobResult:
        r = (
            await self.db.execute(
                select(JobResult)
                .where(JobResult.id == job_id, JobResult.user_id == user.id)
                .options(selectinload(JobResult.search))
            )
        ).scalar_one_or_none()
        if r is None:
            raise NotFoundError("Job not found.")
        return r

    def _out(
        self, s: JobSearch, *, cached_hit: bool = False, warnings: list[str] | None = None
    ) -> JobSearchOut:
        return JobSearchOut(
            id=s.id,
            created_at=s.created_at,
            expires_at=s.expires_at,
            provider=s.provider,
            attribution=attribution_for(s.provider, s.country),
            params=JobSearchParams(**s.params),
            queries=s.queries,
            profile=JobProfile.model_validate(s.profile),
            status=s.status,
            match_error=s.match_error,
            total_found=s.total_found,
            rejected=s.rejected,
            cached=cached_hit,
            warnings=warnings or [],
            results=[result_out(r) for r in sorted(s.results, key=lambda r: r.rank)],
        )
