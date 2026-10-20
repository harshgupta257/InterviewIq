import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.dependencies import DbDep, GatewayDep, LimiterDep, UserDep
from app.schemas import RoleType, SessionCreate, SessionDetail, SessionList, SessionSort
from app.services.interview_service import InterviewService

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.post("", response_model=SessionDetail, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: SessionCreate, user: UserDep, db: DbDep, gateway: GatewayDep, limiter: LimiterDep
) -> SessionDetail:
    """Analyse the resume and job description, generate eight tailored questions and
    persist the session. Nothing is saved if generation fails."""
    limiter.check(str(user.id))
    return await InterviewService(db, gateway).create(user, data)


@router.get("", response_model=SessionList)
async def list_sessions(
    user: UserDep,
    db: DbDep,
    gateway: GatewayDep,
    q: Annotated[str | None, Query(max_length=100, description="Search job title or company")] = None,
    role_type: RoleType | None = None,
    status_filter: Annotated[
        str | None, Query(alias="status", pattern="^(in_progress|completed|failed)$")
    ] = None,
    sort: SessionSort = "date_desc",
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 10,
) -> SessionList:
    return await InterviewService(db, gateway).list(
        user,
        search=q,
        role_type=role_type,
        status=status_filter,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(session_id: uuid.UUID, user: UserDep, db: DbDep, gateway: GatewayDep) -> SessionDetail:
    return await InterviewService(db, gateway).detail(user, session_id)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: uuid.UUID, user: UserDep, db: DbDep, gateway: GatewayDep) -> Response:
    await InterviewService(db, gateway).delete(user, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
