from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.infrastructure.config import Settings
from app.infrastructure.llm_client import FakeLLMClient
from app.infrastructure.session_repository import InMemorySessionRepository


def test_api_session_flow() -> None:
    repository = InMemorySessionRepository()
    app = create_app(
        settings=Settings(),
        repository=repository,
        llm_client=FakeLLMClient(),
    )
    client = TestClient(app)

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert "X-Request-ID" in health.headers

    scenarios = client.get("/api/scenarios")
    assert scenarios.status_code == 200
    assert len(scenarios.json()) >= 1

    personas = client.get("/api/personas")
    assert personas.status_code == 200
    assert len(personas.json()) >= 1

    create_response = client.post(
        "/api/sessions",
        json={"scenario_id": "sales_audit_cold_outreach", "persona_id": "owner"},
    )
    assert create_response.status_code == 201
    session_payload = create_response.json()["session"]
    session_id = session_payload["session_id"]
    assert session_payload["status"] == "active"

    resume_response = client.post(f"/api/sessions/{session_id}/resume")
    assert resume_response.status_code == 200

    detail_response = client.get(f"/api/sessions/{session_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["session"]["session_id"] == session_id
    assert detail_response.json()["turns"] == []

    turn_response = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"manager_message": "How do you track conversion losses now?"},
    )
    assert turn_response.status_code == 200
    turn_payload = turn_response.json()
    assert turn_payload["client_answer"]
    assert turn_payload["turn_index"] == 1
    assert len(turn_payload["turns"]) == 1

    unfinished_report = client.get(f"/api/sessions/{session_id}/report")
    assert unfinished_report.status_code == 409

    finish_response = client.post(f"/api/sessions/{session_id}/finish")
    assert finish_response.status_code == 200
    assert finish_response.json()["session"]["status"] == "finished"
    assert "Final interest:" in finish_response.json()["report"]

    report_response = client.get(f"/api/sessions/{session_id}/report")
    assert report_response.status_code == 200
    assert report_response.json()["session"]["status"] == "finished"


def test_api_returns_404_for_missing_session() -> None:
    app = create_app(
        settings=Settings(),
        repository=InMemorySessionRepository(),
        llm_client=FakeLLMClient(),
    )
    client = TestClient(app)

    response = client.get("/api/sessions/missing-session")
    assert response.status_code == 404
    assert "X-Request-ID" in response.headers
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "Session not found.",
            "request_id": response.headers["X-Request-ID"],
            "details": [],
        }
    }


def test_api_returns_openapi_friendly_validation_error_shape() -> None:
    app = create_app(
        settings=Settings(),
        repository=InMemorySessionRepository(),
        llm_client=FakeLLMClient(),
    )
    client = TestClient(app)

    response = client.post(
        "/api/sessions",
        json={"scenario_id": "sales_audit_cold_outreach"},
    )
    assert response.status_code == 422
    payload = response.json()
    assert "X-Request-ID" in response.headers
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["message"] == "Request validation failed."
    assert payload["error"]["request_id"] == response.headers["X-Request-ID"]
    assert payload["error"]["details"]


def test_api_preserves_incoming_request_id() -> None:
    app = create_app(
        settings=Settings(),
        repository=InMemorySessionRepository(),
        llm_client=FakeLLMClient(),
    )
    client = TestClient(app)

    response = client.get("/api/health", headers={"X-Request-ID": "req-123"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-123"


def test_api_create_session_returns_controlled_404_for_unknown_scenario() -> None:
    app = create_app(
        settings=Settings(),
        repository=InMemorySessionRepository(),
        llm_client=FakeLLMClient(),
    )
    client = TestClient(app)

    response = client.post(
        "/api/sessions",
        json={"scenario_id": "missing-scenario", "persona_id": "owner"},
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "not_found"
    assert "Unknown scenario_id 'missing-scenario'." == payload["error"]["message"]


def test_api_create_session_returns_controlled_404_for_unknown_persona() -> None:
    app = create_app(
        settings=Settings(),
        repository=InMemorySessionRepository(),
        llm_client=FakeLLMClient(),
    )
    client = TestClient(app)

    response = client.post(
        "/api/sessions",
        json={"scenario_id": "sales_audit_cold_outreach", "persona_id": "missing-persona"},
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "not_found"
    assert "Unknown persona_id 'missing-persona'." == payload["error"]["message"]


def test_api_finished_session_returns_conflict_for_message_and_resume() -> None:
    app = create_app(
        settings=Settings(),
        repository=InMemorySessionRepository(),
        llm_client=FakeLLMClient(),
    )
    client = TestClient(app)

    create_response = client.post(
        "/api/sessions",
        json={"scenario_id": "sales_audit_cold_outreach", "persona_id": "owner"},
    )
    session_id = create_response.json()["session"]["session_id"]

    finish_response = client.post(f"/api/sessions/{session_id}/finish")
    assert finish_response.status_code == 200

    message_response = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"manager_message": "Can we continue?"},
    )
    assert message_response.status_code == 409
    assert message_response.json()["error"]["code"] == "conflict"

    resume_response = client.post(f"/api/sessions/{session_id}/resume")
    assert resume_response.status_code == 409
    assert resume_response.json()["error"]["code"] == "conflict"


def test_api_session_detail_returns_full_turn_history_beyond_recent_turn_limit() -> None:
    repository = InMemorySessionRepository()
    app = create_app(
        settings=Settings(recent_turn_limit=2),
        repository=repository,
        llm_client=FakeLLMClient(),
    )
    client = TestClient(app)

    create_response = client.post(
        "/api/sessions",
        json={"scenario_id": "sales_audit_cold_outreach", "persona_id": "owner"},
    )
    session_id = create_response.json()["session"]["session_id"]

    for message in [
        "How do you track conversion losses now?",
        "What does your funnel look like by stage?",
        "Where do deals drop most often?",
    ]:
        response = client.post(
            f"/api/sessions/{session_id}/messages",
            json={"manager_message": message},
        )
        assert response.status_code == 200

    saved_session = repository.get(session_id)
    assert saved_session is not None
    assert len(saved_session.recent_turns) == 2
    assert len(saved_session.turns) == 3

    detail_response = client.get(f"/api/sessions/{session_id}")
    assert detail_response.status_code == 200
    assert len(detail_response.json()["turns"]) == 3
