import uuid
from collections.abc import Callable

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.security import issue_demo_token
from tests.conftest import answer_text, create_session, make_token


class TestAuthentication:
    def test_missing_token(self, client: TestClient) -> None:
        r = client.get("/api/v1/sessions")
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "unauthorized"

    def test_garbage_token(self, client: TestClient) -> None:
        r = client.get("/api/v1/sessions", headers={"Authorization": "Bearer not.a.jwt"})
        assert r.status_code == 401

    def test_wrong_signature(self, client: TestClient) -> None:
        token = make_token(uuid.uuid4(), secret="another-secret-of-sufficient-length-0000000")
        r = client.get("/api/v1/sessions", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401

    def test_expired_token(self, client: TestClient) -> None:
        token = make_token(uuid.uuid4(), expired=True)
        r = client.get("/api/v1/sessions", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "token_expired"

    def test_alg_none_rejected(self, client: TestClient) -> None:
        import jwt

        token = jwt.encode({"sub": str(uuid.uuid4()), "aud": "authenticated"}, key=None, algorithm="none")  # type: ignore[arg-type]
        r = client.get("/api/v1/sessions", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401

    def test_demo_token_rejected_when_demo_disabled(
        self, client: TestClient, settings_factory: Callable[..., Settings]
    ) -> None:
        token, _ = issue_demo_token(settings_factory(demo_mode=True), uuid.uuid4())
        r = client.get("/api/v1/sessions", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401

    def test_demo_endpoint_disabled(self, client: TestClient) -> None:
        assert client.post("/api/v1/demo/session").status_code == 403


class TestOwnership:
    """User B must never read or modify user A's data (IDOR). 404, not 403, so that
    record existence is not revealed."""

    def test_cross_user_access_is_blocked(
        self, client: TestClient, user_a: dict[str, str], user_b: dict[str, str]
    ) -> None:
        s = create_session(client, user_a)
        q0 = s["questions"][0]
        r = client.post(
            f"/api/v1/sessions/{s['id']}/answers",
            json={"question_id": q0["id"], "answer_text": answer_text()},
            headers=user_a,
        )
        answer_id = r.json()["id"]

        assert client.get(f"/api/v1/sessions/{s['id']}", headers=user_b).status_code == 404
        assert client.get(f"/api/v1/sessions/{s['id']}/answers", headers=user_b).status_code == 404
        assert client.delete(f"/api/v1/sessions/{s['id']}", headers=user_b).status_code == 404
        assert (
            client.post(
                f"/api/v1/sessions/{s['id']}/answers",
                json={"question_id": s["questions"][1]["id"], "answer_text": answer_text()},
                headers=user_b,
            ).status_code
            == 404
        )
        assert client.post(f"/api/v1/answers/{answer_id}/rewrite", headers=user_b).status_code == 404
        assert client.post(f"/api/v1/answers/{answer_id}/retry-evaluation", headers=user_b).status_code == 404
        assert client.get("/api/v1/sessions", headers=user_b).json()["total"] == 0
        assert client.get("/api/v1/analytics/overview", headers=user_b).json()["total_sessions"] == 0
        # Still intact for the owner.
        assert client.get(f"/api/v1/sessions/{s['id']}", headers=user_a).status_code == 200

    def test_question_from_other_session_rejected(
        self, client: TestClient, user_a: dict[str, str], user_b: dict[str, str]
    ) -> None:
        mine = create_session(client, user_b)
        theirs = create_session(client, user_a)
        r = client.post(
            f"/api/v1/sessions/{mine['id']}/answers",
            json={"question_id": theirs["questions"][0]["id"], "answer_text": answer_text()},
            headers=user_b,
        )
        assert r.status_code == 404


def test_demo_mode_isolates_visitors(make_client: Callable[..., TestClient]) -> None:
    client = make_client(demo_mode=True)
    t1 = client.post("/api/v1/demo/session").json()["access_token"]
    t2 = client.post("/api/v1/demo/session").json()["access_token"]
    h1, h2 = {"Authorization": f"Bearer {t1}"}, {"Authorization": f"Bearer {t2}"}
    s1 = client.get("/api/v1/sessions", headers=h1).json()
    assert s1["total"] == 3 and all(i["is_demo"] for i in s1["items"])
    assert client.get(f"/api/v1/sessions/{s1['items'][0]['id']}", headers=h2).status_code == 404
    me = client.get("/api/v1/me", headers=h1).json()
    assert me["is_demo"] is True


def test_small_clock_skew_is_tolerated(client: TestClient) -> None:
    from datetime import UTC, datetime, timedelta

    import jwt as pyjwt

    from tests.conftest import JWT_SECRET

    def tok(iat_offset: int) -> str:
        now = datetime.now(UTC) + timedelta(seconds=iat_offset)
        return pyjwt.encode(
            {"sub": str(uuid.uuid4()), "aud": "authenticated", "iat": now, "exp": now + timedelta(hours=1)},
            JWT_SECRET,
            algorithm="HS256",
        )

    # Issuer clock slightly ahead of ours: accepted.
    assert client.get("/api/v1/sessions", headers={"Authorization": f"Bearer {tok(5)}"}).status_code == 200
    # Far in the future: still rejected.
    assert client.get("/api/v1/sessions", headers={"Authorization": f"Bearer {tok(600)}"}).status_code == 401
