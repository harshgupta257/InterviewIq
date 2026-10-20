"""Turn raw provider listings into safe, de-duplicated, honestly-labelled records.

Only data actually present in the listing is kept; anything missing stays None and is
shown as "Not listed". Predicted salaries are not presented as published ones.
"""

import html
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit

from app.jobs.providers import RawJob

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
# Only the provider's own listing links are followed. Prevents javascript:/data: URLs,
# credential-bearing URLs and arbitrary destinations from being rendered.
ALLOWED_HOST = re.compile(
    r"^(?:[a-z0-9-]+\.)*adzuna\.(?:com|co\.uk|in|com\.au|ca|de|fr|nl|sg|co\.nz|co\.za|at|be|ch|es|it|pl|com\.br|com\.mx)$"
)


def clean_text(value: str | None, limit: int = 4000) -> str | None:
    if not value:
        return None
    text = html.unescape(_TAG.sub(" ", value))
    text = _WS.sub(" ", text).strip()
    return text[:limit] or None


def safe_url(url: str | None, allowed: re.Pattern[str] = ALLOWED_HOST) -> str | None:
    if not url or len(url) > 2048:
        return None
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return None
    host = (parts.hostname or "").lower()
    if parts.scheme not in ("https", "http") or parts.username or parts.password or not host:
        return None
    if not allowed.match(host):
        return None
    # Always link over HTTPS.
    return parts._replace(scheme="https").geturl()


def detect_work_mode(*texts: str | None) -> str | None:
    blob = " ".join(t for t in texts if t).lower()
    if not blob:
        return None
    if "hybrid" in blob:
        return "hybrid"
    if re.search(r"\b(fully remote|remote|work from home|wfh)\b", blob):
        return "remote"
    if re.search(r"\b(on-?site|in-office|in office)\b", blob):
        return "onsite"
    return None


def detect_level(title: str) -> str | None:
    t = title.lower()
    if re.search(r"\bintern(ship)?\b|\btrainee\b|\bapprentice", t):
        return "intern"
    if re.search(r"\b(principal|staff|lead|head|director|architect|manager)\b", t):
        return "lead"
    if re.search(r"\b(senior|sr\.?)\b", t):
        return "senior"
    if re.search(r"\b(junior|jr\.?|graduate|entry[- ]level|fresher|associate)\b", t):
        return "junior"
    if re.search(r"\b(mid|ii|2)\b", t):
        return "mid"
    return None


def employment_type(raw: RawJob) -> str | None:
    time = {"full_time": "Full-time", "part_time": "Part-time"}.get(raw.contract_time or "")
    kind = {"permanent": "Permanent", "contract": "Contract"}.get(raw.contract_type or "")
    parts = [p for p in (time, kind) if p]
    return " · ".join(parts) or None


@dataclass
class NormalizedJob:
    provider: str
    provider_job_id: str
    dedupe_key: str
    title: str
    company: str | None
    location: str | None
    work_mode: str | None
    employment_type: str | None
    experience_level: str | None
    salary_min: float | None
    salary_max: float | None
    description: str | None
    url: str
    posted_at: datetime | None
    category: str | None


def _key(*parts: str | None) -> str:
    return "|".join(_WS.sub(" ", (p or "").lower()).strip() for p in parts)


def normalize(raw_jobs: list[RawJob]) -> tuple[list[NormalizedJob], int]:
    """Returns (valid de-duplicated jobs, number rejected for unsafe/missing URLs)."""
    seen: set[str] = set()
    out: list[NormalizedJob] = []
    rejected = 0
    for r in raw_jobs:
        url = safe_url(r.url)
        title = clean_text(r.title, 300)
        if not url or not title:
            rejected += 1
            continue
        company = clean_text(r.company, 200)
        location = clean_text(r.location, 200)
        ids = {f"id:{r.provider}:{r.provider_job_id}"} if r.provider_job_id else set()
        content_key = "c:" + _key(title, company, location)
        if (ids & seen) or content_key in seen:
            continue
        seen |= ids | {content_key}
        description = clean_text(r.description)
        published_salary = not r.salary_is_predicted
        out.append(
            NormalizedJob(
                provider=r.provider,
                provider_job_id=r.provider_job_id or content_key,
                dedupe_key=content_key,
                title=title,
                company=company,
                location=location,
                work_mode=detect_work_mode(title, description, location),
                employment_type=employment_type(r),
                experience_level=detect_level(title),
                salary_min=r.salary_min if published_salary else None,
                salary_max=r.salary_max if published_salary else None,
                description=description,
                url=url,
                posted_at=r.posted_at,
                category=clean_text(r.category, 120),
            )
        )
    return out, rejected
