"""AI Job Finder: extraction, provider, normalisation, search, matching, isolation, handoff."""

import io
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.ai.provider import ProviderError
from app.ai.schemas import JobMatchItem, ResumeProfile
from app.jobs.matching import compute_score, score_label, skill_coverage
from app.jobs.normalize import normalize, safe_url
from app.jobs.providers import (
    AdzunaProvider,
    JobProviderError,
    JobProviderNotConfigured,
    JobProviderQuotaError,
    JobQuery,
    JobSearchProvider,
    RawJob,
)
from app.jobs.resume_extract import ResumeExtractionError, extract_resume
from tests.conftest import PROFILE, RESUME, FakeProvider

LONG_DESC = (
    "We are hiring a backend engineer to design reliable production APIs in Python. You will build data "
    "pipelines with Kafka, own deployments on AWS with Docker, and collaborate with product. Requirements: "
    "3+ years of Python, SQL, REST API design, CI/CD. Nice to have: Kafka, Kubernetes."
)


def raw(i: int, **kw: Any) -> RawJob:
    base: dict[str, Any] = dict(
        provider="adzuna",
        provider_job_id=str(i),
        title=f"Backend Engineer {i}",
        company=f"Company {i}",
        location="Noida, Uttar Pradesh",
        description=LONG_DESC,
        url=f"https://www.adzuna.in/land/ad/{i}?se=abc",
        posted_at=datetime(2026, 10, 1, tzinfo=UTC),
        salary_min=900000.0,
        salary_max=1400000.0,
        salary_is_predicted=False,
        contract_time="full_time",
        contract_type="permanent",
    )
    base.update(kw)
    return RawJob(**base)


class FakeJobProvider(JobSearchProvider):
    name = "adzuna"
    country = "in"

    def __init__(self) -> None:
        self.queries: list[JobQuery] = []
        self.responses: list[Any] = []

    async def search(self, query: JobQuery) -> list[RawJob]:
        self.queries.append(query)
        item = self.responses.pop(0) if self.responses else [raw(1), raw(2), raw(3)]
        if isinstance(item, Exception):
            raise item
        return list(item)


@pytest.fixture
def job_provider() -> FakeJobProvider:
    return FakeJobProvider()


@pytest.fixture
def jclient(make_client: Callable[..., TestClient], job_provider: FakeJobProvider) -> TestClient:
    return make_client(job_provider=job_provider, adzuna_app_id="x", adzuna_app_key="y")


def search_body(**kw: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"profile": PROFILE, "target_roles": ["Backend Engineer"], "location": "Noida"}
    body.update(kw)
    return body


def do_search(c: TestClient, h: dict[str, str], **kw: Any) -> dict[str, Any]:
    r = c.post("/api/v1/jobs/searches", json=search_body(**kw), headers=h)
    assert r.status_code == 201, r.text
    data: dict[str, Any] = r.json()
    return data


# ------------------------------------------------------------- extraction


def make_pdf(lines: list[str]) -> bytes:
    content = "BT /F1 11 Tf 72 740 Td 14 TL " + " ".join(f"({ln}) Tj T*" for ln in lines) + " ET"
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(content)} >>\nstream\n{content}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for n, body in enumerate(objs, start=1):
        offsets.append(out.tell())
        out.write(f"{n} 0 obj\n{body}\nendobj\n".encode())
    xref = out.tell()
    out.write(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode())
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return out.getvalue()


def make_docx(paragraphs: list[str], doctype: bool = False) -> bytes:
    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
    dtd = '<!DOCTYPE x [<!ENTITY a "aaaa">]>' if doctype else ""
    xml = f'<?xml version="1.0"?>{dtd}<w:document xmlns:w="{ns}"><w:body>{body}</w:body></w:document>'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", xml)
        z.writestr("[Content_Types].xml", "<Types/>")
    return buf.getvalue()


RESUME_LINES = [
    "Backend Engineer at Northwind Logistics 2022 - present",
    "Built a FastAPI service for document processing with Pydantic validation.",
    "Designed PostgreSQL schemas and Redis caching for the tracking API.",
    "Skills: Python, SQL, FastAPI, Docker, AWS, Airflow, PySpark.",
]
MAX = 5 * 1024 * 1024


