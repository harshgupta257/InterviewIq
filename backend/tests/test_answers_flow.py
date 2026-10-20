from typing import Any

from fastapi.testclient import TestClient

from app.ai.provider import ProviderError
from tests.conftest import EVALUATION, FakeProvider, answer_text, create_session


def submit(
    client: TestClient, headers: dict[str, str], session: dict[str, Any], i: int, text: str | None = None
):  # type: ignore[no-untyped-def]
    return client.post(
        f"/api/v1/sessions/{session['id']}/answers",
        json={"question_id": session["questions"][i]["id"], "answer_text": text or answer_text(i)},
        headers=headers,
    )


def test_submit_evaluates_with_backend_computed_score(client: TestClient, user_a: dict[str, str]) -> None:
    s = create_session(client, user_a)
    r = submit(client, user_a, s, 0)
    assert r.status_code == 201
    body = r.json()
    assert body["evaluation_status"] == "completed"
    ev = body["evaluation"]
    assert (
        ev["clarity"]["score"],
        ev["specificity"]["score"],
        ev["result_orientation"]["score"],
        ev["relevance"]["score"],
    ) == (4, 3, 4, 5)
    assert ev["average"] == 4.0 and ev["percentage"] == 80.0
    assert ev["clarity"]["reason"] == EVALUATION["clarity_reason"]
    assert ev["one_thing_to_fix"]


def test_duplicate_submit_is_idempotent(
    client: TestClient, user_a: dict[str, str], provider: FakeProvider
) -> None:
    s = create_session(client, user_a)
    first = submit(client, user_a, s, 0)
    second = submit(client, user_a, s, 0)
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert provider.count("answer_evaluation") == 1  # not re-evaluated / re-billed
    answers = client.get(f"/api/v1/sessions/{s['id']}/answers", headers=user_a).json()
    assert len(answers) == 1


def test_changed_resubmit_conflicts(client: TestClient, user_a: dict[str, str]) -> None:
    s = create_session(client, user_a)
    submit(client, user_a, s, 0)
    r = submit(client, user_a, s, 0, text="A completely different answer to the same question.")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "answer_exists"


def test_questions_must_be_answered_in_order(client: TestClient, user_a: dict[str, str]) -> None:
    s = create_session(client, user_a)
    r = submit(client, user_a, s, 2)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "out_of_order"
    assert r.json()["error"]["details"]["expected_question_id"] == s["questions"][0]["id"]


def test_answer_too_short(client: TestClient, user_a: dict[str, str]) -> None:
    s = create_session(client, user_a)
    assert submit(client, user_a, s, 0, text="short").status_code == 422


def test_evaluation_failure_preserves_answer_and_retry_succeeds(
    client: TestClient, user_a: dict[str, str], provider: FakeProvider
) -> None:
    s = create_session(client, user_a)
    provider.queue("answer_evaluation", *[ProviderError("down", transient=True)] * 3)
    r = submit(client, user_a, s, 0)
    assert r.status_code == 201
    failed = r.json()
    assert failed["evaluation_status"] == "failed"
    assert failed["evaluation"] is None  # no fabricated scores
    assert failed["evaluation_error"]
    assert failed["answer_text"] == answer_text(0)

    detail = client.get(f"/api/v1/sessions/{s['id']}", headers=user_a).json()
    assert detail["progress"]["answered_count"] == 1
    assert detail["progress"]["failed_evaluations"] == 1
    assert detail["progress"]["current_question_index"] == 1  # can continue

    retried = client.post(f"/api/v1/answers/{failed['id']}/retry-evaluation", headers=user_a)
    assert retried.status_code == 200
    assert retried.json()["evaluation_status"] == "completed"
    assert retried.json()["id"] == failed["id"]

    again = client.post(f"/api/v1/answers/{failed['id']}/retry-evaluation", headers=user_a)
    assert again.status_code == 409
    assert len(client.get(f"/api/v1/sessions/{s['id']}/answers", headers=user_a).json()) == 1


def test_progress_restored_and_session_completes(client: TestClient, user_a: dict[str, str]) -> None:
    s = create_session(client, user_a)
    for i in range(3):
        assert submit(client, user_a, s, i).status_code == 201
    # Simulates a browser refresh: state comes from the database.
    detail = client.get(f"/api/v1/sessions/{s['id']}", headers=user_a).json()
    assert detail["progress"]["current_question_index"] == 3
    assert detail["status"] == "in_progress"
    for i in range(3, 8):
        submit(client, user_a, s, i)
    detail = client.get(f"/api/v1/sessions/{s['id']}", headers=user_a).json()
    assert detail["progress"]["is_complete"] is True
    assert detail["status"] == "completed"
    assert detail["completed_at"] is not None
    assert detail["average_score"] == 80.0
    assert detail["completion_pct"] == 100.0


def test_rewrite_is_generated_saved_and_reused(
    client: TestClient, user_a: dict[str, str], provider: FakeProvider
) -> None:
    s = create_session(client, user_a)
    answer_id = submit(client, user_a, s, 0).json()["id"]
    r = client.post(f"/api/v1/answers/{answer_id}/rewrite", headers=user_a)
    assert r.status_code == 200
    rw = r.json()["rewrite"]
    assert rw["improved_answer"].startswith("In the FastAPI")
    assert rw["missing_information"] == ["The error rate before and after"]
    assert rw["is_demo"] is False
    assert provider.count("answer_rewriting") == 1

    cached = client.post(f"/api/v1/answers/{answer_id}/rewrite", headers=user_a).json()
    assert cached["rewrite"] == rw
    assert provider.count("answer_rewriting") == 1

    client.post(f"/api/v1/answers/{answer_id}/rewrite?regenerate=true", headers=user_a)
    assert provider.count("answer_rewriting") == 2

    detail = client.get(f"/api/v1/sessions/{s['id']}", headers=user_a).json()
    assert detail["answers"][0]["rewrite"]["improved_answer"]


def test_rewrite_failure_reports_error(
    client: TestClient, user_a: dict[str, str], provider: FakeProvider
) -> None:
    s = create_session(client, user_a)
    answer_id = submit(client, user_a, s, 0).json()["id"]
    provider.queue("answer_rewriting", ProviderError("bad", transient=False, status=400))
    r = client.post(f"/api/v1/answers/{answer_id}/rewrite", headers=user_a)
    assert r.status_code == 502
    detail = client.get(f"/api/v1/sessions/{s['id']}", headers=user_a).json()
    assert detail["answers"][0]["rewrite"] is None
