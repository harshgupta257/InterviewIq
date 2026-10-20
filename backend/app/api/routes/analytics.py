from fastapi import APIRouter

from app.api.dependencies import DbDep, UserDep
from app.schemas import AnalyticsOverview, AnalyticsProgress
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
async def overview(user: UserDep, db: DbDep) -> AnalyticsOverview:
    return await AnalyticsService(db).overview(user)


@router.get("/progress", response_model=AnalyticsProgress)
async def progress(user: UserDep, db: DbDep) -> AnalyticsProgress:
    return await AnalyticsService(db).progress(user)
