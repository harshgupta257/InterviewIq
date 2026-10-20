from fastapi.testclient import TestClient

from app.ai.provider import ProviderError
from tests.conftest import FakeProvider, create_session, question_set, session_payload


def test_create_session_generates_and_persists_eight_questions(
    client: TestClient, user_a: dict[str, str], provider: FakeProvider
) -> None:
    data = create_session(client, user_a)
    assert len(data["questions"]) == 8
    assert [q["order_index"] for q in data["questions"]] == list(range(8))
    assert data["status"] == "in_progress"
    assert data["seniority_level"] == "mid"  # inferred by analysis
    assert data["progress"] == {
        "total_questions": 8,
        "answered_count": 0,
        "evaluated_count": 0,
        "failed_evaluations": 0,
        "current_question_index": 0,
        "is_complete": False,
    }
    assert data["is_demo"] is False
    # Reopening does not regenerate.
    calls = provider.count("question_generation")
    again = client.get(f"/api/v1/sessions/{data['id']}", headers=user_a).json()
    assert again["questions"] == data["questions"]
    assert provider.count("question_generation") == calls


def test_explicit_seniority_wins(client: TestClient, user_a: dict[str, str]) -> None:
    data = create_session(client, user_a, seniority_level="senior")
    assert data["seniority_level"] == "senior"


def test_contact_details_are_redacted_before_ai(
    client: TestClient, user_a: dict[str, str], provider: FakeProvider
) -> None:
    create_session(client, user_a)
    for call in provider.calls:
        assert "jordan@example.com" not in call.user_message
        assert "555 123 4567" not in call.user_message


def test_generation_failure_saves_nothing(
    client: TestClient, user_a: dict[str, str], provider: FakeProvider
) -> None:
    provider.queue("question_generation", *[ProviderError("down", transient=True)] * 3)
    r = client.post("/api/v1/sessions", json=session_payload(), headers=user_a)
    assert r.status_code == 502
    assert r.json()["error"]["code"] == "ai_unavailable"
    assert client.get("/api/v1/sessions", headers=user_a).json()["total"] == 0


def test_invalid_model_output_after_retries_returns_error(
    client: TestClient, user_a: dict[str, str], provider: FakeProvider
) -> None:
    bad = question_set()
    bad["questions"] = bad["questions"][:5]
    provider.queue("question_generation", bad, bad, bad)
    r = client.post("/api/v1/sessions", json=session_payload(), headers=user_a)
    assert r.status_code == 502
    assert r.json()["error"]["code"] == "ai_invalid_output"
    assert client.get("/api/v1/sessions", headers=user_a).json()["total"] == 0


class TestValidation:
    def test_resume_too_short(self, client: TestClient, user_a: dict[str, str]) -> None:
        r = client.post("/api/v1/sessions", json=session_payload(resume_text="too short"), headers=user_a)
        assert r.status_code == 422
        body = r.json()["error"]
        assert body["code"] == "validation_error"
        assert "too short" not in r.text  # user input is not echoed back

    def test_resume_too_long(self, client: TestClient, user_a: dict[str, str]) -> None:
        r = client.post("/api/v1/sessions", json=session_payload(resume_text="x" * 15001), headers=user_a)
        assert r.status_code == 422

    def test_missing_jd(self, client: TestClient, user_a: dict[str, str]) -> None:
        body = session_payload()
        del body["jd_text"]
        assert client.post("/api/v1/sessions", json=body, headers=user_a).status_code == 422

    def test_bad_role_type(self, client: TestClient, user_a: dict[str, str]) -> None:
        r = client.post("/api/v1/sessions", json=session_payload(role_type="astronaut"), headers=user_a)
        assert r.status_code == 422

    def test_question_count_fixed_at_eight(self, client: TestClient, user_a: dict[str, str]) -> None:
        r = client.post("/api/v1/sessions", json=session_payload(question_count=12), headers=user_a)
        assert r.status_code == 422

    def test_user_id_in_body_is_rejected(self, client: TestClient, user_a: dict[str, str]) -> None:
        r = client.post("/api/v1/sessions", json=session_payload(user_id="someone-else"), headers=user_a)
        assert r.status_code == 422


def test_list_search_filter_sort_paginate(client: TestClient, user_a: dict[str, str]) -> None:
    create_session(
        client, user_a, job_title="Data Engineer", company="Fabrikam", role_type="data_engineering"
    )
    create_session(client, user_a, job_title="Backend Engineer", company="Contoso")
    create_session(
        client, user_a, job_title="ML Engineer", company="Contoso_AI", role_type="ai_ml_engineering"
    )

    all_ = client.get("/api/v1/sessions", headers=user_a).json()
    assert all_["total"] == 3
    assert all_["items"][0]["job_title"] == "ML Engineer"  # newest first

    assert client.get("/api/v1/sessions?q=fabri", headers=user_a).json()["total"] == 1
    assert client.get("/api/v1/sessions?q=contoso", headers=user_a).json()["total"] == 2
    # LIKE wildcards are escaped.
    assert client.get("/api/v1/sessions?q=%25", headers=user_a).json()["total"] == 0
    assert client.get("/api/v1/sessions?q=o_a", headers=user_a).json()["total"] == 1
    assert client.get("/api/v1/sessions?role_type=data_engineering", headers=user_a).json()["total"] == 1

    asc = client.get("/api/v1/sessions?sort=date_asc", headers=user_a).json()
    assert asc["items"][0]["job_title"] == "Data Engineer"

    page = client.get("/api/v1/sessions?page=2&page_size=2", headers=user_a).json()
    assert page["total"] == 3 and len(page["items"]) == 1
    assert client.get("/api/v1/sessions?page_size=500", headers=user_a).status_code == 422


def test_delete_cascades(client: TestClient, user_a: dict[str, str]) -> None:
    s = create_session(client, user_a)
    q = s["questions"][0]
    r = client.post(
        f"/api/v1/sessions/{s['id']}/answers",
        json={"question_id": q["id"], "answer_text": "A sufficiently long answer about FastAPI."},
        headers=user_a,
    )
    assert r.status_code == 201
    answer_id = r.json()["id"]
    assert client.delete(f"/api/v1/sessions/{s['id']}", headers=user_a).status_code == 204
    assert client.get(f"/api/v1/sessions/{s['id']}", headers=user_a).status_code == 404
    assert client.post(f"/api/v1/answers/{answer_id}/rewrite", headers=user_a).status_code == 404
    assert client.delete(f"/api/v1/sessions/{s['id']}", headers=user_a).status_code == 404


def test_health_and_config(client: TestClient) -> None:
    h = client.get("/health")
    assert h.status_code == 200 and h.json()["database"] == "ok"
    assert "X-Request-ID" in h.headers
    cfg = client.get("/api/v1/config").json()
    assert cfg["limits"]["resume_max"] == 15000
    assert "key" not in str(cfg).lower()


def test_root_points_to_web_app(client: TestClient) -> None:
    body = client.get("/").json()
    assert body["web_app"] == "http://localhost:5173"
    assert body["api_docs"] == "/docs"
