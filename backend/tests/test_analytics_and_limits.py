from collections.abc import Callable

from fastapi.testclient import TestClient

from tests.conftest import EVALUATION, FakeProvider, answer_text, create_session


def _answer(client: TestClient, h: dict[str, str], s: dict, i: int) -> None:  # type: ignore[type-arg]
    r = client.post(
        f"/api/v1/sessions/{s['id']}/answers",
        json={"question_id": s["questions"][i]["id"], "answer_text": answer_text(i)},
        headers=h,
    )
    assert r.status_code == 201


def test_analytics_empty(client: TestClient, user_a: dict[str, str]) -> None:
    o = client.get("/api/v1/analytics/overview", headers=user_a).json()
    assert o["total_sessions"] == 0
    assert o["average_score"] is None and o["most_recent_session_score"] is None
    assert client.get("/api/v1/analytics/progress", headers=user_a).json()["points"] == []


def test_analytics_aggregates_real_records(
    client: TestClient, user_a: dict[str, str], provider: FakeProvider
) -> None:
    s1 = create_session(client, user_a, job_title="First")
    for i in range(8):
        _answer(client, user_a, s1, i)  # every answer 4/3/4/5 -> 80%

    s2 = create_session(client, user_a, job_title="Second")
    provider.queue(
        "answer_evaluation",
        {**EVALUATION, "clarity": 2, "specificity": 2, "result_orientation": 2, "relevance": 2},
    )
    _answer(client, user_a, s2, 0)  # 40%
    create_session(client, user_a, job_title="Third (no answers)")

    o = client.get("/api/v1/analytics/overview", headers=user_a).json()
    assert o["total_sessions"] == 3
    assert o["completed_interviews"] == 1
    assert o["total_questions_answered"] == 9
    assert o["evaluated_answers"] == 9
    # Mean of averages: (8 * 4.0 + 2.0) / 9 = 3.777.. -> 75.6%
    assert o["average_score"] == 75.6
    assert o["most_recent_session_score"] == 40.0
    assert o["most_recent_session_id"] == s2["id"]
    assert o["dimension_averages"]["relevance"] == round((8 * 5 + 2) / 9, 2)
    assert o["includes_demo_data"] is False

    pts = client.get("/api/v1/analytics/progress", headers=user_a).json()["points"]
    assert [p["job_title"] for p in pts] == ["First", "Second"]  # sessions without scores excluded
    assert [p["average_score"] for p in pts] == [80.0, 40.0]


def test_rate_limit_on_ai_endpoints(make_client: Callable[..., TestClient], user_a: dict[str, str]) -> None:
    client = make_client(rate_limit_per_minute=2)
    create_session(client, user_a)
    s = create_session(client, user_a)
    r = client.post(
        "/api/v1/sessions",
        json={
            "resume_text": "x" * 200,
            "jd_text": "y" * 200,
            "job_title": "Eng",
            "role_type": "other",
        },
        headers=user_a,
    )
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "rate_limited"
    assert r.json()["error"]["details"]["retry_after_seconds"] > 0
    # Non-AI endpoints are not limited.
    assert client.get(f"/api/v1/sessions/{s['id']}", headers=user_a).status_code == 200
