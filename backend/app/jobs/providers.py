"""Job-search providers.

A provider takes a small, PII-free query (role keywords, location, filters) and returns
real listings from a licensed source. The resume itself is never sent to a provider.

Why not Gemini "Grounding with Google Search"? The Gemini API terms forbid analysing,
caching, altering, or mixing other content into grounded results, and collecting their
links for other purposes. A job finder must do all of those, so grounding is not used.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx

from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.logging import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class JobQuery:
    keywords: str
    location: str | None = None
    full_time: bool = False
    part_time: bool = False
    contract: bool = False
    permanent: bool = False
    max_days_old: int = 30
    results: int = 10


@dataclass
class RawJob:
    provider: str
    provider_job_id: str
    title: str
    company: str | None
    location: str | None
    description: str | None
    url: str | None
    posted_at: datetime | None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_is_predicted: bool = False
    contract_type: str | None = None  # permanent | contract
    contract_time: str | None = None  # full_time | part_time
    category: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Attribution:
    label: str
    url: str


class JobProviderError(AppError):
    status_code = 502
    code = "job_search_unavailable"


class JobProviderQuotaError(JobProviderError):
    status_code = 429
    code = "job_search_quota_exceeded"


class JobProviderNotConfigured(JobProviderError):
    status_code = 503
    code = "job_search_not_configured"


class JobSearchProvider(ABC):
    name: str
    attribution: Attribution | None = None

    @abstractmethod
    async def search(self, query: JobQuery) -> list[RawJob]: ...

    async def aclose(self) -> None:  # pragma: no cover - default no-op
        return None


class UnconfiguredJobProvider(JobSearchProvider):
    """Used when no job-search credentials are set. Never returns results."""

    name = "none"

    async def search(self, query: JobQuery) -> list[RawJob]:
        raise JobProviderNotConfigured(
            "Live job search isn't configured on this server yet. An administrator needs to add "
            "ADZUNA_APP_ID and ADZUNA_APP_KEY to the backend configuration."
        )


ADZUNA_LOCAL_SITES = {
    "gb": "https://www.adzuna.co.uk",
    "in": "https://www.adzuna.in",
    "us": "https://www.adzuna.com",
    "au": "https://www.adzuna.com.au",
    "ca": "https://www.adzuna.ca",
    "de": "https://www.adzuna.de",
    "fr": "https://www.adzuna.fr",
    "nl": "https://www.adzuna.nl",
    "sg": "https://www.adzuna.sg",
    "nz": "https://www.adzuna.co.nz",
    "za": "https://www.adzuna.co.za",
}


def _parse_dt(v: Any) -> datetime | None:
    if not isinstance(v, str):
        return None
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return None


def _num(v: Any) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


class AdzunaProvider(JobSearchProvider):
    """Adzuna job-search API (https://developer.adzuna.com). Requires the "Adzuna"
    attribution next to listings, which the frontend renders."""

    name = "adzuna"
    BASE = "https://api.adzuna.com/v1/api/jobs"

    def __init__(
        self, app_id: str, app_key: str, country: str, client: httpx.AsyncClient | None = None
    ) -> None:
        self._app_id = app_id
        self._app_key = app_key
        self.country = country
        self.attribution = Attribution(
            "Jobs by Adzuna", ADZUNA_LOCAL_SITES.get(country, "https://www.adzuna.com")
        )
        self._client = client or httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=8.0))

    async def aclose(self) -> None:
        await self._client.aclose()

    async def search(self, query: JobQuery) -> list[RawJob]:
        params: dict[str, Any] = {
            "app_id": self._app_id,
            "app_key": self._app_key,
            "what": query.keywords,
            "results_per_page": query.results,
            "max_days_old": query.max_days_old,
            "content-type": "application/json",
        }
        if query.location:
            params["where"] = query.location
        for flag in ("full_time", "part_time", "contract", "permanent"):
            if getattr(query, flag):
                params[flag] = 1
        try:
            resp = await self._client.get(f"{self.BASE}/{self.country}/search/1", params=params)
        except httpx.TimeoutException as exc:
            raise JobProviderError("The job-search service timed out. Please try again.") from exc
        except httpx.TransportError as exc:
            raise JobProviderError(
                "Couldn't reach the job-search service. Check your connection and try again."
            ) from exc

        # Never log the request URL: it contains the API key.
        if resp.status_code == 429:
            raise JobProviderQuotaError(
                "The job-search service's usage limit has been reached. Please try again later."
            )
        if resp.status_code in (401, 403):
            log.error("job_provider_auth_failed", extra={"provider": self.name, "status": resp.status_code})
            raise JobProviderNotConfigured("The job-search service rejected this server's credentials.")
        if resp.status_code >= 400:
            log.warning("job_provider_error", extra={"provider": self.name, "status": resp.status_code})
            raise JobProviderError("The job-search service returned an error. Please try again.")
        try:
            data = resp.json()
        except ValueError as exc:
            raise JobProviderError("The job-search service returned an unreadable response.") from exc

        jobs: list[RawJob] = []
        for r in data.get("results") or []:
            if not isinstance(r, dict) or not r.get("title"):
                continue
            jobs.append(
                RawJob(
                    provider=self.name,
                    provider_job_id=str(r.get("id") or ""),
                    title=str(r.get("title")),
                    company=(r.get("company") or {}).get("display_name"),
                    location=(r.get("location") or {}).get("display_name"),
                    description=r.get("description"),
                    url=r.get("redirect_url"),
                    posted_at=_parse_dt(r.get("created")),
                    salary_min=_num(r.get("salary_min")),
                    salary_max=_num(r.get("salary_max")),
                    salary_is_predicted=str(r.get("salary_is_predicted", "0")) == "1",
                    contract_type=r.get("contract_type"),
                    contract_time=r.get("contract_time"),
                    category=(r.get("category") or {}).get("label"),
                )
            )
        return jobs


def build_job_provider(settings: Settings) -> JobSearchProvider:
    if settings.job_search_enabled:
        return AdzunaProvider(settings.adzuna_app_id, settings.adzuna_app_key, settings.adzuna_country)
    return UnconfiguredJobProvider()
