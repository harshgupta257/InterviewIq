"""Profile management and account deletion."""

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.core.security import CurrentUser
from app.models import JobSearch, Profile
from app.repositories.answers import AnswerRepository
from app.repositories.sessions import SessionRepository
from app.schemas import ProfileOut, ProfileUpdate

log = get_logger(__name__)


class AccountService:
    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def get_profile(self, user: CurrentUser) -> ProfileOut:
        profile = (await self.db.execute(select(Profile).where(Profile.id == user.id))).scalar_one_or_none()
        return ProfileOut(
            id=user.id,
            email=user.email,
            display_name=profile.display_name if profile else None,
            is_demo=user.is_demo,
        )

    async def update_profile(self, user: CurrentUser, data: ProfileUpdate) -> ProfileOut:
        profile = (await self.db.execute(select(Profile).where(Profile.id == user.id))).scalar_one_or_none()
        if profile is None:
            profile = Profile(id=user.id)
            self.db.add(profile)
        profile.display_name = data.display_name or None
        await self.db.commit()
        return await self.get_profile(user)

    async def delete_account(self, user: CurrentUser) -> None:
        """Delete all application data, then the Supabase Auth user.

        Application data is removed first in a single transaction. If the Auth deletion
        then fails, the user is told so (no false success) and can retry; their data is
        already gone, and retrying is safe because every step is idempotent.
        """
        await self.db.execute(delete(JobSearch).where(JobSearch.user_id == user.id))
        await SessionRepository(self.db).delete_all_for_user(user.id)
        await AnswerRepository(self.db).delete_user_data(user.id)
        await self.db.commit()
        log.info("account_data_deleted")

        if user.is_demo:
            return
        if not (self.settings.supabase_url and self.settings.supabase_service_role_key):
            raise AppError(
                "Your interview data was deleted, but this server is not configured to delete "
                "authentication accounts. Contact the administrator to remove your login.",
                code="auth_deletion_unavailable",
            )
        url = f"{self.settings.supabase_url.rstrip('/')}/auth/v1/admin/users/{user.id}"
        key = self.settings.supabase_service_role_key
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.delete(url, headers={"apikey": key, "Authorization": f"Bearer {key}"})
        except httpx.HTTPError as exc:
            raise AppError(
                "Your data was deleted but the login could not be removed. Please retry.",
                code="auth_deletion_failed",
            ) from exc
        if resp.status_code not in (200, 204, 404):
            log.error("auth_user_delete_failed", extra={"status": resp.status_code})
            raise AppError(
                "Your data was deleted but the login could not be removed. Please retry.",
                code="auth_deletion_failed",
            )
