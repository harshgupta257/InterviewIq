"""Access-token verification.

Supported token sources:
1. Supabase Auth access tokens.
   - Asymmetric signing keys (RS256/ES256), verified against the project's JWKS
     endpoint. This is Supabase's recommended setup and supports key rotation.
   - Legacy symmetric HS256 tokens, verified with SUPABASE_JWT_SECRET.
2. Demo tokens (only when DEMO_MODE=true), signed by this backend with DEMO_JWT_SECRET
   and issued by POST /api/v1/demo/session.

The authenticated user ID always comes from the verified `sub` claim, never from
request bodies or query parameters.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from jwt import PyJWKClient

from app.core.config import Settings
from app.core.exceptions import AuthError
from app.core.logging import get_logger

log = get_logger(__name__)

DEMO_ISSUER = "interviewiq-demo"
DEMO_TOKEN_TTL = timedelta(hours=12)
# Tolerate small clock differences between this server and the token issuer; without it,
# freshly issued tokens are intermittently rejected as "not yet valid (iat)".
CLOCK_SKEW_LEEWAY_SECONDS = 30


@dataclass(frozen=True)
class CurrentUser:
    id: uuid.UUID
    email: str | None
    is_demo: bool


_jwks_clients: dict[str, PyJWKClient] = {}


def _jwks_client(supabase_url: str) -> PyJWKClient:
    url = supabase_url.rstrip("/") + "/auth/v1/.well-known/jwks.json"
    client = _jwks_clients.get(url)
    if client is None:
        client = PyJWKClient(url, cache_keys=True, lifespan=600, timeout=5)
        _jwks_clients[url] = client
    return client


def issue_demo_token(settings: Settings, user_id: uuid.UUID) -> tuple[str, datetime]:
    expires = datetime.now(UTC) + DEMO_TOKEN_TTL
    token = jwt.encode(
        {
            "sub": str(user_id),
            "iss": DEMO_ISSUER,
            "aud": DEMO_ISSUER,
            "role": "demo",
            "exp": expires,
            "iat": datetime.now(UTC),
        },
        settings.demo_jwt_secret,
        algorithm="HS256",
    )
    return token, expires


def _user_from_claims(claims: dict, *, is_demo: bool) -> CurrentUser:
    try:
        user_id = uuid.UUID(str(claims["sub"]))
    except (KeyError, ValueError) as exc:
        raise AuthError("Token has no valid subject.") from exc
    return CurrentUser(id=user_id, email=claims.get("email"), is_demo=is_demo)


def verify_access_token(token: str, settings: Settings) -> CurrentUser:
    try:
        header = jwt.get_unverified_header(token)
        unverified = jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError as exc:
        raise AuthError("Malformed access token.") from exc

    alg = header.get("alg")
    try:
        if unverified.get("iss") == DEMO_ISSUER:
            if not settings.demo_mode:
                raise AuthError("Demo tokens are not accepted by this server.")
            claims = jwt.decode(
                token,
                settings.demo_jwt_secret,
                algorithms=["HS256"],
                audience=DEMO_ISSUER,
                leeway=CLOCK_SKEW_LEEWAY_SECONDS,
                issuer=DEMO_ISSUER,
            )
            return _user_from_claims(claims, is_demo=True)

        if alg in ("RS256", "ES256", "EdDSA"):
            if not settings.supabase_url:
                raise AuthError("Supabase authentication is not configured.")
            signing_key = _jwks_client(settings.supabase_url).get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=[alg],
                audience=settings.supabase_jwt_audience,
                leeway=CLOCK_SKEW_LEEWAY_SECONDS,
                issuer=settings.supabase_url.rstrip("/") + "/auth/v1",
            )
            return _user_from_claims(claims, is_demo=False)

        if alg == "HS256":
            if not settings.supabase_jwt_secret:
                raise AuthError("Supabase authentication is not configured.")
            claims = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience=settings.supabase_jwt_audience,
                leeway=CLOCK_SKEW_LEEWAY_SECONDS,
            )
            return _user_from_claims(claims, is_demo=False)
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Your session has expired. Please sign in again.", code="token_expired") from exc
    except jwt.PyJWKClientError as exc:
        log.warning("jwks_fetch_failed", extra={"error_type": type(exc).__name__})
        raise AuthError("Unable to verify access token right now.") from exc
    except jwt.PyJWTError as exc:
        raise AuthError("Invalid access token.") from exc

    raise AuthError("Unsupported token algorithm.")
