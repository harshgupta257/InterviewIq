import uuid

from fastapi import APIRouter, Request, Response, status

from app.api.dependencies import DbDep, SettingsDep, UserDep
from app.core.exceptions import ForbiddenError
from app.core.security import issue_demo_token
from app.schemas import DemoSessionOut, ProfileOut, ProfileUpdate
from app.services.account_service import AccountService
from app.services.demo_service import seed_demo_user

router = APIRouter(prefix="/api/v1", tags=["account"])


@router.get("/me", response_model=ProfileOut)
async def me(user: UserDep, db: DbDep, settings: SettingsDep) -> ProfileOut:
    return await AccountService(db, settings).get_profile(user)


@router.patch("/me", response_model=ProfileOut)
async def update_me(data: ProfileUpdate, user: UserDep, db: DbDep, settings: SettingsDep) -> ProfileOut:
    return await AccountService(db, settings).update_profile(user, data)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(user: UserDep, db: DbDep, settings: SettingsDep) -> Response:
    """Permanently delete the account: sessions, questions, answers, profile, usage
    records and (for Supabase users) the authentication user."""
    await AccountService(db, settings).delete_account(user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/demo/session", response_model=DemoSessionOut, status_code=status.HTTP_201_CREATED)
async def start_demo(request: Request, db: DbDep, settings: SettingsDep) -> DemoSessionOut:
    """Create an isolated demo account seeded with labelled sample history.
    Only available when DEMO_MODE=true."""
    if not settings.demo_mode:
        raise ForbiddenError("Demo mode is disabled on this server.", code="demo_disabled")
    request.app.state.demo_limiter.check(request.client.host if request.client else "unknown")
    user_id = uuid.uuid4()
    await seed_demo_user(db, user_id)
    token, expires = issue_demo_token(settings, user_id)
    return DemoSessionOut(access_token=token, expires_at=expires, user_id=user_id)
