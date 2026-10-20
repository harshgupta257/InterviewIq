from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import AuthError
from app.core.rate_limit import RateLimiter
from app.core.security import CurrentUser, verify_access_token
from app.services.ai_gateway import AIGateway

_bearer = HTTPBearer(auto_error=False)


def get_settings_dep(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session


def get_gateway(request: Request) -> AIGateway:
    gateway: AIGateway = request.app.state.ai_gateway
    return gateway


def get_limiter(request: Request) -> RateLimiter:
    limiter: RateLimiter = request.app.state.rate_limiter
    return limiter


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings_dep)],
) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise AuthError("Authentication required.")
    return verify_access_token(credentials.credentials, settings)


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
DbDep = Annotated[AsyncSession, Depends(get_db)]
GatewayDep = Annotated[AIGateway, Depends(get_gateway)]
LimiterDep = Annotated[RateLimiter, Depends(get_limiter)]
UserDep = Annotated[CurrentUser, Depends(get_current_user)]
