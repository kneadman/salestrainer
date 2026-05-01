from __future__ import annotations

from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.access.models import TrainingSessionOwnership
from app.access.repository import AccessRepository
from app.api.main import create_app
from app.identity.dependencies import get_db_session
from app.identity.repository import IdentityRepository
from app.identity.security import hash_password
from app.infrastructure.config import Settings
from app.infrastructure.db import Base, import_model_modules
from app.infrastructure.llm_client import FakeLLMClient
from app.infrastructure.session_repository import InMemorySessionRepository


def _create_db_session() -> Session:
    import_model_modules()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)
    return session_factory()


def _create_client(
    db_session: Session | None = None,
    *,
    repository: InMemorySessionRepository | None = None,
) -> TestClient:
    app = create_app(
        settings=Settings(auth_cookie_secure=False),
        repository=repository or InMemorySessionRepository(),
        llm_client=FakeLLMClient(),
    )

    if db_session is not None:
        def override_get_db_session() -> Generator[Session, None, None]:
            yield db_session

        app.dependency_overrides[get_db_session] = override_get_db_session

    return TestClient(app)


def _seed_authenticated_user(
    db_session: Session,
    *,
    email: str = "manager@example.com",
    password: str = "password",
    role: str = "client_user",
    client_account_name: str = "Acme",
    client_account_slug: str = "acme",
    default_scenario_id: str = "generic_b2b_first_contact",
    product_line: str = "accounting_outsourcing",
    persona_policy: dict[str, object] | None = None,
    ui_config: dict[str, object] | None = None,
) -> tuple[object, object]:
    identity_repository = IdentityRepository(db_session)
    access_repository = AccessRepository(db_session)
    client_account = identity_repository.create_client_account(
        name=client_account_name,
        slug=client_account_slug,
    )
    user = identity_repository.create_user(
        client_account_id=client_account.id,
        email=email,
        password_hash=hash_password(password),
        role=role,
        must_change_password=False,
    )
    training_config = access_repository.create_training_config(
        client_account_id=client_account.id,
        name="Default config",
        default_scenario_id=default_scenario_id,
        product_line=product_line,
        persona_policy=persona_policy or {},
        ui_config=ui_config or {},
    )
    access_repository.assign_training_config_to_user(
        user_id=user.id,
        training_config_id=training_config.id,
        is_default=True,
    )
    return user, training_config


def _login(client: TestClient, *, email: str = "manager@example.com", password: str = "password") -> None:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    csrf_response = client.get("/auth/csrf")
    assert csrf_response.status_code == 200
    client.headers.update({"X-CSRF-Token": csrf_response.json()["csrf_token"]})


def _create_session_for_logged_in_user(client: TestClient) -> str:
    response = client.post("/api/sessions", json={})
    assert response.status_code == 201
    return response.json()["session"]["session_id"]


def test_api_session_flow() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(db_session, role="internal_admin")
    client = _create_client(db_session, repository=repository)
    _login(client)

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

    create_response = client.post("/api/sessions", json={})
    assert create_response.status_code == 201
    session_payload = create_response.json()["session"]
    session_id = session_payload["session_id"]
    assert session_payload["status"] == "active"
    assert session_payload["persona_name"] == "Unknown B2B contact"
    assert session_payload["scenario_id"] == "generic_b2b_first_contact"
    assert "public_brief" in session_payload

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
    assert "# Итог тренировки" in finish_response.json()["report"]

    report_response = client.get(f"/api/sessions/{session_id}/report")
    assert report_response.status_code == 200
    assert report_response.json()["session"]["status"] == "finished"

    db_session.close()


def test_api_create_session_requires_auth() -> None:
    client = _create_client()

    response = client.post("/api/sessions", json={})

    assert response.status_code == 401


def test_api_mutating_endpoint_rejects_authenticated_request_without_csrf() -> None:
    db_session = _create_db_session()
    _seed_authenticated_user(db_session)
    client = _create_client(db_session)
    response = client.post("/auth/login", json={"email": "manager@example.com", "password": "password"})
    assert response.status_code == 200

    response = client.post("/api/sessions", json={})

    assert response.status_code == 403
    assert response.json()["error"]["message"] == "Missing or invalid CSRF token."
    db_session.close()


def test_anonymous_cannot_get_session() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    owner_client = _create_client(db_session, repository=repository)
    _seed_authenticated_user(db_session)
    _login(owner_client)
    session_id = _create_session_for_logged_in_user(owner_client)

    anonymous_client = _create_client(db_session, repository=repository)
    response = anonymous_client.get(f"/api/sessions/{session_id}")

    assert response.status_code == 401

    db_session.close()


def test_anonymous_cannot_send_message() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(db_session)
    owner_client = _create_client(db_session, repository=repository)
    _login(owner_client)
    session_id = _create_session_for_logged_in_user(owner_client)

    anonymous_client = _create_client(db_session, repository=repository)
    response = anonymous_client.post(
        f"/api/sessions/{session_id}/messages",
        json={"manager_message": "Hello"},
    )

    assert response.status_code == 401

    db_session.close()