class TestResumeExtraction:
    def test_pdf(self) -> None:
        out = extract_resume("cv.pdf", "application/pdf", make_pdf(RESUME_LINES), MAX)
        assert out.file_type == "pdf" and out.pages == 1
        assert "FastAPI service" in out.text

    def test_docx(self) -> None:
        out = extract_resume(
            "cv.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            make_docx(RESUME_LINES),
            MAX,
        )
        assert out.file_type == "docx"
        assert "PostgreSQL schemas" in out.text

    @pytest.mark.parametrize(
        ("name", "ctype", "data", "code"),
        [
            ("cv.txt", "text/plain", b"hello", "resume_unsupported_type"),
            ("cv.pdf", "application/pdf", b"not a pdf at all", "resume_corrupt"),
            ("cv.pdf", "text/html", b"%PDF-1.4", "resume_unsupported_type"),
            ("cv.docx", None, b"PK\x03\x04garbage", "resume_corrupt"),
            ("cv.pdf", "application/pdf", b"", "resume_empty"),
        ],
    )
    def test_invalid_files(self, name: str, ctype: str | None, data: bytes, code: str) -> None:
        with pytest.raises(ResumeExtractionError) as exc:
            extract_resume(name, ctype, data, MAX)
        assert exc.value.code == code

    def test_scanned_pdf_reports_no_text(self) -> None:
        with pytest.raises(ResumeExtractionError) as exc:
            extract_resume("scan.pdf", "application/pdf", make_pdf([]), MAX)
        assert exc.value.code == "resume_no_text"

    def test_docx_with_entities_rejected(self) -> None:
        with pytest.raises(ResumeExtractionError) as exc:
            extract_resume("cv.docx", None, make_docx(RESUME_LINES, doctype=True), MAX)
        assert exc.value.code == "resume_corrupt"

    def test_size_limit(self) -> None:
        with pytest.raises(ResumeExtractionError) as exc:
            extract_resume("cv.pdf", "application/pdf", make_pdf(RESUME_LINES), 100)
        assert exc.value.code == "resume_too_large"

    def test_upload_endpoint(self, jclient: TestClient, user_a: dict[str, str]) -> None:
        files = {
            "file": (
                "cv.docx",
                make_docx(RESUME_LINES),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        }
        r = jclient.post("/api/v1/resumes/extract", files=files, headers=user_a)
        assert r.status_code == 200, r.text
        assert r.json()["file_type"] == "docx" and r.json()["char_count"] > 150
        bad = jclient.post(
            "/api/v1/resumes/extract",
            files={"file": ("x.exe", b"MZ", "application/octet-stream")},
            headers=user_a,
        )
        assert bad.status_code == 422 and bad.json()["error"]["code"] == "resume_unsupported_type"
        assert jclient.post("/api/v1/resumes/extract", files=files).status_code == 401


# ------------------------------------------------------- provider + normalise


async def test_adzuna_provider_parses_and_maps_errors() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        what = request.url.params.get("what")
        if what == "quota":
            return httpx.Response(429, json={})
        if what == "auth":
            return httpx.Response(401, json={})
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "42",
                        "title": "<strong>Data</strong> Engineer",
                        "company": {"display_name": "Acme"},
                        "location": {"display_name": "Noida"},
                        "description": "Build pipelines",
                        "created": "2026-10-10T08:00:00Z",
                        "redirect_url": "https://www.adzuna.in/land/ad/42",
                        "salary_min": 800000,
                        "salary_is_predicted": "1",
                        "contract_time": "full_time",
                    }
                ]
            },
        )

    p = AdzunaProvider("id", "key", "in", client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    jobs = await p.search(JobQuery(keywords="data engineer", location="Noida", full_time=True))
    assert seen[0].url.path == "/v1/api/jobs/in/search/1"
    assert seen[0].url.params["full_time"] == "1" and seen[0].url.params["where"] == "Noida"
    assert jobs[0].salary_is_predicted and jobs[0].company == "Acme"
    with pytest.raises(JobProviderQuotaError):
        await p.search(JobQuery(keywords="quota"))
    with pytest.raises(JobProviderNotConfigured):
        await p.search(JobQuery(keywords="auth"))


def test_normalize_validates_dedupes_and_hides_predicted_salary() -> None:
    jobs, rejected = normalize(
        [
            raw(1),
            raw(1),  # same provider id
            raw(2, title="Backend Engineer 1", company="Company 1", provider_job_id="99"),  # same content
            raw(3, url="javascript:alert(1)"),
            raw(4, url="https://evil.example.com/job"),
            raw(5, url=None),
            raw(6, title="<b>Senior</b> Data &amp; ML Engineer (Remote)", salary_is_predicted=True),
        ]
    )
    assert [j.provider_job_id for j in jobs] == ["1", "6"]
    assert rejected == 3
    six = jobs[1]
    assert six.title == "Senior Data & ML Engineer (Remote)"
    assert six.salary_min is None and six.salary_max is None  # predicted, not published
    assert six.work_mode == "remote" and six.experience_level == "senior"
    assert jobs[0].salary_min == 900000.0 and jobs[0].employment_type == "Full-time · Permanent"


@pytest.mark.parametrize(
    "url",
    [
        "ftp://www.adzuna.in/x",
        "https://user:pw@www.adzuna.in/x",
        "https://adzuna.in.evil.com/x",
        "",
        "https://",
    ],
)
def test_safe_url_rejects(url: str) -> None:
    assert safe_url(url) is None


# ---------------------------------------------------------------- scoring


def test_score_is_deterministic_and_evidence_based() -> None:
    profile = ResumeProfile.model_validate(PROFILE)
    item = JobMatchItem(
        job_ref="J1",
        required_skills=["Python", "Kafka", "postgres", "Kubernetes"],
        experience_fit=5,
        role_alignment=3,
        responsibilities_fit=1,
        reasons=["x" * 10],
        description_sufficient=True,
    )
    cov = skill_coverage(item.required_skills, profile, "I use Kubernetes daily.")
    assert cov.matched == ["Python", "postgres", "Kubernetes"]  # alias + resume text evidence
    assert cov.missing == ["Kafka"]
    # 0.40*0.75 + 0.25*1 + 0.20*0.5 + 0.15*0 = 0.65
    assert compute_score(item, cov) == 65
    assert compute_score(item, cov) == 65  # stable
    assert score_label(65) == "Good match"
    empty = skill_coverage([], profile, "")
    # No skills named: (0.25*1 + 0.20*0.5 + 0) / 0.6 = 0.5833
    assert compute_score(item, empty) == 58


# ------------------------------------------------------------- search API


def test_search_not_configured(client: TestClient, user_a: dict[str, str]) -> None:
    cfg = client.get("/api/v1/config").json()["job_search"]
    assert cfg["enabled"] is False
    r = client.post("/api/v1/jobs/searches", json=search_body(), headers=user_a)
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "job_search_not_configured"
    assert client.get("/api/v1/jobs/searches", headers=user_a).json() == []


def test_search_stores_valid_results_without_sending_resume(
    jclient: TestClient, user_a: dict[str, str], job_provider: FakeJobProvider
) -> None:
    job_provider.responses = [[raw(1), raw(1), raw(2, url="javascript:x")], [raw(3)]]
    out = do_search(
        jclient, user_a, target_roles=["Backend Engineer", "Data Engineer"], employment_types=["full_time"]
    )
    assert [r["title"] for r in out["results"]] == ["Backend Engineer 1", "Backend Engineer 3"]
    assert out["rejected"] == 1 and out["status"] == "discovered"
    assert (
        out["attribution"]["label"] == "Jobs by Adzuna"
        and out["attribution"]["url"] == "https://www.adzuna.in"
    )
    r0 = out["results"][0]
    assert r0["source"] == "Adzuna" and r0["salary_currency"] == "INR" and r0["match"] is None
    assert [q.keywords for q in job_provider.queries] == ["Backend Engineer", "Data Engineer"]
    assert all(q.location == "Noida" and q.full_time for q in job_provider.queries)
    for q in job_provider.queries:  # only role keywords, never resume content
        assert "FastAPI" not in q.keywords and "Northwind" not in q.keywords


def test_search_falls_back_to_suggested_roles_and_adapts_query(
    jclient: TestClient, user_a: dict[str, str], job_provider: FakeJobProvider
) -> None:
    do_search(jclient, user_a, target_roles=[], experience_level="intern", work_modes=["remote"])
    assert [q.keywords for q in job_provider.queries] == [
        "Backend Engineer internship remote",
        "Data Engineer internship remote",
    ]


def test_empty_results(jclient: TestClient, user_a: dict[str, str], job_provider: FakeJobProvider) -> None:
    job_provider.responses = [[], []]
    out = do_search(jclient, user_a)
    assert out["results"] == [] and out["total_found"] == 0


def test_cache_and_refresh(
    jclient: TestClient, user_a: dict[str, str], user_b: dict[str, str], job_provider: FakeJobProvider
) -> None:
    first = do_search(jclient, user_a)
    calls = len(job_provider.queries)
    again = do_search(jclient, user_a)
    assert again["id"] == first["id"] and again["cached"] is True
    assert len(job_provider.queries) == calls  # no quota spent
    do_search(jclient, user_b)  # cache is per user
    assert len(job_provider.queries) == calls * 2
    fresh = do_search(jclient, user_a, refresh=True)
    assert fresh["id"] != first["id"] and len(job_provider.queries) == calls * 3


def test_provider_errors(jclient: TestClient, user_a: dict[str, str], job_provider: FakeJobProvider) -> None:
    job_provider.responses = [JobProviderQuotaError("limit reached")]
    r = jclient.post("/api/v1/jobs/searches", json=search_body(), headers=user_a)
    assert r.status_code == 429 and r.json()["error"]["code"] == "job_search_quota_exceeded"
    job_provider.responses = [JobProviderError("down")]
    r = jclient.post("/api/v1/jobs/searches", json=search_body(refresh=True), headers=user_a)
    assert r.status_code == 502


def test_partial_failure_keeps_results_with_warning(
    jclient: TestClient, user_a: dict[str, str], job_provider: FakeJobProvider
) -> None:
    job_provider.responses = [[raw(1)], JobProviderQuotaError("limit reached")]
    out = do_search(jclient, user_a, target_roles=["Backend Engineer", "Data Engineer"])
    assert len(out["results"]) == 1
    assert out["warnings"] and "incomplete" in out["warnings"][0]


def test_search_rate_limit(
    make_client: Callable[..., TestClient], user_a: dict[str, str], job_provider: FakeJobProvider
) -> None:
    c = make_client(job_provider=job_provider, adzuna_app_id="x", adzuna_app_key="y", job_searches_per_hour=1)
    do_search(c, user_a)
    do_search(c, user_a)  # cached: allowed
    r = c.post("/api/v1/jobs/searches", json=search_body(refresh=True), headers=user_a)
    assert r.status_code == 429 and "job searches" in r.json()["error"]["message"]


# ---------------------------------------------------------- profile + match


def test_profile_redacts_contact_details(
    jclient: TestClient, user_a: dict[str, str], provider: FakeProvider
) -> None:
    r = jclient.post("/api/v1/jobs/profile", json={"resume_text": RESUME * 2}, headers=user_a)
    assert r.status_code == 200 and r.json()["suggested_roles"] == ["Backend Engineer", "Data Engineer"]
    call = next(c for c in provider.calls if c.operation == "resume_profile")
    assert "jordan@example.com" not in call.user_message


def test_match_scores_all_results_in_one_call(
    jclient: TestClient, user_a: dict[str, str], provider: FakeProvider
) -> None:
    s = do_search(jclient, user_a)
    r = jclient.post(
        f"/api/v1/jobs/searches/{s['id']}/match", json={"resume_text": RESUME * 2}, headers=user_a
    )
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["status"] == "matched"
    assert provider.count("job_matching") == 1
    m = out["results"][0]["match"]
    # Python matched (profile), Kafka missing: 0.4*0.5 + 0.25*0.75 + 0.2*0.75 + 0.15*0.5 = 0.6125
    assert m["score"] == 61 and m["label"] == "Good match"
    assert m["matched_skills"] == ["Python"] and m["missing_skills"] == ["Kafka"]
    assert m["confidence"] == "provisional"  # listing summary, not a full description
    call = next(c for c in provider.calls if c.operation == "job_matching")
    assert "jordan@example.com" not in call.user_message


def test_match_failure_keeps_listings(
    jclient: TestClient, user_a: dict[str, str], provider: FakeProvider
) -> None:
    s = do_search(jclient, user_a)
    provider.queue("job_matching", *[ProviderError("busy", transient=True)] * 3)
    out = jclient.post(
        f"/api/v1/jobs/searches/{s['id']}/match", json={"resume_text": RESUME * 2}, headers=user_a
    ).json()
    assert out["status"] == "match_failed" and out["match_error"]
    assert len(out["results"]) == 3 and all(r["match"] is None for r in out["results"])


def test_model_skipping_a_job_leaves_it_unscored(
    jclient: TestClient, user_a: dict[str, str], provider: FakeProvider
) -> None:
    s = do_search(jclient, user_a)
    only_first = {
        "matches": [
            {
                "job_ref": "J1",
                "required_skills": [],
                "experience_fit": 3,
                "role_alignment": 3,
                "responsibilities_fit": 3,
                "reasons": ["Partial overlap."],
                "description_sufficient": True,
            }
        ]
    }
    provider.queue("job_matching", only_first)
    out = jclient.post(
        f"/api/v1/jobs/searches/{s['id']}/match", json={"resume_text": RESUME * 2}, headers=user_a
    ).json()
    assert out["results"][0]["match"]["score"] == 50
    assert out["results"][1]["match"] is None


def test_rematch_with_full_description(jclient: TestClient, user_a: dict[str, str]) -> None:
    s = do_search(jclient, user_a)
    job_id = s["results"][0]["id"]
    r = jclient.post(
        f"/api/v1/jobs/{job_id}/match",
        json={"resume_text": RESUME * 2, "description": LONG_DESC * 2},
        headers=user_a,
    )
    assert r.status_code == 200
    assert r.json()["description_source"] == "user_provided"
    assert r.json()["match"]["confidence"] == "full"


# ------------------------------------------------------ isolation + handoff


def test_other_users_cannot_access(
    jclient: TestClient, user_a: dict[str, str], user_b: dict[str, str]
) -> None:
    s = do_search(jclient, user_a)
    job_id = s["results"][0]["id"]
    assert jclient.get(f"/api/v1/jobs/searches/{s['id']}", headers=user_b).status_code == 404
    assert (
        jclient.post(
            f"/api/v1/jobs/searches/{s['id']}/match", json={"resume_text": RESUME * 2}, headers=user_b
        ).status_code
        == 404
    )
    assert (
        jclient.post(
            f"/api/v1/jobs/{job_id}/match", json={"resume_text": RESUME * 2}, headers=user_b
        ).status_code
        == 404
    )
    assert (
        jclient.post(
            f"/api/v1/jobs/{job_id}/prepare-interview",
            json={"resume_text": RESUME * 2, "role_type": "software_engineering"},
            headers=user_b,
        ).status_code
        == 404
    )
    assert jclient.delete(f"/api/v1/jobs/searches/{s['id']}", headers=user_b).status_code == 404
    assert jclient.get("/api/v1/jobs/searches", headers=user_b).json() == []
    assert jclient.get("/api/v1/jobs/searches").status_code == 401


def test_prepare_interview_uses_existing_engine(
    jclient: TestClient, user_a: dict[str, str], job_provider: FakeJobProvider, provider: FakeProvider
) -> None:
    job_provider.responses = [[raw(1, description="Short summary only.")]]
    s = do_search(jclient, user_a, target_roles=["Backend Engineer"])
    job_id = s["results"][0]["id"]
    body = {"resume_text": RESUME * 2, "role_type": "software_engineering"}

    short = jclient.post(f"/api/v1/jobs/{job_id}/prepare-interview", json=body, headers=user_a)
    assert short.status_code == 400 and short.json()["error"]["code"] == "job_description_insufficient"

    r = jclient.post(
        f"/api/v1/jobs/{job_id}/prepare-interview", json={**body, "description": LONG_DESC}, headers=user_a
    )
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["created"] is True and len(out["session"]["questions"]) == 8
    assert out["session"]["job_title"] == "Backend Engineer 1" and out["session"]["company"] == "Company 1"
    assert "reliable production APIs" in out["session"]["jd_text"]
    gen_calls = provider.count("question_generation")

    again = jclient.post(f"/api/v1/jobs/{job_id}/prepare-interview", json=body, headers=user_a).json()
    assert again["created"] is False and again["session"]["id"] == out["session"]["id"]
    assert provider.count("question_generation") == gen_calls  # no duplicate session / AI cost

    linked = jclient.get(f"/api/v1/jobs/searches/{s['id']}", headers=user_a).json()["results"][0]
    assert linked["interview_session_id"] == out["session"]["id"]
    # The session is a normal interview: it shows in history.
    assert jclient.get("/api/v1/sessions", headers=user_a).json()["total"] == 1


def test_account_deletion_removes_job_data(jclient: TestClient, user_a: dict[str, str]) -> None:
    do_search(jclient, user_a)
    jclient.delete("/api/v1/me", headers=user_a)  # 400: no service key in tests, but data is removed
    assert jclient.get("/api/v1/jobs/searches", headers=user_a).json() == []
