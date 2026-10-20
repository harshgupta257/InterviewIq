import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile, status

from app.api.dependencies import DbDep, GatewayDep, LimiterDep, SettingsDep, UserDep
from app.jobs.providers import JobSearchProvider
from app.jobs.resume_extract import ResumeExtractionError, extract_resume
from app.schemas.jobs import (
    JobMatchRequest,
    JobProfileOut,
    JobProfileRequest,
    JobRematchRequest,
    JobResultOut,
    JobSearchCreate,
    JobSearchOut,
    JobSearchSummary,
    PrepareInterviewOut,
    PrepareInterviewRequest,
    ResumeExtractOut,
)
from app.services.job_finder_service import JobFinderService

router = APIRouter(prefix="/api/v1", tags=["job finder"])


def get_job_provider(request: Request) -> JobSearchProvider:
    provider: JobSearchProvider = request.app.state.job_provider
    return provider


def get_service(
    request: Request,
    db: DbDep,
    gateway: GatewayDep,
    limiter: LimiterDep,
    settings: SettingsDep,
    provider: Annotated[JobSearchProvider, Depends(get_job_provider)],
) -> JobFinderService:
    return JobFinderService(db, gateway, provider, settings, limiter, request.app.state.job_search_limiter)


ServiceDep = Annotated[JobFinderService, Depends(get_service)]


@router.post("/resumes/extract", response_model=ResumeExtractOut)
async def extract_resume_text(
    user: UserDep, settings: SettingsDep, file: Annotated[UploadFile, File(description="PDF or DOCX resume")]
) -> ResumeExtractOut:
    """Extract plain text from an uploaded resume. The file is processed in memory and
    never stored or logged."""
    max_bytes = int(settings.resume_upload_max_mb * 1024 * 1024)
    data = await file.read(max_bytes + 1)
    await file.close()
    if len(data) > max_bytes:
        raise ResumeExtractionError(
            f"The file is larger than {settings.resume_upload_max_mb:g} MB.", code="resume_too_large"
        )
    result = extract_resume(file.filename or "", file.content_type, data, max_bytes)
    return ResumeExtractOut(
        text=result.text,
        file_type=result.file_type,
        pages=result.pages,
        char_count=len(result.text),
        truncated=result.truncated,
        warnings=result.warnings,
    )


@router.post("/jobs/profile", response_model=JobProfileOut)
async def build_profile(data: JobProfileRequest, user: UserDep, svc: ServiceDep) -> JobProfileOut:
    """Stage 1: extract a skills-only profile and suggested roles from the resume."""
    return await svc.profile(user, data.resume_text)


@router.post("/jobs/searches", response_model=JobSearchOut, status_code=status.HTTP_201_CREATED)
async def create_search(data: JobSearchCreate, user: UserDep, svc: ServiceDep) -> JobSearchOut:
    """Stage 2: query the job-search provider (role keywords and location only), then
    validate, de-duplicate and store the listings. Identical searches within the cache
    window are served from storage without using provider quota."""
    return await svc.search(user, data)


@router.get("/jobs/searches", response_model=list[JobSearchSummary])
async def list_searches(user: UserDep, svc: ServiceDep) -> list[JobSearchSummary]:
    return await svc.list_searches(user)


@router.get("/jobs/searches/{search_id}", response_model=JobSearchOut)
async def get_search(search_id: uuid.UUID, user: UserDep, svc: ServiceDep) -> JobSearchOut:
    return await svc.get(user, search_id)


@router.delete("/jobs/searches/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_search(search_id: uuid.UUID, user: UserDep, svc: ServiceDep) -> Response:
    await svc.delete(user, search_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/jobs/searches/{search_id}/match", response_model=JobSearchOut)
async def match_search(
    search_id: uuid.UUID, data: JobMatchRequest, user: UserDep, svc: ServiceDep
) -> JobSearchOut:
    """Stage 3: one batched AI evaluation of the listings against the resume. If it fails,
    the listings remain available and status is "match_failed"."""
    return await svc.match(user, search_id, data.resume_text)


@router.post("/jobs/{job_id}/match", response_model=JobResultOut)
async def rematch_job(
    job_id: uuid.UUID, data: JobRematchRequest, user: UserDep, svc: ServiceDep
) -> JobResultOut:
    """Re-evaluate one listing, optionally with the full job description pasted by the user."""
    return await svc.rematch(user, job_id, data.resume_text, data.description)


@router.post("/jobs/{job_id}/prepare-interview", response_model=PrepareInterviewOut)
async def prepare_interview(
    job_id: uuid.UUID, data: PrepareInterviewRequest, user: UserDep, svc: ServiceDep
) -> PrepareInterviewOut:
    """Create an interview session for this job using the existing interview engine."""
    return await svc.prepare_interview(user, job_id, data)