def test_anonymous_cannot_finish_session() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(db_session)
    owner_client = _create_client(db_session, repository=repository)
    _login(owner_client)
    session_id = _create_session_for_logged_in_user(owner_client)

    anonymous_client = _create_client(db_session, repository=repository)
    response = anonymous_client.post(f"/api/sessions/{session_id}/finish")

    assert response.status_code == 401

    db_session.close()


def test_user_cannot_read_another_users_session() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(db_session)
    _seed_authenticated_user(
        db_session,
        email="other@example.com",
        client_account_name="Beta",
        client_account_slug="beta",
    )
    owner_client = _create_client(db_session, repository=repository)
    _login(owner_client)
    session_id = _create_session_for_logged_in_user(owner_client)

    other_client = _create_client(db_session, repository=repository)
    _login(other_client, email="other@example.com")
    response = other_client.get(f"/api/sessions/{session_id}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"

    db_session.close()


def test_user_cannot_send_message_to_another_users_session() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(db_session)
    _seed_authenticated_user(
        db_session,
        email="other@example.com",
        client_account_name="Beta",
        client_account_slug="beta",
    )
    owner_client = _create_client(db_session, repository=repository)
    _login(owner_client)
    session_id = _create_session_for_logged_in_user(owner_client)

    other_client = _create_client(db_session, repository=repository)
    _login(other_client, email="other@example.com")
    response = other_client.post(
        f"/api/sessions/{session_id}/messages",
        json={"manager_message": "Can we continue?"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"

    db_session.close()


def test_user_cannot_finish_another_users_session() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(db_session)
    _seed_authenticated_user(
        db_session,
        email="other@example.com",
        client_account_name="Beta",
        client_account_slug="beta",
    )
    owner_client = _create_client(db_session, repository=repository)
    _login(owner_client)
    session_id = _create_session_for_logged_in_user(owner_client)

    other_client = _create_client(db_session, repository=repository)
    _login(other_client, email="other@example.com")
    response = other_client.post(f"/api/sessions/{session_id}/finish")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"

    db_session.close()


def test_user_cannot_get_another_users_report() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(db_session)
    _seed_authenticated_user(
        db_session,
        email="other@example.com",
        client_account_name="Beta",
        client_account_slug="beta",
    )
    owner_client = _create_client(db_session, repository=repository)
    _login(owner_client)
    session_id = _create_session_for_logged_in_user(owner_client)
    finish_response = owner_client.post(f"/api/sessions/{session_id}/finish")
    assert finish_response.status_code == 200

    other_client = _create_client(db_session, repository=repository)
    _login(other_client, email="other@example.com")
    response = other_client.get(f"/api/sessions/{session_id}/report")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"

    db_session.close()


def test_owner_user_can_access_own_session() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(db_session)
    client = _create_client(db_session, repository=repository)
    _login(client)
    session_id = _create_session_for_logged_in_user(client)

    response = client.get(f"/api/sessions/{session_id}")

    assert response.status_code == 200
    assert response.json()["session"]["session_id"] == session_id

    db_session.close()


def test_owner_user_can_send_message_to_own_session() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(db_session)
    client = _create_client(db_session, repository=repository)
    _login(client)
    session_id = _create_session_for_logged_in_user(client)

    response = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"manager_message": "How do you handle this now?"},
    )

    assert response.status_code == 200
    assert response.json()["turn_index"] == 1


def test_api_create_session_uses_users_default_training_config_and_creates_ownership() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    user, training_config = _seed_authenticated_user(
        db_session,
        default_scenario_id="sales_audit_cold_outreach",
        product_line="outsourced_cfo",
        persona_policy={
            "allowed_roles": ["owner"],
            "target_action": "book_financial_diagnostic",
        },
    )
    client = _create_client(db_session, repository=repository)
    _login(client)

    response = client.post("/api/sessions", json={})

    assert response.status_code == 201
    session_id = response.json()["session"]["session_id"]
    saved_session = repository.get(session_id)
    assert saved_session is not None
    assert saved_session.scenario_id == "sales_audit_cold_outreach"
    assert saved_session.persona.product_line == "outsourced_cfo"
    assert saved_session.persona.authority_level == "final_decider"
    ownership = db_session.scalar(select(TrainingSessionOwnership).where(TrainingSessionOwnership.session_id == saved_session.session_id))
    assert ownership is not None
    assert ownership.user_id == user.id
    assert ownership.client_account_id == training_config.client_account_id
    assert ownership.training_config_id == training_config.id

    db_session.close()


def test_api_personas_forbidden_for_client_user() -> None:
    db_session = _create_db_session()
    _seed_authenticated_user(db_session)
    client = _create_client(db_session)
    _login(client)

    response = client.get("/api/personas")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"

    db_session.close()


def test_api_personas_allowed_for_internal_admin() -> None:
    db_session = _create_db_session()
    _seed_authenticated_user(db_session, role="internal_admin")
    client = _create_client(db_session)
    _login(client)

    response = client.get("/api/personas")

    assert response.status_code == 200
    assert len(response.json()) >= 1

    db_session.close()


def test_api_scenarios_for_client_user_returns_default_scenario_when_allowed_scenarios_not_set() -> None:
    db_session = _create_db_session()
    _seed_authenticated_user(
        db_session,
        default_scenario_id="sales_audit_cold_outreach",
    )
    client = _create_client(db_session)
    _login(client)

    response = client.get("/api/scenarios")

    assert response.status_code == 200
    assert [scenario["scenario_id"] for scenario in response.json()] == ["sales_audit_cold_outreach"]

    db_session.close()


def test_api_scenarios_for_client_user_returns_allowed_scenarios() -> None:
    db_session = _create_db_session()
    _seed_authenticated_user(
        db_session,
        default_scenario_id="sales_audit_cold_outreach",
        ui_config={
            "allowed_scenarios": [
                "sales_audit_cold_outreach",
                "accounting_outsource_cold_outreach",
            ]
        },
    )
    client = _create_client(db_session)
    _login(client)

    response = client.get("/api/scenarios")

    assert response.status_code == 200
    assert [scenario["scenario_id"] for scenario in response.json()] == [
        "sales_audit_cold_outreach",
        "accounting_outsource_cold_outreach",
    ]

    db_session.close()


def test_api_create_session_rejects_request_persona_id_in_client_auth_mode() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(
        db_session,
        product_line="accounting_outsourcing",
        persona_policy={
            "allowed_roles": ["owner"],
            "target_action": "book_express_audit",
        },
    )
    client = _create_client(db_session, repository=repository)
    _login(client)

    response = client.post(
        "/api/sessions",
        json={"persona_id": "purchase_manager"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["message"] == "persona_id is not allowed for client_user sessions."

    db_session.close()


def test_api_create_session_allows_request_persona_id_for_internal_admin() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(
        db_session,
        role="internal_admin",
        product_line="accounting_outsourcing",
        persona_policy={
            "allowed_roles": ["owner"],
            "target_action": "book_express_audit",
        },
    )
    client = _create_client(db_session, repository=repository)
    _login(client)

    response = client.post(
        "/api/sessions",
        json={"scenario_id": "accounting_outsource_cold_outreach", "persona_id": "purchase_manager"},
    )

    assert response.status_code == 201
    session_id = response.json()["session"]["session_id"]
    saved_session = repository.get(session_id)
    assert saved_session is not None
    assert saved_session.persona.id == "purchase_manager"
    assert saved_session.scenario_id == "accounting_outsource_cold_outreach"


def test_api_returns_404_for_missing_session() -> None:
    db_session = _create_db_session()
    _seed_authenticated_user(db_session)
    client = _create_client(db_session)
    _login(client)

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

    db_session.close()


def test_api_returns_openapi_friendly_validation_error_shape() -> None:
    db_session = _create_db_session()
    _seed_authenticated_user(db_session)
    client = _create_client(db_session)
    _login(client)

    response = client.post(
        "/api/sessions",
        json={"persona_id": 123},
    )
    assert response.status_code == 422
    payload = response.json()
    assert "X-Request-ID" in response.headers
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["message"] == "Request validation failed."
    assert payload["error"]["request_id"] == response.headers["X-Request-ID"]
    assert payload["error"]["details"]

    db_session.close()


def test_api_preserves_incoming_request_id() -> None:
    client = _create_client()

    response = client.get("/api/health", headers={"X-Request-ID": "req-123"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-123"


def test_api_create_session_returns_controlled_404_for_unknown_scenario() -> None:
    db_session = _create_db_session()
    _seed_authenticated_user(db_session)
    client = _create_client(db_session)
    _login(client)

    response = client.post(
        "/api/sessions",
        json={"scenario_id": "missing-scenario"},
    )

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "not_found"
    assert "Unknown scenario_id 'missing-scenario'." == payload["error"]["message"]

    db_session.close()


def test_api_finished_session_returns_conflict_for_message_and_resume() -> None:
    db_session = _create_db_session()
    _seed_authenticated_user(db_session)
    client = _create_client(db_session)
    _login(client)

    create_response = client.post("/api/sessions", json={})
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

    db_session.close()


def test_api_session_detail_returns_full_turn_history_beyond_recent_turn_limit() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(db_session)
    app = create_app(
        settings=Settings(auth_cookie_secure=False, recent_turn_limit=2),
        repository=repository,
        llm_client=FakeLLMClient(),
    )

    def override_get_db_session() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    client = TestClient(app)
    _login(client)

    create_response = client.post("/api/sessions", json={})
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

    db_session.close()


def test_api_report_reveals_hidden_profile_only_after_finish() -> None:
    db_session = _create_db_session()
    repository = InMemorySessionRepository()
    _seed_authenticated_user(db_session)
    client = _create_client(db_session, repository=repository)
    _login(client)

    create_response = client.post("/api/sessions", json={})
    session_id = create_response.json()["session"]["session_id"]
    detail_before = client.get(f"/api/sessions/{session_id}")
    assert "# Кто был клиент" not in detail_before.text

    finish_response = client.post(f"/api/sessions/{session_id}/finish")
    assert finish_response.status_code == 200
    assert "# Кто был клиент" in finish_response.json()["report"]

    db_session.close()
