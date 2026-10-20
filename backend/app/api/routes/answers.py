import uuid

from fastapi import APIRouter, Query, Response, status

from app.api.dependencies import DbDep, GatewayDep, LimiterDep, UserDep
from app.schemas import AnswerOut, AnswerSubmit
from app.services.evaluation_service import EvaluationService
from app.services.rewrite_service import RewriteService

router = APIRouter(prefix="/api/v1", tags=["answers"])


@router.post(
    "/sessions/{session_id}/answers",
    response_model=AnswerOut,
    status_code=status.HTTP_201_CREATED,
    responses={200: {"model": AnswerOut, "description": "Identical answer already stored (idempotent)."}},
)
async def submit_answer(
    session_id: uuid.UUID,
    data: AnswerSubmit,
    response: Response,
    user: UserDep,
    db: DbDep,
    gateway: GatewayDep,
    limiter: LimiterDep,
) -> AnswerOut:
    """Persist the answer, then evaluate it. If evaluation fails the answer is kept with
    `evaluation_status = "failed"` and can be retried via /answers/{id}/retry-evaluation."""
    answer, created = await EvaluationService(db, gateway, limiter).submit(user, session_id, data)
    if not created:
        response.status_code = status.HTTP_200_OK
    return answer


@router.get("/sessions/{session_id}/answers", response_model=list[AnswerOut])
async def list_answers(
    session_id: uuid.UUID, user: UserDep, db: DbDep, gateway: GatewayDep, limiter: LimiterDep
) -> list[AnswerOut]:
    return await EvaluationService(db, gateway, limiter).list_for_session(user, session_id)


@router.post("/answers/{answer_id}/retry-evaluation", response_model=AnswerOut)
async def retry_evaluation(
    answer_id: uuid.UUID, user: UserDep, db: DbDep, gateway: GatewayDep, limiter: LimiterDep
) -> AnswerOut:
    return await EvaluationService(db, gateway, limiter).retry(user, answer_id)


@router.post("/answers/{answer_id}/rewrite", response_model=AnswerOut)
async def rewrite_answer(
    answer_id: uuid.UUID,
    user: UserDep,
    db: DbDep,
    gateway: GatewayDep,
    limiter: LimiterDep,
    regenerate: bool = Query(False, description="Generate a new example even if one is saved."),
) -> AnswerOut:
    return await RewriteService(db, gateway, limiter).rewrite(user, answer_id, regenerate=regenerate)
